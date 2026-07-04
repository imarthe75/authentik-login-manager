import React, { useEffect, useState } from 'react';
import { CheckCircle, AlertCircle, RefreshCw, Wand2 } from 'lucide-react';
import { passwordPolicyApi } from '../api/passwordPolicyApi';
import { PasswordPolicy, PasswordPolicyUpdate } from '../types/passwordPolicy';

// Espejo de _format_link_expiry_text en admin.py — mismo texto que verá el
// usuario en el correo, calculado aquí solo para la vista previa en vivo.
const formatLinkExpiryText = (minutes: number): string => {
  if (minutes % 60 === 0) {
    const hours = minutes / 60;
    return `${hours} hora${hours !== 1 ? 's' : ''}`;
  }
  return `${minutes} minuto${minutes !== 1 ? 's' : ''}`;
};

const ZXCVBN_LABELS: Record<number, string> = {
  0: '0 — Muy débil (acepta casi cualquier cosa)',
  1: '1 — Débil',
  2: '2 — Razonable',
  3: '3 — Fuerte (recomendado)',
  4: '4 — Muy fuerte',
};

const buildSuggestedHelpText = (p: PasswordPolicyUpdate): string => {
  const parts: string[] = [`Mínimo ${p.length_min ?? 10} caracteres`];
  const reqs: string[] = [];
  if ((p.amount_uppercase ?? 0) > 0) reqs.push(`${p.amount_uppercase} mayúscula${(p.amount_uppercase as number) > 1 ? 's' : ''}`);
  if ((p.amount_lowercase ?? 0) > 0) reqs.push(`${p.amount_lowercase} minúscula${(p.amount_lowercase as number) > 1 ? 's' : ''}`);
  if ((p.amount_digits ?? 0) > 0) reqs.push(`${p.amount_digits} número${(p.amount_digits as number) > 1 ? 's' : ''}`);
  if ((p.amount_symbols ?? 0) > 0) reqs.push(`${p.amount_symbols} símbolo${(p.amount_symbols as number) > 1 ? 's' : ''}`);
  if (reqs.length) parts.push(`incluye al menos ${reqs.join(', ')}`);
  if (p.check_zxcvbn) parts.push(`evita palabras comunes, nombres o patrones predecibles (fechas, secuencias como '1234')`);
  return parts.join(', ') + '.';
};

interface ToggleProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}

