import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.config import settings
from app.models.password_policy import PasswordPolicy, SINGLETON_ID
from app.routers.admin import verify_admin_key
from app.schemas.password_policy import PasswordPolicyResponse, PasswordPolicyUpdate

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/password-policy",
    tags=["Password Policy"],
    dependencies=[Depends(verify_admin_key)],
)

# Nombres de los objetos reales en Authentik — únicos, globales, compartidos
# por default-authentication-flow / default-password-change / password-recovery.
_AUTHENTIK_POLICY_NAME = "default-password-change-password-policy"
_AUTHENTIK_PROMPT_NAME = "default-password-change-field-password"

# Expiración: tipo de policy DISTINTO (authentik_policies_expiry.PasswordExpiryPolicy),
# no un campo de PasswordPolicy. Se ata al stage de password del login normal
# (no al de password-recovery/change) porque ahí es donde Authentik evalúa la
# antigüedad de la contraseña en cada inicio de sesión.
_AUTHENTIK_EXPIRY_POLICY_NAME = "casmarts-password-expiry-policy"
_AUTHENTIK_EXPIRY_TARGET_FLOW_SLUG = "default-authentication-flow"
_AUTHENTIK_EXPIRY_TARGET_STAGE_NAME = "default-authentication-password"

# EmailStage que emite el enlace de un solo uso, compartido por password_reset
# y new_account (ambos redirigen al flujo password-recovery).
_AUTHENTIK_EMAIL_STAGE_NAME = "casmarts-smtp-gmail"

# ReputationPolicy que aplica el bloqueo real por intentos fallidos — creada
# por casmarts-event-webhooks.yaml, atada a default-authentication-identification.
_AUTHENTIK_REPUTATION_POLICY_NAME = "casmarts-lockout-reputation"


