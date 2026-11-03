# Reporte de mejoras UI en pantallas de Authentik (para portar a otra instancia)

**Origen:** instancia `/opt/ecosistema-casmarts` (core-casmarts + Login Manager/Designer)
**Fecha del reporte:** 2026-10-30
**Alcance:** solo mejoras genéricas de UI/UX de Authentik (sombras, bordes, textos encimados,
mensajes, responsividad, traducciones). **No incluye** logos, imágenes ni branding de proyecto.

---

## 0. Dónde viven los cambios (lo primero que hay que ubicar en la otra instancia)

Authentik se personaliza con **dos motores independientes**. Hay que portar las mejoras a ambos.

| Motor | Archivo en esta instancia | Qué pantallas cubre |
|---|---|---|
| SPA (web components) | `core-casmarts/data/authentik/custom-templates/if/flow.html` (montado en `/authentik/flows/templates/if/flow.html`) | Login, password, recuperación, MFA, consent, acceso denegado dentro del flow |
| Plantilla generadora | `authentik-login-manager/backend/app/templates/login.html.j2` (y la del designer) | **Regenera** `flow.html` en cada deploy del Login Manager/Designer |
| SSR (gateway nginx) | `core-casmarts/gateway/static/custom_authentik.css` + `custom_authentik.js` (inyectado con `sub_filter` en `</head>`) | Páginas server-rendered, p. ej. "Permiso denegado" en `/application/o/authorize/` |

> ⚠️ Si solo se edita `flow.html`, el siguiente deploy del Login Manager lo sobrescribe.
> Aplicar los cambios en `login.html.j2` (y copiar a `flow.html`) — en esta instancia los
> tres archivos son idénticos (misma md5).
>
> ⚠️ Al editar `custom_authentik.js`, subir el `?v=` en `gateway/sites-enabled/subdomains.conf`
> y luego `nginx -s reload`; si no, el navegador sigue usando el JS en caché.

---

## 1. Campo de contraseña + botón "ojo" (sin redondeo en la unión)

**Problema:** el input y el botón de mostrar contraseña tenían cada uno sus 4 esquinas
redondeadas y una sombra/borde PatternFly; en la unión se veía un "pellizco" redondeado,
doble borde y un halo de foco que solo envolvía al input.

**Solución:** tratar `.pf-c-input-group` como una sola pieza:
- Input: radio solo a la izquierda (`8px 0 0 8px`), sin borde derecho.
- Botón: radio solo a la derecha (`0 8px 8px 0`), borde izquierdo fino de 1px como divisor,
  mismo fondo que el input, sin `::after` (PatternFly dibuja ahí un borde extra).
- Foco: `:focus-within` en el grupo pinta el borde de **ambos** con el color de foco, sin sombra.
- Si el input está solo (`:only-child`), recupera los 4 radios y su borde derecho.

```css
.pf-c-input-group{display:flex!important;width:100%!important;align-items:stretch!important;position:relative!important;border-radius:8px!important;box-shadow:none!important;outline:none!important;box-sizing:border-box!important}
.pf-c-input-group>.pf-c-form-control,
.pf-c-input-group>input:not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]):not([type=range]){
  flex:1 1 auto!important;width:0!important;min-width:0!important;
  border-radius:8px 0 0 8px!important;
  border-top-right-radius:0!important;border-bottom-right-radius:0!important;
  border:1.5px solid #d1d5db!important;border-right:none!important;
  background:var(--cs-input-bg,#fff)!important;box-shadow:none!important;outline:none!important}
.pf-c-input-group>.pf-c-button,.pf-c-input-group>button{
  flex:0 0 auto!important;margin:0!important;
  border-radius:0 8px 8px 0!important;
  border-top-left-radius:0!important;border-bottom-left-radius:0!important;
  border:1.5px solid #d1d5db!important;border-left:1px solid #d1d5db!important;
  background:var(--cs-input-bg,#fff)!important;color:#4b5563!important;
  padding:0 .85rem!important;display:flex!important;align-items:center!important;justify-content:center!important;
  box-shadow:none!important;outline:none!important;transition:background-color .2s,color .2s!important}
.pf-c-input-group>.pf-c-button:hover,.pf-c-input-group>button:hover{background-color:#f9fafb!important;color:#111827!important}
.pf-c-input-group>.pf-c-button::after,.pf-c-input-group>button::after{display:none!important;content:none!important;border:none!important}
.pf-c-input-group:focus-within{box-shadow:none!important;outline:none!important}
.pf-c-input-group:focus-within>.pf-c-form-control,
.pf-c-input-group:focus-within>input,
.pf-c-input-group:focus-within>.pf-c-button,
.pf-c-input-group:focus-within>button{border-color:var(--cs-focus-border,var(--cs-btn))!important;box-shadow:none!important;outline:none!important}
.pf-c-input-group>:only-child,
.pf-c-input-group>input:only-child{border-radius:8px!important;border-right:1.5px solid #d1d5db!important}
```