const Toggle: React.FC<ToggleProps> = ({ checked, onChange, label, description }) => (
  <label className="flex items-start gap-3 cursor-pointer">
    <div className="relative mt-0.5 shrink-0">
      <input type="checkbox" className="sr-only" checked={checked} onChange={e => onChange(e.target.checked)} />
      <div className="w-10 h-5 rounded-full transition-colors duration-200" style={{ backgroundColor: checked ? '#4272A5' : '#d1d5db' }} />
      <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200" style={{ transform: checked ? 'translateX(20px)' : 'translateX(0)' }} />
    </div>
    <div className="min-w-0">
      <p className="text-sm font-medium text-gray-800">{label}</p>
      {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
    </div>
  </label>
);

const NumberField: React.FC<{ label: string; value: number; onChange: (v: number) => void; min?: number; max?: number }> = ({
  label, value, onChange, min = 0, max = 20,
}) => (
  <label className="block">
    <span className="text-xs font-medium text-gray-600">{label}</span>
    <input
      type="number"
      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
      value={value}
      min={min}
      max={max}
      onChange={e => onChange(Math.max(min, Math.min(max, Number(e.target.value) || 0)))}
    />
  </label>
);

export const PasswordPolicyPanel: React.FC = () => {
  const [policy, setPolicy] = useState<PasswordPolicy | null>(null);
  const [draft, setDraft] = useState<PasswordPolicyUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncError, setLastSyncError] = useState<string | null>(null);

  useEffect(() => {
    passwordPolicyApi.get()
      .then(p => { setPolicy(p); setDraft(p); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const update = <K extends keyof PasswordPolicyUpdate>(key: K, value: PasswordPolicyUpdate[K]) => {
    setDraft(prev => ({ ...prev, [key]: value }));
  };

  const handleGenerateHelpText = () => {
    update('help_text', buildSuggestedHelpText(draft));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await passwordPolicyApi.update(draft);
      setPolicy(updated);
      setDraft(updated);
      setLastSyncError(updated.sync_error);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleResync = async () => {
    setSaving(true);
    try {
      const updated = await passwordPolicyApi.resync();
      setPolicy(updated);
      setDraft(updated);
      setLastSyncError(updated.sync_error);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">Cargando política de contraseña…</div>;
  }
  if (!policy) {
    return <div className="flex-1 flex items-center justify-center text-red-500 text-sm">{error || 'No se pudo cargar la política.'}</div>;
  }

  const isDirty = JSON.stringify(draft) !== JSON.stringify(policy);

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-3xl mx-auto p-8 space-y-8">
        <div>
          <h2 className="text-lg font-bold text-gray-800">Política de Contraseña</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configuración global — Authentik hoy tiene una sola política de contraseña, compartida por todos los
            flujos de inicio de sesión, cambio y recuperación de contraseña.
          </p>
        </div>

        {policy.last_synced_at && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <CheckCircle size={14} className="text-green-500" />
            Última sincronización con Authentik: {new Date(policy.last_synced_at).toLocaleString('es-MX')}
          </div>
        )}
        {lastSyncError && (
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold">Se guardó en la base de datos, pero no se pudo sincronizar con Authentik:</p>
              <p className="mt-0.5">{lastSyncError}</p>
              <button onClick={handleResync} disabled={saving} className="mt-2 inline-flex items-center gap-1 text-amber-900 font-semibold hover:underline">
                <RefreshCw size={12} /> Reintentar sincronización
              </button>
            </div>
          </div>
        )}

        <section className="space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Vigencia del enlace</h3>
          <NumberField
            label="Minutos de validez del enlace de un solo uso"
            value={draft.link_expiry_minutes ?? 60}
            min={1}
            max={10080}
            onChange={v => update('link_expiry_minutes', v)}
          />
          <p className="text-xs text-gray-500">
            Aplica al enlace para establecer contraseña al dar de alta un usuario nuevo y al de recuperación de
            contraseña (comparten el mismo mecanismo en Authentik). Texto mostrado en el correo:{' '}
            <span className="font-semibold text-gray-700">"{formatLinkExpiryText(draft.link_expiry_minutes ?? 60)}"</span>.
          </p>
        </section>

        <section className="space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Bloqueo de cuenta</h3>
          <NumberField
            label="Intentos fallidos permitidos antes de bloquear"
            value={draft.lockout_failed_attempts ?? 5}
            min={1}
            max={50}
            onChange={v => update('lockout_failed_attempts', v)}
          />
          <p className="text-xs text-gray-500">
            Al llegar a este número de intentos fallidos consecutivos, la cuenta se bloquea temporalmente y se
            envía el correo de "Bloqueo de cuenta" (Vista Correo).
          </p>
        </section>

        <section className="space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Requisitos</h3>
          <NumberField label="Longitud mínima" value={draft.length_min ?? 10} min={4} max={128} onChange={v => update('length_min', v)} />
          <div className="grid grid-cols-2 gap-4">
            <NumberField label="Mayúsculas mínimas" value={draft.amount_uppercase ?? 0} onChange={v => update('amount_uppercase', v)} />
            <NumberField label="Minúsculas mínimas" value={draft.amount_lowercase ?? 0} onChange={v => update('amount_lowercase', v)} />
            <NumberField label="Números mínimos" value={draft.amount_digits ?? 0} onChange={v => update('amount_digits', v)} />
            <NumberField label="Símbolos mínimos" value={draft.amount_symbols ?? 0} onChange={v => update('amount_symbols', v)} />
          </div>
          <label className="block">
            <span className="text-xs font-medium text-gray-600">Símbolos permitidos</span>
            <input
              type="text"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
              value={draft.symbol_charset ?? ''}
              onChange={e => update('symbol_charset', e.target.value)}
            />
            <span className="text-[11px] text-gray-400">Conjunto exacto de caracteres que cuentan como "símbolo" — incluye el espacio si quieres permitirlo.</span>
          </label>
        </section>

        <section className="space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Patrones predecibles</h3>
          <Toggle
            checked={draft.check_zxcvbn ?? true}
            onChange={v => update('check_zxcvbn', v)}
            label="Rechazar contraseñas débiles o predecibles (zxcvbn)"
            description="Detecta secuencias, palabras del diccionario, fechas, teclado (qwerty), sustituciones obvias (@ por a), etc. — aunque cumplan los requisitos numéricos de arriba."
          />
          {draft.check_zxcvbn && (
            <label className="block pl-12">
              <span className="text-xs font-medium text-gray-600">Nivel de fortaleza mínimo exigido</span>
              <select
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                value={draft.zxcvbn_score_threshold ?? 3}
                onChange={e => update('zxcvbn_score_threshold', Number(e.target.value))}
              >
                {[0, 1, 2, 3, 4].map(n => <option key={n} value={n}>{ZXCVBN_LABELS[n]}</option>)}
              </select>
            </label>
          )}
          <Toggle
            checked={draft.check_have_i_been_pwned ?? false}
            onChange={v => update('check_have_i_been_pwned', v)}
            label="Rechazar contraseñas filtradas (Have I Been Pwned)"
            description="Consulta el hash de la contraseña contra la base de datos pública de contraseñas comprometidas en brechas de seguridad conocidas."
          />
          {draft.check_have_i_been_pwned && (
            <NumberField
              label="Apariciones permitidas en brechas antes de rechazar"
              value={draft.hibp_allowed_count ?? 0}
              min={0}
              max={100}
              onChange={v => update('hibp_allowed_count', v)}
            />
          )}
        </section>

        <section className="space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Caducidad de contraseña</h3>
          <Toggle
            checked={draft.expiry_enabled ?? false}
            onChange={v => update('expiry_enabled', v)}
            label="Forzar cambio periódico de contraseña"
            description="Al vencer, Authentik redirige automáticamente al usuario a establecer una nueva contraseña en su próximo inicio de sesión. Aplica al login normal, no a la recuperación por correo."
          />
          {draft.expiry_enabled && (
            <NumberField
              label="Días de vigencia"
              value={draft.expiry_days ?? 90}
              min={1}
              max={3650}
              onChange={v => update('expiry_days', v)}
            />
          )}
        </section>

        <section className="space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Mensajes al usuario</h3>
          <label className="block">
            <span className="text-xs font-medium text-gray-600">Mensaje de error (al rechazar por requisitos numéricos)</span>
            <textarea
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              rows={2}
              maxLength={500}
              value={draft.error_message ?? ''}
              onChange={e => update('error_message', e.target.value)}
            />
          </label>
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-600">
                Texto de ayuda (visible bajo el campo, antes de escribir)
              </span>
              <button
                type="button"
                onClick={handleGenerateHelpText}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-800"
              >
                <Wand2 size={12} /> Generar desde los requisitos
              </button>
            </div>
            <textarea
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              rows={3}
              maxLength={1000}
              value={draft.help_text ?? ''}
              onChange={e => update('help_text', e.target.value)}
            />
          </div>

          {/* Vista previa: aproxima el tooltip real bajo el campo de contraseña en Authentik */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Vista previa del campo</p>
            <label className="text-sm font-medium text-gray-800">Nueva Contraseña</label>
            <div className="mt-1 h-9 rounded-lg border border-gray-300 bg-white" />
            <p className="text-xs text-gray-500 mt-1.5">{draft.help_text}</p>
          </div>
        </section>

        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          {error && <span className="text-xs text-red-600">{error}</span>}
          <div className="ml-auto flex items-center gap-3">
            {isDirty && <span className="text-xs text-amber-600">Cambios sin guardar</span>}
            <button
              onClick={handleSave}
              disabled={saving || !isDirty}
              className="px-4 py-2 rounded-lg bg-[#4272A5] text-white text-sm font-semibold disabled:opacity-40 hover:bg-[#2d5580] transition-colors"
            >
              {saving ? 'Guardando…' : 'Guardar y aplicar en Authentik'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