async def _get_or_create(db: AsyncSession) -> PasswordPolicy:
    result = await db.execute(select(PasswordPolicy).where(PasswordPolicy.id == SINGLETON_ID))
    policy = result.scalar_one_or_none()
    if policy:
        return policy
    # No debería pasar en un sistema migrado (la migración siembra la fila),
    # pero cubre un DB nuevo sin ese seed.
    policy = PasswordPolicy(
        id=SINGLETON_ID,
        symbol_charset='!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ',
        error_message="La contraseña debe tener mínimo 10 caracteres, 1 mayúscula y 1 dígito.",
        help_text="Mínimo 10 caracteres, incluye al menos 1 mayúscula y 1 número.",
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def _push_to_authentik(policy: PasswordPolicy) -> tuple[bool, str | None]:
    """PATCH la PasswordPolicy y el Prompt reales en Authentik. No lanza —
    devuelve (ok, error) para que el caller pueda persistir el cambio local
    igual aunque Authentik esté inalcanzable (mismo patrón que las plantillas
    de correo: guardar siempre, avisar si el deploy en vivo falló)."""
    if not settings.AUTHENTIK_API_TOKEN or not settings.AUTHENTIK_HOST:
        return False, "AUTHENTIK_API_TOKEN/AUTHENTIK_HOST no configurados en .env."

    headers = {"Authorization": f"Bearer {settings.AUTHENTIK_API_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Ubicar la PasswordPolicy por nombre (no hardcodear pk).
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/policies/password/",
                headers=headers,
                params={"name": _AUTHENTIK_POLICY_NAME},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            policy_obj = next((p for p in results if p.get("name") == _AUTHENTIK_POLICY_NAME), None)
            if not policy_obj:
                return False, f"No se encontró la PasswordPolicy '{_AUTHENTIK_POLICY_NAME}' en Authentik."

            patch_resp = await client.patch(
                f"{settings.AUTHENTIK_HOST}/api/v3/policies/password/{policy_obj['pk']}/",
                headers=headers,
                json={
                    "length_min": policy.length_min,
                    "amount_uppercase": policy.amount_uppercase,
                    "amount_lowercase": policy.amount_lowercase,
                    "amount_digits": policy.amount_digits,
                    "amount_symbols": policy.amount_symbols,
                    "symbol_charset": policy.symbol_charset,
                    "check_zxcvbn": policy.check_zxcvbn,
                    "zxcvbn_score_threshold": policy.zxcvbn_score_threshold,
                    "check_have_i_been_pwned": policy.check_have_i_been_pwned,
                    "hibp_allowed_count": policy.hibp_allowed_count,
                    "error_message": policy.error_message,
                },
            )
            patch_resp.raise_for_status()

            # 2. Ubicar el Prompt del campo password por nombre y actualizar sub_text.
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/stages/prompt/prompts/",
                headers=headers,
                params={"name": _AUTHENTIK_PROMPT_NAME},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            prompt_obj = next((p for p in results if p.get("name") == _AUTHENTIK_PROMPT_NAME), None)
            if not prompt_obj:
                return False, f"Se actualizó la política pero no se encontró el Prompt '{_AUTHENTIK_PROMPT_NAME}' para el tooltip."

            patch_resp = await client.patch(
                f"{settings.AUTHENTIK_HOST}/api/v3/stages/prompt/prompts/{prompt_obj['pk']}/",
                headers=headers,
                json={"sub_text": policy.help_text},
            )
            patch_resp.raise_for_status()

            # 3. Expiración de contraseña — policy y binding aparte (ver
            # constantes arriba). Siempre se sincroniza days aunque esté
            # deshabilitada, para que quede lista si luego se activa; el
            # enforcement real lo controla PolicyBinding.enabled.
            await _sync_expiry_policy(client, headers, policy)

            # 4. Vigencia del enlace de un solo uso (EmailStage.token_expiry,
            # formato Authentik "minutes=N") — comparte el mismo EmailStage
            # tanto password_reset como new_account (ambos redirigen al
            # mismo flujo password-recovery).
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/stages/email/",
                headers=headers,
                params={"name": _AUTHENTIK_EMAIL_STAGE_NAME},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            email_stage_obj = next((s for s in results if s.get("name") == _AUTHENTIK_EMAIL_STAGE_NAME), None)
            if not email_stage_obj:
                return False, f"Se actualizó lo demás pero no se encontró el EmailStage '{_AUTHENTIK_EMAIL_STAGE_NAME}' para la vigencia del enlace."

            patch_resp = await client.patch(
                f"{settings.AUTHENTIK_HOST}/api/v3/stages/email/{email_stage_obj['pk']}/",
                headers=headers,
                json={"token_expiry": f"minutes={policy.link_expiry_minutes}"},
            )
            patch_resp.raise_for_status()

            # 5. Intentos fallidos antes de bloquear la cuenta —
            # ReputationPolicy('casmarts-lockout-reputation').threshold, ya
            # sembrada por casmarts-event-webhooks.yaml. Cada login_failed
            # resta 1 punto (authentik/policies/reputation/signals.py), así
            # que threshold = -lockout_failed_attempts bloquea exactamente
            # tras esa cantidad de intentos consecutivos.
            resp = await client.get(
                f"{settings.AUTHENTIK_HOST}/api/v3/policies/reputation/",
                headers=headers,
                params={"name": _AUTHENTIK_REPUTATION_POLICY_NAME},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            reputation_policy_obj = next((p for p in results if p.get("name") == _AUTHENTIK_REPUTATION_POLICY_NAME), None)
            if not reputation_policy_obj:
                return False, f"Se actualizó lo demás pero no se encontró la ReputationPolicy '{_AUTHENTIK_REPUTATION_POLICY_NAME}' para el umbral de bloqueo."

            # El validador de ReputationPolicySerializer exige check_ip o
            # check_username en TODA request, incluso PATCH parcial (mismo
            # patrón ya visto en PolicyBinding: hay que reenviar el objeto
            # completo, no solo el campo que cambia — confirmado en vivo
            # 2026-07-04, un PATCH con solo {"threshold": ...} devolvió "Se
            # debe verificar la IP o el nombre de usuario").
            patch_resp = await client.patch(
                f"{settings.AUTHENTIK_HOST}/api/v3/policies/reputation/{reputation_policy_obj['pk']}/",
                headers=headers,
                json={
                    "check_ip": reputation_policy_obj["check_ip"],
                    "check_username": reputation_policy_obj["check_username"],
                    "threshold": -policy.lockout_failed_attempts,
                },
            )
            patch_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return False, f"Error de la API de Authentik: {e.response.text[:300]}"
    except httpx.RequestError as e:
        return False, f"No se pudo contactar a Authentik: {str(e)}"
    except LookupError as e:
        return False, str(e)

    return True, None


async def _get_flow_stage_ptr_id(client: httpx.AsyncClient, headers: dict, flow_slug: str, stage_name: str) -> tuple[str, str]:
    """Devuelve (ptr_id, fsb_pk) para el FlowStageBinding indicado.

    PolicyBinding.target necesita el ptr-id de PolicyBindingModel
    (policybindingmodel_ptr_id) al CREAR/ACTUALIZAR — es lo que realmente
    guarda la columna target_id, confirmado leyendo el modelo directo
    (PolicyBinding.target_id). Pero al LEER vía GET /api/v3/policies/bindings/,
    el serializer de DRF devuelve el "target" resuelto como el pk PROPIO del
    FlowStageBinding (fsb_uuid) — MTI de Django: mismo FK, dos UUIDs válidos
    según se lea la columna cruda o el .pk del objeto ya resuelto. Comparar
    contra el valor equivocado (como se hizo al principio) hace que la
    detección de "ya existe" nunca dispare match, y cada guardado intenta
    crear un PolicyBinding duplicado — error 'policy, target, order deben
    formar un conjunto único' (confirmado en vivo 2026-07-03)."""
    resp = await client.get(f"{settings.AUTHENTIK_HOST}/api/v3/flows/instances/{flow_slug}/", headers=headers)
    resp.raise_for_status()
    flow_pk = resp.json()["pk"]

    resp = await client.get(
        f"{settings.AUTHENTIK_HOST}/api/v3/flows/bindings/",
        headers=headers,
        params={"target": flow_pk},
    )
    resp.raise_for_status()
    for binding in resp.json().get("results", []):
        if binding.get("stage_obj", {}).get("name") == stage_name:
            return binding["policybindingmodel_ptr_id"], binding["pk"]
    raise LookupError(f"No se encontró el stage '{stage_name}' en el flujo '{flow_slug}'.")


async def _sync_expiry_policy(client: httpx.AsyncClient, headers: dict, policy: PasswordPolicy) -> None:
    # 1. Get-or-create la PasswordExpiryPolicy por nombre.
    resp = await client.get(
        f"{settings.AUTHENTIK_HOST}/api/v3/policies/password_expiry/",
        headers=headers,
        params={"name": _AUTHENTIK_EXPIRY_POLICY_NAME},
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    expiry_obj = next((p for p in results if p.get("name") == _AUTHENTIK_EXPIRY_POLICY_NAME), None)

    if expiry_obj:
        patch_resp = await client.patch(
            f"{settings.AUTHENTIK_HOST}/api/v3/policies/password_expiry/{expiry_obj['pk']}/",
            headers=headers,
            json={"days": policy.expiry_days},
        )
        patch_resp.raise_for_status()
        expiry_pk = expiry_obj["pk"]
    else:
        create_resp = await client.post(
            f"{settings.AUTHENTIK_HOST}/api/v3/policies/password_expiry/",
            headers=headers,
            # deny_only=False: además de negar el acceso, redirige automáticamente
            # al flujo de cambio de contraseña en vez de solo bloquear el login.
            json={"name": _AUTHENTIK_EXPIRY_POLICY_NAME, "days": policy.expiry_days, "deny_only": False},
        )
        create_resp.raise_for_status()
        expiry_pk = create_resp.json()["pk"]

    # 2. Get-or-create el PolicyBinding que realmente activa/desactiva el
    # enforcement — la policy puede existir configurada sin estar aplicándose.
    target_ptr_id, target_fsb_pk = await _get_flow_stage_ptr_id(
        client, headers, _AUTHENTIK_EXPIRY_TARGET_FLOW_SLUG, _AUTHENTIK_EXPIRY_TARGET_STAGE_NAME
    )
    resp = await client.get(
        f"{settings.AUTHENTIK_HOST}/api/v3/policies/bindings/",
        headers=headers,
        params={"policy": expiry_pk},
    )
    resp.raise_for_status()
    # GET serializa "target" como el pk propio del FlowStageBinding
    # (target_fsb_pk), no el ptr_id usado para crear — ver docstring de
    # _get_flow_stage_ptr_id.
    binding_obj = next((b for b in resp.json().get("results", []) if b.get("target") == target_fsb_pk), None)

    if binding_obj:
        # El ViewSet de PolicyBinding solo expone PUT (confirmado via
        # OPTIONS) — no soporta PATCH parcial, hay que reenviar el objeto
        # completo (target/order no vuelven a resolverse, se toman del
        # binding existente para no alterarlos).
        put_resp = await client.put(
            f"{settings.AUTHENTIK_HOST}/api/v3/policies/bindings/{binding_obj['pk']}/",
            headers=headers,
            json={
                "policy": expiry_pk,
                "target": binding_obj["target"],
                "order": binding_obj["order"],
                "enabled": policy.expiry_enabled,
                "timeout": binding_obj.get("timeout", 30),
                "failure_result": binding_obj.get("failure_result", True),
            },
        )
        put_resp.raise_for_status()
    else:
        create_resp = await client.post(
            f"{settings.AUTHENTIK_HOST}/api/v3/policies/bindings/",
            headers=headers,
            json={
                "policy": expiry_pk,
                "target": target_ptr_id,
                "order": 0,
                "enabled": policy.expiry_enabled,
                "timeout": 30,
                "failure_result": True,
            },
        )
        create_resp.raise_for_status()


@router.get("", response_model=PasswordPolicyResponse)
async def get_password_policy(db: AsyncSession = Depends(get_db)):
    policy = await _get_or_create(db)
    return PasswordPolicyResponse.model_validate(policy)


@router.patch("", response_model=PasswordPolicyResponse)
async def patch_password_policy(
    policy_in: PasswordPolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    policy = await _get_or_create(db)

    update_data = policy_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    synced, sync_error = await _push_to_authentik(policy)
    if synced:
        policy.last_synced_at = datetime.utcnow()

    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    if not synced:
        log.warning("Password policy guardada en DB pero no sincronizada a Authentik: %s", sync_error)

    response = PasswordPolicyResponse.model_validate(policy)
    response.synced_to_authentik = synced
    response.sync_error = sync_error
    return response


@router.post("/resync", response_model=PasswordPolicyResponse)
async def resync_password_policy(db: AsyncSession = Depends(get_db)):
    """Reintenta el push a Authentik sin modificar nada en la DB — útil tras
    un fallo de red temporal reportado por PATCH."""
    policy = await _get_or_create(db)
    synced, sync_error = await _push_to_authentik(policy)
    if synced:
        policy.last_synced_at = datetime.utcnow()
        db.add(policy)
        await db.commit()
        await db.refresh(policy)

    response = PasswordPolicyResponse.model_validate(policy)
    response.synced_to_authentik = synced
    response.sync_error = sync_error
    return response