**Dónde aplicarlo (las 3 copias):**
1. Array `ECSS` del script `casmarts-shadow-intercept` en `flow.html` (se inyecta en cada shadow root `ak-*`).
2. CSS dinámico de `csInjectShadow`/`processRoot` en `flow.html` (usa `${inputBg}`/`${focusBorder}` del theme).
3. `custom_authentik.css` del gateway (páginas SSR) + su variante en el bloque `prefers-color-scheme: dark`.

**Mostrar/ocultar el ojo:** el botón real vive en el web component Lit `ak-flow-input-password`
(Shadow DOM), así que **ocultarlo por CSS no funciona**. El Login Manager lo controla vía API:
`_sync_password_toggle()` en `backend/app/routers/admin.py` hace `PATCH` a
`PasswordStage.allow_show_password` en cada deploy. Portar esa función si la otra instancia
tiene el switch "mostrar contraseña" en el editor.

---

## 2. Inputs: sin sombras, foco limpio, autofill sin fondo amarillo/azul

```css
.pf-c-form-control,input:not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]){
  border-radius:8px!important;border:1.5px solid #d1d5db!important;background:#fff!important;
  box-shadow:none!important;outline:none!important;color:#111827!important;
  font-size:.9rem!important;padding:.6rem .85rem!important;box-sizing:border-box!important}
input:focus,input:focus-visible,.pf-c-form-control:focus{
  box-shadow:none!important;outline:none!important;
  border-color:var(--cs-focus-border,var(--cs-btn))!important;
  caret-color:var(--cs-focus-border,var(--cs-btn))!important}
/* Autofill de Chrome/Edge: tapa el fondo con una sombra inset del color del input */
input:-webkit-autofill,input:-webkit-autofill:hover,input:-webkit-autofill:focus,
input:-webkit-autofill:active,input:-internal-autofill-selected{
  -webkit-box-shadow:0 0 0 1000px #fff inset!important;box-shadow:0 0 0 1000px #fff inset!important;
  -webkit-text-fill-color:#111827!important;caret-color:#111827!important;
  transition:background-color 50000s ease-in-out 0s,color 50000s ease-in-out 0s!important}
```

Botón primario: `border-radius:8px; box-shadow:none; text-shadow:none; width:100%`, y en `:focus`
un anillo suave `box-shadow:0 0 0 3px <primario>40` (accesible, sin sombra en reposo).

---

## 3. Eliminar la "tarjeta dentro de tarjeta" (sombras y bordes nativos de PatternFly)

**Problema:** Authentik pinta su propio card (`.pf-c-login__main`, `.pf-c-card`, `ak-flow-card`)
con sombra, borde, fondo y padding; dentro de nuestro card se veía un segundo recuadro con sombra.

**Solución (3 capas, porque Shadow DOM bloquea selectores normales):**
1. **Variables CSS** en el light DOM (atraviesan el Shadow DOM sin JS):
   `--pf-c-login__main--BoxShadow:none`, `--pf-c-card--BoxShadow:none`,
   `--pf-global--BoxShadow--{sm,md,lg,xl}[-top]:none`, `--pf-c-login__main--BorderRadius:0`,
   `--pf-c-*--Padding*:0`, `--pf-c-login--BackgroundColor:transparent`.
2. **CSS inyectado en cada shadow root** (`ECSS`): `:host, ak-flow-card, .pf-c-login, .pf-c-login__main,
   .pf-c-card, .pf-c-panel` → `box-shadow:none; border:none; border-radius:0; background:transparent;
   filter:none; backdrop-filter:none`, más `::before/::after { content:none }` (PatternFly dibuja
   bordes con pseudo-elementos).
3. **Respaldo JS** `removeBoxShadows()` dentro de un `scan()` que recorre todos los shadow roots
   cada 400 ms + `MutationObserver` (los observers no ven dentro de shadow roots).

La inyección se hace interceptando `customElements.define` **antes** de que cargue
`FlowInterface.js`, parcheando `connectedCallback` de todo elemento `ak-*` → el CSS está presente
desde el primer render (sin parpadeo; necesario en Firefox/Edge).

---

## 4. Textos encimados / footer superpuesto ("Aviso de privacidad" vs "¿Olvidaste tu contraseña?")

**Problema:** con contenido largo o pantallas bajas, el footer quedaba encima del link
"¿Olvidaste tu contraseña?" y no aparecía scroll.

**Causa raíz:** el wrapper del executor tenía `flex: 1 1 0` → se comprimía más chico que el
formulario, el form se desbordaba (overflow visible), el contenedor "creía" que todo cabía y
nunca activaba el scroll.

**Solución — estructura del panel del formulario:**
```
#cs-form-col      (flex column, overflow:hidden — no scrollea)
  #cs-scroll-area (flex:1 1 auto; min-height:0; overflow-y:auto)  ← ÚNICO que scrollea
    título, subtítulo, mensajes, #cs-executor-wrap (flex:0 0 auto — mide su contenido)
  #cs-privacy     (flex:0 0 auto; background:transparent)         ← footer siempre visible
```
- `#cs-executor-wrap { flex:0 0 auto; transform:translateZ(0); isolation:isolate; contain:layout style; }`
  (el `translateZ/contain` crea containing block propio: contiene los `position:fixed` del shadow
  DOM en Firefox/Edge).
- `#cs-privacy` **sin background propio**: con `var(--cs-card-bg)` se apilan dos capas
  semitransparentes y la franja se ve más blanca.
- Scrollbar fino: `::-webkit-scrollbar{width:6px}`, thumb `rgba(0,0,0,.15)` con radio 10px.
- **NO** volver a `flex:1 1 0` en el wrapper (regresión recurrente).

---

## 5. Mensajes de error visibles (recuadro rojo vacío)

**Problema:** en login fallido aparecía el recuadro rojo **sin texto**, y en el 2º intento nada.

**Causas raíz (dos):**
1. Regla `p:not(.pf-c-form__helper-text){display:none}` (para ocultar la descripción redundante
   del stage) ocultaba también el `<p>` del error. En Authentik 2026.2 el error **no** es
   `.pf-c-alert`: es `<ak-empty-state><div slot="body"><p>mensaje</p></div>` y los de campo son
   `p.pf-c-form__helper-text.pf-m-error`.
2. Función JS `setupErrorCleaner()` ponía `display:none` **inline !important** en errores al
   hacer `focusin`; el campo de contraseña se autoenfoca tras el error → desaparecía al instante.
   Un inline `!important` puesto por JS no se puede revertir con ninguna hoja de estilo.

**Solución:**
- Añadir exclusiones a **todas** las copias del selector:
  `p:not(.pf-c-form__helper-text):not(.pf-c-alert__title):not(.pf-c-alert__description):not([class*='alert']):not([class*='error'])`
- Override de mayor especificidad que re-muestra el error:
  ```css
  ak-empty-state [slot='body'],ak-empty-state [slot='body'] *,
  .pf-c-form__helper-text.pf-m-error,p.pf-m-error{display:revert!important;visibility:visible!important;opacity:1!important;height:auto!important;overflow:visible!important}
  ak-empty-state [slot='body'] p,.pf-c-form__helper-text.pf-m-error{color:#b1151c!important;font-size:.9rem!important}
  @media (prefers-color-scheme:dark){ak-empty-state [slot='body'] p,.pf-c-form__helper-text.pf-m-error{color:#ff6b6b!important}}
  ```
- Dejar `setupErrorCleaner()` como **no-op** (`return;`) en **ambos** motores (flow.html y
  custom_authentik.js tenían copias gemelas). El error se limpia solo al re-renderizar el stage.
- Respaldo JS `showErrors()` en el `scan()` periódico fuerza visibles `.pf-c-alert__title`,
  `.pf-c-alert__description`, `.pf-m-error`.

---

## 6. Ocultar textos redundantes de Authentik

- Header nativo (`ak-brand`, `.pf-c-brand`, `h1`, `h2`, `.pf-c-title`, `.pf-c-login__main-header`,
  `[slot='description']`) y `.pf-c-login__footer` ("Powered by authentik") → `display:none`.
- Selector de idioma nativo (`ak-locale-select`, `[aria-label*="language" i]`, …) → oculto.
- **"Inicia sesión para continuar a X" / "Login to continue to X"** (aparece solo en el login de
  una app con `client_id`): vive en `<form class="pf-c-form"> > <p>` dentro del shadow root de
  `ak-stage-identification`, **no** bajo `.pf-c-login__main-body`. Se oculta en el `scan()` por
  **texto**, que es seguro (ningún error empieza así):
  ```js
  root.querySelectorAll('p').forEach(function(p){
    var t=(p.textContent||'').trim();
    if(/^Inicia sesión para continuar/i.test(t)||/^Log ?in to continue/i.test(t)){
      p.style.setProperty('display','none','important');
      p.style.setProperty('height','0','important');
      p.style.setProperty('margin','0','important');
      p.style.setProperty('padding','0','important');
    }
  });
  ```

---

## 7. Textos informativos invisibles con modo oscuro del sistema

**Problema:** con el SO en modo oscuro, Authentik pinta textos con `--pf-global--Color--100/200/300`
casi blancos → invisibles sobre la tarjeta clara (p. ej. la descripción de "¿Olvidaste tu contraseña?").

**Solución:** forzar un color legible configurable sin pisar el rojo de errores:
```css
:host{--pf-global--Color--100:var(--cs-body-text,#374151)!important;--pf-global--Color--200:var(--cs-body-text,#374151)!important;--pf-global--Color--300:var(--cs-body-text,#374151)!important}
.pf-c-login__main-body,.pf-c-form,.pf-c-content,.pf-c-content p,
.pf-c-form__helper-text:not(.pf-m-error),.pf-c-check__label,.pf-c-radio__label,.pf-c-form__group-label-help,
p:not(.pf-m-error):not([class*='error']):not([class*='alert']):not(ak-empty-state *){color:var(--cs-body-text,#374151)!important}
```
Colocarlo **antes** del override de error para que el rojo gane. Variables de tema en `:root`
con su bloque `@media (prefers-color-scheme: dark)` (`--cs-text-primary`, `--cs-text-secondary`,
`--cs-error-text`, `--cs-card-bg`) y overlay de fondo más oscuro en dark (`rgba(0,0,0,.4)`).

---

## 8. Pantalla "Permiso denegado" (acceso denegado)

| Síntoma | Causa | Arreglo |
|---|---|---|
| Se veía Authentik sin personalizar ("pantalla azul") | `inject()` tenía lista blanca de 4 tags; `ak-stage-access-denied`/`ak-stage-consent` no recibían CSS | Cambiar la lista blanca por chequeo de prefijo: inyectar en todo host cuyo tag empiece con `ak-` |
| Botón "Ir al inicio" pegado/recortado contra el borde inferior (SPA) | `--pf-c-login__main-body--PaddingBottom:0` se hereda al shadow de `ak-flow-card` | En ese card únicamente: `--pf-c-login__main-body--PaddingBottom:1.5rem` y `--pf-c-login__main--PaddingBottom:1.5rem` inline |
| Mismo botón recortado (SSR, `/application/o/authorize/`) | `.pf-c-login__main` con `overflow:hidden` es flex-item constreñido a menos alto que su contenido | `card.style.overflow='visible' !important` y `padding-bottom:1.5rem` en `.pf-c-login__main-body` (no usar márgenes ni `height:auto`) |
| "Ir al inicio" en **loop infinito** | `cancelUrl`/`/` reintenta el authorize del usuario ya autenticado → denegado otra vez | Reescribir el `href` del botón (`a.pf-c-button` en SPA, `#ak-back-home` en SSR) a `/if/flow/default-invalidation-flow/` (logout → login) |

---

## 9. Responsividad (logos/botón invisibles en laptops 1366×768)

- Breakpoint "móvil" bajado de `768px` a **`480px`**: un laptop 1366px con escalado Windows
  200% reporta viewport de 683px y caía en el layout móvil (ocultaba panel y recortaba el botón).
- Breakpoint intermedio **`920px`** (tablet): card en columna, `max-width:600px`, `height:90vh`,
  panel lateral `max-height:200px`; móvil `max-height:150px` y título `1.4rem`.
- Card principal con límites para no desbordar: `width:820px; max-width:90vw; height:70vh;
  min-height:560px; max-height:620px`; card sin panel lateral `width:420px`.
- El scroll de seguridad lo da `#cs-scroll-area` (punto 4), por eso `body` puede quedar en
  `overflow:hidden` sin perder acceso al botón.

---

## 10. Traducciones al español faltantes

Diccionario `TRANSLATIONS` aplicado por `translateNode()` a nodos de texto y `placeholder`
(también dentro de shadow roots, vía el `MutationObserver` de `inject()` con `characterData:true`):
- "Failed to authenticate." → "Error de autenticación."
- "Password recovery" → "Recuperación de contraseña", y descripciones de identificación.
- **~30 mensajes de zxcvbn** (fortaleza de contraseña: "Straight rows of keys are easy to guess",
  "This is a top-10 common password", "Avoid sequences", …) — no vienen del catálogo i18n de
  Authentik, por eso llegaban en inglés. Copiar el bloque completo de `flow.html` (líneas ~618-654).

---

## Checklist de verificación tras portar

- [x] Login con **contraseña incorrecta** → el texto del error se ve (1º y 2º intento), en claro y oscuro. _(Playwright, 2026-10-30: desktop/teléfono/oscuro, "Error de autenticación." visible y traducido)_
- [x] Unión input/ojo sin redondeo ni doble borde; al enfocar, borde de color en ambos. _(visual OK en capturas de login)_
- [x] Autofill del navegador no cambia el fondo del input. _(regla agregada, claro y oscuro, en ambos motores)_
- [x] Sin segundo recuadro/sombra dentro del card en login, password, recuperación y MFA. _(consent no se pudo forzar — ver detalle arriba; mismo mecanismo CSS genérico ya verificado en los demás stages)_
- [x] Contenido largo (recuperación, MFA): aparece scroll interno y el footer no se encima. _(verificado con la query de altura corta + scrollIntoView)_
- [x] Login de una app (`?client_id=…`): no aparece "Inicia sesión para continuar a X". _(Playwright, escritorio y teléfono, branding "Starter" correcto)_
- [x] "Permiso denegado": con estilo, botón con aire inferior y sin loop (SPA y SSR). _(Playwright con usuario de prueba real, 4 viewports — ver sección de arriba; encontró y corrigió 2 bugs nuevos: footer sin ocultar y tarjeta sin centrar)_
- [x] 1366×768 con escalado 150–200 %: botón de iniciar sesión alcanzable. _(equivalente al viewport 683×768 ya probado — el escalado del SO solo cambia el innerWidth CSS reportado)_
- [x] SO en modo oscuro: textos informativos legibles. _(Playwright `colorScheme:'dark'`, inputs oscuros confirmados visualmente)_
- [x] `login.html.j2` actualizado (si no, el próximo deploy revierte `flow.html`); `?v=` del
      gateway incrementado y `nginx -s reload`. _(los 3 `flow.html`-gemelos en sync; `?v=20261030_v17`)_

## Referencias en esta instancia
- `.agent/ARCHITECTURE_CSS_RULES.md`, `.agent/ARCHITECTURE_BRANDING.md`
- `.agent/DECISIONS/0004-incidente-login-css-mensajes-error-ocultos-y-regresiones.md`

---

## Addendum 2026-10-30 — qué de este reporte faltaba portar AQUÍ, y responsividad

Se revisó esta misma instancia contra las 10 secciones de arriba. Resultado: los puntos
**4, 5, 6, 8, 9 y 10 ya estaban aplicados** (de hecho esta instancia es el origen de esos
arreglos). Lo que **faltaba** y se aplicó hoy a los 3 archivos (`flow.html` +
`authentik-login-manager/.../login.html.j2` + `authentik-login-designer/.../login.html.j2`,
mismo texto en los tres) y a `core-casmarts/gateway/static/custom_authentik.css`:

- **Punto 1 (input/ojo):** la versión aquí no tenía `:focus-within` (el halo de foco se
  cortaba en la unión con el botón), ni quitaba el `::after` de PatternFly, ni tenía
  variante de modo oscuro para el botón. Subido al mismo nivel que el reporte describe.
- **Punto 2 (autofill):** no existía en ningún motor — el autofill de Chrome/Edge pintaba
  el input con su amarillo/azul nativo. Agregado (claro y oscuro) en los 3 `flow.html`
  gemelos, en el array `ECSS`, y en `custom_authentik.css`.
- **Punto 7 (texto en modo oscuro):** la plantilla dinámica de `flow.html`
  (`csInjectShadow`) no tenía variante oscura para `.pf-c-form-control` — pisaba SIEMPRE
  el fondo oscuro que `ECSS` aplicaba antes de que cargara el tema real, dejando los
  inputs claros con el SO en oscuro. Se agregó su `@media (prefers-color-scheme: dark)` y
  el override de `--pf-global--Color--100/200/300` (reutiliza `--cs-text-secondary`, ya
  existente). `custom_authentik.css` **ya** cubría esto razonablemente — no se tocó.

### Responsividad tablet/teléfono — dos bugs nuevos encontrados y corregidos

1. **`flow.html`: `#cs-screen` se desbordaba horizontalmente en teléfonos.** No tenía
   `box-sizing: border-box`; el breakpoint de 480px le agrega `padding: 1rem !important`
   que, en `content-box`, se SUMA al `max-width` en vez de restarse — en un iPhone de
   375px de ancho el card terminaba renderizando ~391px, más ancho que la pantalla.
   Arreglo: reset universal `*, *::before, *::after { box-sizing: border-box; }`.
2. **`flow.html`: tarjeta recortada sin scroll en teléfonos en horizontal / ventanas
   bajas.** El `min-height` fijo (560/500/450px según breakpoint de ANCHO) puede superar
   la altura REAL del viewport — un teléfono en horizontal (altura ~375-430px) no
   calificaba para el breakpoint de 480px (su ancho es >480) y quedaba con
   `min-height: 500px` de la regla de tablet, desbordando el viewport. Con `body`
   en `overflow: hidden` no había forma de alcanzar el botón recortado. Arreglo: nueva
   regla `@media (max-height: 560px)` (independiente del ancho) que relaja el
   `min-height` a 0 y limita la altura a `92dvh`. Se agregó `dvh` como mejora adicional
   en los 3 breakpoints de altura (con `vh` de fallback) para evitar saltos de layout
   cuando el navegador móvil oculta/muestra su barra de direcciones.
3. **`custom_authentik.css`/`custom_authentik.js` (motor SSR): el layout de dos paneles
   recortaba el card en tablets de 768px exactos (ej. iPad en vertical).** El breakpoint
   de "desktop" estaba en `768px` con el card centrado en `left: 25%` + ancho fijo de
   420px — en un viewport de 768px el centro del panel queda a 192px del borde, 18px
   MENOS que la mitad del card (210px), y el borde izquierdo se recorta por el
   `overflow: hidden` del contenedor. Mismo error de fondo que el que ya se había
   corregido en `flow.html` con su breakpoint de 920px (no asumir que "tablet" empieza
   en 768px). Subido a `860px` en `custom_authentik.css` (2 ocurrencias) y en la
   constante `BREAK_PX` de `custom_authentik.js` — deben moverse juntos.

### Bug de caché adicional corregido de paso
`custom_authentik.css` se inyectaba siempre desde la misma URL sin `?v=`, a diferencia
del propio `custom_authentik.js` — el navegador podía quedarse indefinidamente con una
copia vieja del CSS aunque el archivo cambiara en el servidor. Ahora usa
`custom_authentik.css?v=<CSS_VERSION>` (constante en `custom_authentik.js`, súbanla junto
con el `?v=` del script en `subdomains.conf`).

**Aplicado y verificado en vivo (sin reiniciar contenedores — bind mounts):**
`?v=` subido a `20261030_v15` en las 4 ocurrencias de `subdomains.conf`,
`nginx -s reload` en `casmarts-core-gateway`, y confirmado con `curl` contra
`auth.casmart.internal` que la plantilla y los estáticos ya sirven el contenido nuevo.
`login.html.j2` de Login Manager y de Login Designer actualizados con los mismos
cambios — siguen siendo copias byte-idénticas de `flow.html` salvo el drift histórico ya
conocido (sistema de fuentes propias y `applyFavicon`, exclusivos de Login Manager).

**Prueba visual real (2026-10-30, mismo día):** se corrió Playwright
(`mcr.microsoft.com/playwright:v1.48.0-jammy`) contra `auth.casmart.internal` en vivo, en
7 tamaños de viewport (teléfono vertical/horizontal 375×667 y 667×375, teléfono ancho
horizontal 812×375, tablet vertical/horizontal 768×1024 y 1024×768, laptop con escalado
683×768, desktop 1440×900), midiendo overflow horizontal real (`scrollWidth`) y si el
botón de submit es alcanzable (con `scrollIntoView` primero, para no confundir "está
debajo del pliegue de `#cs-scroll-area`, alcanzable con scroll" con "está fuera del
viewport, inalcanzable" — son cosas distintas).

**Encontró un bug nuevo, no descrito en ningún punto de arriba:** `#cs-screen.cs-left` /
`.cs-right` traen `left: 6vw` / `right: 6vw !important` (pensado para el layout de
escritorio de dos paneles) que los breakpoints de 920px/480px nunca limpiaban al apilar
el layout en una sola columna. Con `layout_position: "left"` — el valor por default de
`TenantTheme` en la base de datos, es decir el caso más común — la tarjeta quedaba
descentrada y su borde derecho se salía unos px del viewport en teléfonos reales (en
375px de ancho: ~3.75px de overflow horizontal, confirmado con Playwright, invisible a
simple vista pero generaba una barra de scroll horizontal fantasma). Arreglo: dentro de
ambos breakpoints, forzar `#cs-screen.cs-left, #cs-screen.cs-right, #cs-screen.cs-center
{ left: 50% !important; right: auto !important; transform: translate(-50%, -50%)
!important; }` — por debajo de 920px el layout siempre está apilado, así que centrar
siempre es correcto sin importar qué `layout_position` tenga el tema. Aplicado a los 3
`flow.html`-gemelos, verificado en vivo con `curl` y con Playwright: los 7 viewports
pasan limpio después del arreglo (capturas en el repo del agente que lo corrió, no en
este repositorio).

Este bug es candidato a existir también en la instancia Kardex (de donde vino el
reporte original) si su `TenantTheme` por default también usa `layout_position: "left"`
— vale la pena revisarlo allá.

### Prueba de "Permiso denegado" (2026-10-30, mismo día) — dos bugs más, en `custom_authentik.css`

Se creó un usuario de prueba temporal sin acceso a ninguna app (`ak shell`,
borrado al terminar) y se forzó el rechazo real pegándole a
`/application/launch/starter/` autenticado con ese usuario, en 4 viewports
(desktop, teléfono 375px, tablet 768px, tablet 860px) vía Playwright.

1. **"Powered by authentik" visible, sin estilo, flotando en el panel derecho.**
   `flow.html` ya oculta `.pf-c-login__footer`, pero `custom_authentik.css`
   (que es lo que SÍ carga esta página, al no tener `#cs-screen`) solo
   ocultaba `.pf-c-login__header` — nunca el footer. Agregada la misma regla
   `display:none` para `.pf-c-login__footer`.
2. **La tarjeta no se centra verticalmente en NINGÚN ancho menor a 860px —
   queda pegada arriba, con un hueco vacío abajo.** No es un caso raro ni
   nuevo de hoy: afecta a cualquier teléfono o tablet, en cualquier fecha,
   desde que existe esta página. Causa raíz: Authentik define `.pf-c-login`
   nativamente como **CSS Grid** (`grid-template-rows: header/main/footer`),
   no flexbox. Nuestro `.pf-c-login{display:flex!important}` gana la pelea
   de especificidad, pero `.pf-c-login__main` conserva un `align-self:start`
   nativo (pensado para el grid original) que un simple `align-items:center`
   del padre no puede pisar (`align-self` del hijo siempre gana sobre
   `align-items` del padre) — y por la misma razón `justify-content:center`
   tampoco centraba verticalmente. Confirmado forzando manualmente
   `align-self`/`margin:auto` vía Playwright antes de concluir la causa.
   Arreglo: en vez de pelear con flex/grid, centrar `.pf-c-login__main` con
   `position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)` —
   mismo patrón que `#cs-screen` en `flow.html`, no depende de qué sistema
   de layout use el padre. Verificado con Playwright en los 4 viewports:
   centrado perfecto, sin overflow, botón con buen margen, sin "powered by".

Subido `CSS_VERSION`/`?v=` a `20261030_v17` (dos bumps, uno por cada hallazgo),
`nginx -s reload`. Ninguno de los dos bugs es específico del cambio de
breakpoint 768→860 — existían en TODOS los anchos móviles desde siempre;
candidatos claros a revisar también en Kardex si usa el mismo
`custom_authentik.css` base.

### Resto del checklist completado (2026-10-30, mismo día)

Con usuarios de prueba temporales (creados y borrados vía `ak shell`; 0 residuos
confirmado al final: `User.objects.filter(username__startswith='qa_').count()` → 0):

- **Recuperación de contraseña** (`/if/flow/password-recovery/`): sin doble sombra,
  sin desborde, escritorio y teléfono — limpio.
- **Login de una app con tema propio** (`?client_id=...` de `starter`): branding
  correcto (logo/subtítulo "Starter"), "Inicia sesión para continuar a X" correctamente
  ausente, escritorio y teléfono.
- **MFA (validación TOTP)**: se creó un usuario con un `TOTPDevice` confirmado
  (secreto aleatorio, sin exponerlo) para forzar que el stage de validación
  apareciera (`not_configured_action: skip` lo salta si el usuario no tiene
  dispositivo). Pantalla "Código de autenticación" limpia, sin desborde, sin doble
  sombra, en escritorio y teléfono.
  - **Hallazgo nuevo:** el texto de ayuda "Open your authenticator app to retrieve
    a one-time use code." y el placeholder "Type an authentication code..." nunca
    habían estado en español — se agregaron al diccionario `TRANSLATIONS`.
- **Consentimiento explícito**: se intentó con Wiki.js (`default-provider-
  authorization-explicit-consent`, modo `expiring`, usuario de prueba sin
  consentimientos previos) — Authentik lo saltó igual, sin que se identificara la
  causa exacta (no es prioritario perseguirla: el CSS que protege ese stage es el
  mismo mecanismo genérico por prefijo `ak-*` ya verificado en identification/
  password/MFA, no una regla aparte). **Pantalla no verificada visualmente.**
- **1366×768 con escalado 150-200%**: no se repitió con el emulador de zoom real de
  Chrome — es equivalente al viewport "laptop-scaled" (683×768) ya probado hoy, que
  pasó limpio. El escalado del SO solo cambia el `window.innerWidth` CSS reportado,
  que es exactamente lo que ese viewport ya simula.
- **Traducción "Correo or Nombre usuario" → "Correo o nombre de usuario":**
  Authentik concatena los campos configurados del stage de identificación con
  `" or "` sin traducir (no viene del catálogo i18n que sí cubre el resto del
  stage). Se agregaron 4 entradas a `TRANSLATIONS` (orden correo/usuario y
  usuario/correo, en español e inglés) — cubre label y placeholder porque
  comparten el mismo nodo de texto. Verificado en vivo tras el cambio.
- **Recuadro de error en modo oscuro — revisado, NO se portó el fix de Kardex.**
  Kardex tenía fondo casi negro + texto oscuro (ilegible). Aquí el texto del error
  en modo oscuro ya es `#ff6b6b` (rojo claro) desde el arreglo original — confirmado
  legible en la captura `shot-fail2-desktop-dark.png` de la prueba de login fallido
  de hoy. Forzar el mismo fondo rosa claro de Kardex aquí sería una regresión: nuestras
  tarjetas y campos son oscuros en modo oscuro por diseño (a diferencia de Kardex,
  que los mantiene claros siempre), así que un recuadro claro desentonaría sin
  resolver ningún problema real.
