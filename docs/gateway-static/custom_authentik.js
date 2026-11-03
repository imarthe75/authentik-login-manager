/**
 * CASmartS — Authentik Layout & Branding Engine (Dynamic Version)
 * Construye el layout split-screen de forma dinámica y reactiva
 * consumiendo el REST API de authentik-login-manager.
 */
(function () {
    const STYLE_ID   = 'casmarts-custom-style';
    const DYNAMIC_STYLE_ID = 'casmarts-dynamic-style';
    const PANEL_ID   = 'cs-left-panel';
    const LOGO_ID    = 'casmarts-logo-branding';
    // 860, no 768: con el card de 420px centrado en left:25%/75%, un
    // viewport <840px deja el centro del panel a menos de la mitad del
    // ancho del card del borde — en un iPad en vertical (768px, el caso
    // real mas comun) el borde del card queda recortado por el
    // overflow:hidden del contenedor. Debe coincidir con el @media de
    // custom_authentik.css (ver su comentario junto al breakpoint).
    const BREAK_PX   = 860;
    // custom_authentik.css se servía siempre desde la misma URL sin query
    // string, a diferencia de este propio script (que SÍ se cachea con
    // ?v= en subdomains.conf) — el navegador podía quedarse indefinidamente
    // con una copia vieja del CSS aunque el archivo cambiara. Mismo valor
    // que el ?v= de este script en subdomains.conf; súbelo junto con ese.
    const CSS_VERSION = '20261103_v18';

    // Obtener variables de contexto de la URL
    const url = new URL(window.location.href);
    let flowSlug = 'default-authentication-flow';
    const pathParts = url.pathname.split('/');
    const flowIndex = pathParts.indexOf('flow');
    if (flowIndex !== -1 && pathParts[flowIndex + 1]) {
        flowSlug = pathParts[flowIndex + 1];
    }
    const clientId = url.searchParams.get('client_id') || window.__CASMARTS_APP_HINT__ || '';

    // Iniciar fetch de configuración de tema inmediatamente
    const themeApiUrl = `/lm/api/v1/public/theme/${flowSlug}${clientId ? '?app=' + clientId : ''}`;
    let themeConfig = null;
    let themeLoaded = false;
    let disableBranding = false;

    fetch(themeApiUrl)
        .then(res => {
            if (!res.ok) throw new Error('Theme API response error');
            return res.json();
        })
        .then(data => {
            if (data && data.is_custom === false) {
                console.log('[CASmartS] Standard/default theme requested, disabling custom theme layout.');
                disableBranding = true;
                const executor = document.querySelector('ak-flow-executor');
                if (executor && executor.shadowRoot) {
                    executor.shadowRoot.querySelectorAll('#' + STYLE_ID + ', #' + DYNAMIC_STYLE_ID + ', #' + LOGO_ID).forEach(el => el.remove());
                }
                if (executor) {
                    document.body.appendChild(executor);
                    executor.style.cssText = '';
                    executor.classList.add('pf-c-login');
                }
                document.querySelectorAll('#' + STYLE_ID + '-global, style[data-id="casmarts-branding"], #cs-bg, #cs-bg-overlay, #cs-screen').forEach(el => el.remove());
                document.body.style.cssText = '';
                document.documentElement.style.cssText = '';
                return;
            }
            themeConfig = data;
            themeLoaded = true;
            console.log('[CASmartS] Dynamic theme successfully loaded:', themeConfig);
            if (themeConfig.has_favicon) {
                const faviconUrl = `/lm/api/v1/public/theme/${flowSlug}/image/favicon${clientId ? '?app=' + clientId : ''}`;
                let favEl = document.querySelector('link[rel*="icon"]');
                if (!favEl) {
                    favEl = document.createElement('link');
                    favEl.rel = 'shortcut icon';
                    document.head.appendChild(favEl);
                }
                favEl.href = faviconUrl;
            }
            applyDynamicStyles();
        })
        .catch(err => {
            console.error('[CASmartS] Error loading dynamic theme, using standard styles:', err);
        });

    /* ── 1. Inyectar stylesheet base ──────────────────────────────── */
    function injectStyle(root) {
        if (root.querySelector('#' + STYLE_ID)) return;
        const link  = document.createElement('link');
        link.id     = STYLE_ID;
        link.rel    = 'stylesheet';
        link.href   = '/static/custom_authentik.css?v=' + CSS_VERSION;
        root.appendChild(link);
    }

    /* ── 2. Inyectar styles dinámicos custom ──────────────────────── */
    function injectDynamicStyle(root, theme) {
        let styleTag = root.querySelector('#' + DYNAMIC_STYLE_ID);
        if (!styleTag) {
            styleTag = document.createElement('style');
            styleTag.id = DYNAMIC_STYLE_ID;
            root.appendChild(styleTag);
        }

        const primary = theme.primary_color || '#4272A5';
        const hover = theme.hover_color || '#2d5580';
        const cardBg = theme.card_bg_color || 'rgba(255, 255, 255, 0.72)';
        const panelBg = theme.panel_bg_color || 'rgba(246, 249, 253, 0.92)';

        let bgRule = '';
        if (theme.has_bg_image) {
            const bgUrl = `/lm/api/v1/public/theme/${flowSlug}/image/bg_image${clientId ? '?app=' + clientId : ''}`;
            bgRule = `background-image: url("${bgUrl}") !important;`;
        } else if (theme.bg_type === 'flat' && theme.bg_flat_color) {
            bgRule = `background-image: none !important; background-color: ${theme.bg_flat_color} !important;`;
        } else if (theme.bg_type === 'gradient' && theme.bg_gradient_from && theme.bg_gradient_to) {
            bgRule = `background-image: linear-gradient(135deg, ${theme.bg_gradient_from}, ${theme.bg_gradient_to}) !important;`;
        }

        // Determinar estilo de alineación de pantalla sin alterar DOM
        let positionCss = '';
        const isCustomFlowTemplate = document.getElementById('cs-screen') !== null;

        if (window.innerWidth >= BREAK_PX && !isCustomFlowTemplate) {
            if (theme.layout_position === 'right') {
                positionCss = `
                    .pf-c-login::before {
                        inset: 0 0 0 auto !important;
                        width: 50% !important;
                        height: 100% !important;
                        background: ${panelBg} !important;
                        backdrop-filter: blur(28px) !important;
                        -webkit-backdrop-filter: blur(28px) !important;
                    }
                    .pf-c-login__main {
                        position: fixed !important;
                        left: 75% !important;
                        top: 50% !important;
                        transform: translate(-50%, -50%) !important;
                        margin: 0 !important;
                    }
                `;
            } else if (theme.layout_position === 'center') {
                positionCss = `
                    .pf-c-login::before {
                        display: none !important;
                    }
                    .pf-c-login__main {
                        position: relative !important;
                        margin: 0 auto !important;
                    }
                `;
            } else {
                // left (default)
                positionCss = `
                    .pf-c-login::before {
                        inset: 0 auto 0 0 !important;
                        width: 50% !important;
                        height: 100% !important;
                        background: ${panelBg} !important;
                        backdrop-filter: blur(28px) !important;
                        -webkit-backdrop-filter: blur(28px) !important;
                    }
                    .pf-c-login__main {
                        position: fixed !important;
                        left: 25% !important;
                        top: 50% !important;
                        transform: translate(-50%, -50%) !important;
                        margin: 0 !important;
                    }
                `;
            }
        } else if (isCustomFlowTemplate) {
            // Si ya existe la maqueta flow.html exterior, la del shadow root debe ser transparente e inofensiva
            positionCss = `
                .pf-c-login::before {
                    display: none !important;
                }
                .pf-c-login {
                    background: transparent !important;
                    background-color: transparent !important;
                    background-image: none !important;
                    position: static !important;
                    width: 100% !important;
                    height: auto !important;
                    min-height: 0 !important;
                    padding: 0 !important;
                    box-sizing: border-box !important;
                }
                /* Nuke all native white card wrappers, borders, shadows and headers */
                .pf-c-login__main, .pf-c-card, [class*="login__main"], [class*="card"] {
                    position: static !important;
                    transform: none !important;
                    width: 100% !important;
                    max-width: 100% !important;
                    box-shadow: none !important;
                    background: transparent !important;
                    background-color: transparent !important;
                    border: none !important;
                    backdrop-filter: none !important;
                    -webkit-backdrop-filter: none !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
                 .pf-c-login__main-header, [class*="main-header"], ak-brand, .pf-c-brand, h1, .pf-c-title, [class*="title"], [slot="description"], .pf-c-login__main-body > p, .pf-c-login__main-body-subtext {
                    display: none !important;
                    height: 0 !important;
                    padding: 0 !important;
                    margin: 0 !important;
                }
                .pf-c-login__main-body, [class*="main-body"] {
                    padding: 0 0 1.5rem 0 !important;
                    background: transparent !important;
                    background-color: transparent !important;
                }
                .pf-c-form__group, [class*="form__group"] {
                    margin-bottom: 0.5rem !important;
                }
                .pf-c-form-control, input {
                    padding: 0.5rem 0.75rem !important;
                }
                .pf-c-login__main-footer, [class*="main-footer"] {
                    padding: 0 !important;
                    margin-top: 0.75rem !important;
                    background: transparent !important;
                    background-color: transparent !important;
                }
            `;
        }

        // Estilos para el spinner de carga nativo
        const spinnerCss = `
            .pf-c-spinner, ak-loading-indicator, pf-spinner, svg[class*="spinner"], circle {
                --pf-c-spinner--stroke-color: ${primary} !important;
                stroke: ${primary} !important;
                color: ${primary} !important;
            }
        `;

        // Generar CSS dinámico con los colores del SaaS y override del background
        styleTag.textContent = `
            :host, :root, .pf-c-login {
                --pf-c-login--Background: ${panelBg} !important;
                --pf-c-button--m-primary--BackgroundColor: ${primary} !important;
                --pf-c-button--m-primary--hover--BackgroundColor: ${hover} !important;
                --pf-c-form-control--focus--BorderBottomColor: ${primary} !important;
                --pf-global--primary-color--100: ${primary} !important;
                --pf-global--primary-color--200: ${hover} !important;
                --pf-global--link--Color: ${primary} !important;
                --pf-global--link--hover--Color: ${hover} !important;
            }
            .pf-c-login {
                ${bgRule}
            }
            .pf-c-login__main {
                background: ${cardBg} !important;
            }
            .pf-c-button.pf-m-primary, button[type="submit"], .ak-btn-primary {
                background: linear-gradient(135deg, ${primary} 0%, ${hover} 100%) !important;
                box-shadow: 0 4px 12px ${primary}38 !important;
            }
            .pf-c-button.pf-m-primary:hover, button[type="submit"]:hover {
                background: linear-gradient(135deg, ${hover} 0%, ${primary} 100%) !important;
                box-shadow: 0 6px 18px ${primary}4d !important;
            }
            .pf-c-form-control:focus, input:focus {
                border-color: ${primary} !important;
                box-shadow: 0 0 0 3px ${primary}2d !important;
            }
            /* ── Corrección de diseño e integración del Ojo de Contraseña (input-group) ── */
            .pf-c-input-group {
                display: flex !important;
                width: 100% !important;
            }
            .pf-c-input-group > .pf-c-form-control,
            .pf-c-input-group > input {
                flex: 1 1 auto !important;
                width: auto !important;
                min-width: 0 !important;
                border-top-right-radius: 0 !important;
                border-bottom-right-radius: 0 !important;
            }
            .pf-c-input-group > .pf-c-button,
            .pf-c-input-group > button {
                border-top-left-radius: 0 !important;
                border-bottom-left-radius: 0 !important;
                border-top-right-radius: 8px !important;
                border-bottom-right-radius: 8px !important;
                border: 1.5px solid rgba(0, 42, 76, 0.14) !important;
                border-left: none !important;
                background: ${cardBg} !important;
                padding: 0 0.85rem !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            a, .pf-c-login__main-footer-band-item a {
                color: ${primary} !important;
            }
            a:hover {
                color: ${hover} !important;
            }
            ${positionCss}
            ${spinnerCss}
            ak-stage-access-denied, [class*="access-denied"] {
                background: transparent !important;
                background-color: transparent !important;
                padding-bottom: 2rem !important;
            }
            ak-stage-access-denied .pf-c-card,
            ak-stage-access-denied .pf-c-login__main,
            ak-stage-access-denied [class*="card"] {
                background: transparent !important;
                background-color: transparent !important;
                box-shadow: none !important;
                border: none !important;
            }
            ak-stage-access-denied button,
            ak-stage-access-denied a,
            ak-stage-access-denied ak-action-button,
            ak-stage-access-denied .pf-c-button {
                margin-bottom: 2.5rem !important;
            }
        `;
    }

    function setupErrorCleaner(shadow) {
        // Intencionalmente SIN EFECTO. Antes ocultaba TODA alerta/error
        // (.pf-c-form__alert, [class*="error"], .pf-c-form__helper-text) con
        // display:none inline !important en cada input/focusin. Como el campo de
        // contraseña se autoenfoca al re-renderizar el stage tras un login fallido,
        // esto HACÍA DESAPARECER el mensaje "Error de autenticación" apenas aparecía.
        // Un display:none inline !important puesto por JS no puede revertirse desde
        // ninguna hoja de estilo. El error ahora se limpia solo al re-renderizar el
        // stage en el siguiente envío. (Existe una copia gemela ya neutralizada en
        // custom-templates/if/flow.html — ambas deben quedar inertes.)
        return;
    }

    // Destino de "Ir al inicio" en la pantalla de acceso denegado.
    // NO usar '/' ni casmarts-seamless-logout-flow?next=<authorize>: ambos re-lanzan
    // la autorización del usuario YA autenticado (o pasan por el library-gate que
    // redirige a Starter) => vuelve a "Permiso denegado" en bucle infinito.
    // default-invalidation-flow cierra sesión y devuelve al login: sin sesión no hay
    // autorización pendiente ni library-gate, así que no hay loop.
    var CS_ACCESS_DENIED_HOME = '/if/flow/default-invalidation-flow/';

    // Caso web-component (ak-stage-access-denied dentro del shadow del executor).
    function setupAccessDeniedStage(root) {
        if (!root || !root.querySelectorAll) return;
        root.querySelectorAll('a.pf-c-button, a.pf-m-primary, a[id="ak-back-home"]').forEach(function(a) {
            if (a.getAttribute('href') !== CS_ACCESS_DENIED_HOME) a.setAttribute('href', CS_ACCESS_DENIED_HOME);
            a.style.setProperty('margin-bottom', '1.5rem', 'important');
        });
    }

    // Caso server-rendered (SSR): /application/o/authorize/ con denegación de política
    // renderiza HTML plano en light DOM (sin ak-flow-executor), con el botón
    // <a id="ak-back-home" href="/" class="pf-c-button pf-m-primary pf-m-block">.
    // Aquí reescribimos su href al logout y le damos aire inferior (queda pegado al
    // borde del card porque su .pf-c-form__group no tiene margen).
    function fixAccessDeniedSSR() {
        var btn = document.getElementById('ak-back-home');
        if (!btn) return;
        if (btn.getAttribute('href') !== CS_ACCESS_DENIED_HOME) btn.setAttribute('href', CS_ACCESS_DENIED_HOME);
        var card = btn.closest('.pf-c-login__main');
        if (card) {
            // El card es un flex-item DENTRO del shell drawer de Authentik, y su
            // overflow:hidden lo CONSTRIÑE a ~259px (< a su contenido ~329px): el
            // botón queda recortado en el borde inferior => se ve "pegado". Con
            // overflow:visible el card crece hasta su contenido y muestra el hueco.
            // Verificado con Playwright: gap botón↔borde pasó de -16px (recortado)
            // a positivo. NO usar márgenes (colapsan) ni height:auto (no vence la
            // restricción del flex-item): la clave es overflow:visible.
            card.style.setProperty('overflow', 'visible', 'important');
        }
        // El main-body trae 3rem (48px) de padding-bottom nativo de PatternFly, que
        // con el card ya sin recorte se ve demasiado aireado; lo ajustamos a 1.5rem
        // para un hueco equilibrado con el header.
        var body = btn.closest('.pf-c-login__main-body');
        if (body) body.style.setProperty('padding-bottom', '1.5rem', 'important');
    }

    function applyDynamicStylesToRoot(root, theme) {
        if (!root) return;
        var hostTag = (root.host && root.host.tagName) ? root.host.tagName.toLowerCase() : '';
        if (root.host && hostTag !== 'ak-flow-executor' && hostTag.indexOf('ak-stage-') !== 0) {
            return;
        }

        injectStyle(root);
        injectDynamicStyle(root, theme);
        setupErrorCleaner(root);

        if (hostTag === 'ak-stage-access-denied') {
            setupAccessDeniedStage(root);
        }

        // Personalizar títulos del card si existen
        const titleEl = root.querySelector('.pf-c-title, .pf-c-login__main-header h1, h1');
        if (titleEl && theme.system_name) {
            titleEl.innerHTML = theme.system_name;
            if (theme.name_align) {
                titleEl.style.textAlign = theme.name_align;
            }
            if (theme.system_name_color) {
                titleEl.style.color = theme.system_name_color;
            }
        }

        const subtitleEl = root.querySelector('.pf-c-login__main-header p, .pf-c-login__main-header-desc');
        if (subtitleEl && theme.system_subtitle) {
            subtitleEl.innerHTML = theme.system_subtitle;
            if (theme.subtitle_align) {
                subtitleEl.style.textAlign = theme.subtitle_align;
            }
            if (theme.system_subtitle_color) {
                subtitleEl.style.color = theme.system_subtitle_color;
            }
        }

        // Aplicar opacidad del formulario si se configuró
        const formContainer = root.querySelector('.pf-c-login__main-body');
        if (formContainer && theme.form_opacity !== undefined) {
            const targetOpacity = String(theme.form_opacity);
            if (formContainer.style.opacity !== targetOpacity) {
                formContainer.style.opacity = targetOpacity;
            }
        }

        // Apply global properties only on executor root
        if (hostTag === 'ak-flow-executor') {
            // Aplicar altura dinámica al card unificado si existe
            const outerScreen = document.getElementById('cs-screen');
            if (outerScreen) {
                const targetHeight = theme.form_height_pct || theme.logos_height_pct;
                if (targetHeight) {
                    outerScreen.style.height = `${targetHeight}vh`;
                    outerScreen.style.maxHeight = `${targetHeight}vh`;
                } else {
                    outerScreen.style.height = '';
                    outerScreen.style.maxHeight = '';
                }
            }
            const outerFormCol = document.getElementById('cs-form-col');
            if (outerFormCol) {
                outerFormCol.style.height = '';
                outerFormCol.style.maxHeight = '';
            }
            const outerLogosCol = document.getElementById('cs-logos-col');
            if (outerLogosCol) {
                outerLogosCol.style.height = '';
                outerLogosCol.style.maxHeight = '';
                outerLogosCol.style.alignSelf = '';
            }

            // Inyectar o actualizar logotipo superior
            const logoWrapper = root.querySelector('#' + LOGO_ID);
            if (logoWrapper) {
                const img = logoWrapper.querySelector('.cs-logo-img');
                if (img) {
                    let expectedSrc = 'https://auth.casmart.internal/media/public/casmarts-logo-2.png';
                    if (theme.has_logo_top) {
                        expectedSrc = `/lm/api/v1/public/theme/${flowSlug}/image/logo_top${clientId ? '?app=' + clientId : ''}`;
                    }
                    if (img.getAttribute('src') !== expectedSrc) {
                        img.setAttribute('src', expectedSrc);
                    }
                    if (theme.logos_opacity !== undefined) {
                        const targetOpacity = String(theme.logos_opacity);
                        if (img.style.opacity !== targetOpacity) {
                            img.style.opacity = targetOpacity;
                        }
                    }
                }
                
                const tagline = logoWrapper.querySelector('.cs-tagline');
                if (tagline && theme.display_name && tagline.textContent !== theme.display_name) {
                    tagline.textContent = theme.display_name;
                }
            }
        }

        // Recursively apply to children shadow roots
        if (root.querySelectorAll) {
            root.querySelectorAll('*').forEach(function(el) {
                if (el.shadowRoot) {
                    applyDynamicStylesToRoot(el.shadowRoot, theme);
                }
            });
        }

        // Observe Shadow DOM for this specific root to handle updates
        if (!root._cs_observed_recursive) {
            root._cs_observed_recursive = true;
            const obs = new MutationObserver((mutations) => {
                obs.disconnect();

                mutations.forEach(m => {
                    m.addedNodes.forEach(n => {
                        if (n.nodeType !== 1) return;
                        if (n.shadowRoot) applyDynamicStylesToRoot(n.shadowRoot, theme);
                        if (n.querySelectorAll) {
                            n.querySelectorAll('*').forEach(el => {
                                if (el.shadowRoot) applyDynamicStylesToRoot(el.shadowRoot, theme);
                            });
                        }
                    });
                });

                // Re-apply to this root
                injectStyle(root);
                injectDynamicStyle(root, theme);
                setupErrorCleaner(root);
                if (hostTag === 'ak-stage-access-denied') {
                    setupAccessDeniedStage(root);
                }

                obs.observe(root, { childList: true, subtree: true });
            });
            obs.observe(root, { childList: true, subtree: true });
        }
    }

    /* ── 3. Aplicar estilos dinámicos al DOM/Shadow DOM ───────────── */
    function applyDynamicStyles() {
        if (!themeConfig) return;
        // Paginas con #cs-screen (flow.html) ya traen su PROPIO fetch de tema +
        // su propia inyeccion de CSS en el shadow DOM (ver casmarts-shadow-
        // intercept / csInjectShadow en flow.html) — son dos motores
        // independientes que no se coordinan entre si. Sin este guard, este
        // script tambien inyectaba su copia (con los colores que SU PROPIO
        // fetch del tema resolvia) en el MISMO shadow root, y como se agrega
        // despues del <style id="cs-theme"> de flow.html, ganaba la cascada
        // para cualquier propiedad que ambos declararan con !important. Con
        // temas donde los dos fetches resuelven el mismo color no se notaba;
        // con Centinela AI (panel_bg_color oscuro) el boton del ojo terminaba
        // con el fondo oscuro de ESTE script en vez del blanco de flow.html,
        // e invisible el icono negro encima. Ver flowhtml-css-recurring-
        // regressions (2026-11-03) para el caso reportado.
        if (document.getElementById('cs-screen') !== null) return;

        const executor = document.querySelector('ak-flow-executor');
        if (executor && executor.shadowRoot) {
            applyDynamicStylesToRoot(executor.shadowRoot, themeConfig);
        }
    }

    /* ── 4. Construir layout base estructurado ─────────────────────── */
    function buildLayout(root) {
        const login = root.querySelector('.pf-c-login');
        const card  = root.querySelector('.pf-c-login__main');
        if (!login || !card) return;
        if (login._cs_done)  return;
        login._cs_done = true;

        /* — Ocultar branding nativo (rayo) dentro del card — */
        card.querySelectorAll('img, .pf-c-brand, ak-brand, [class*="brand"]').forEach(el => {
            if (!el.id || !el.id.startsWith('casmarts')) el.style.display = 'none';
        });

        /* — Logo corporativo dentro del card — */
        injectLogo(root, card);
    }

    /* ── 5. Inyectar logo dentro del card ───────────────────── */
    function injectLogo(root, card) {
        if (root.querySelector('#' + LOGO_ID)) return;

        const wrapper = document.createElement('div');
        wrapper.id = LOGO_ID;
        Object.assign(wrapper.style, {
            display:        'flex',
            flexDirection:  'column',
            alignItems:     'center',
            padding:        '2rem 2rem 0.25rem',
            gap:            '0.4rem',
        });

        const img = document.createElement('img');
        img.className = 'cs-logo-img';
        img.src   = 'https://auth.casmart.internal/media/public/casmarts-logo-2.png';
        img.alt   = 'CASmartS Logo';
        Object.assign(img.style, {
            maxWidth:     '200px',
            maxHeight:    '76px',
            width:        'auto',
            height:       'auto',
            objectFit:    'contain',
            display:      'block',
            mixBlendMode: 'multiply',
            transition:   'opacity 0.3s ease',
        });
        img.onerror = () => {
            img.style.display = 'none';
            const fallback = document.createElement('span');
            Object.assign(fallback.style, {
                fontFamily: "'Jost', 'Inter', sans-serif",
                fontWeight: '800',
                fontSize:   '1.4rem',
                color:      '#4272A5',
                letterSpacing: '-0.03em',
            });
            fallback.textContent = 'CASmartS';
            wrapper.insertBefore(fallback, tagline);
        };

        const tagline = document.createElement('span');
        tagline.className = 'cs-tagline';
        tagline.textContent = 'Plataforma de Servicios';
        Object.assign(tagline.style, {
            fontFamily:    "'Inter', sans-serif",
            fontSize:      '0.72rem',
            fontWeight:    '500',
            color:         '#6b8fa8',
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            marginTop:     '0.1rem',
        });

        wrapper.appendChild(img);
        wrapper.appendChild(tagline);
        card.insertBefore(wrapper, card.firstChild);
    }

    /* ── 6. Loop de detección e inyección ───────────────────────────── */
    let attempts = 0;
    function tick() {
        if (disableBranding) return;
        /* Pantalla de acceso denegado SSR (light DOM): romper loop + dar aire al botón */
        fixAccessDeniedSSR();
        /* #cs-screen => pagina de flow.html: tiene su PROPIO motor de theming
           (casmarts-shadow-intercept/csInjectShadow), independiente de este
           script. injectStyle/buildLayout inyectaban igual aqui — link de
           custom_authentik.css + reconstruccion de layout SSR — compitiendo
           con lo que flow.html ya puso (mismo bug que applyDynamicStyles,
           ver su comentario). */
        const isCustomFlowTemplate = document.getElementById('cs-screen') !== null;
        /* Inyectar en Shadow DOM de Authentik */
        const executor = document.querySelector('ak-flow-executor');
        if (!isCustomFlowTemplate && executor && executor.shadowRoot) {
            const shadow = executor.shadowRoot;
            injectStyle(shadow);
            buildLayout(shadow);
            if (themeLoaded) {
                applyDynamicStyles();
            }
        }

        /* Fallback: inyectar stylesheet en document.head solo si NO estamos usando la maqueta exterior custom */
        if (!isCustomFlowTemplate && !document.head.querySelector('#' + STYLE_ID + '-global')) {
            const link  = document.createElement('link');
            link.id     = STYLE_ID + '-global';
            link.rel    = 'stylesheet';
            link.href   = '/static/custom_authentik.css?v=' + CSS_VERSION;
            document.head.appendChild(link);
        }

        /* Parar cuando el layout está construido (max 5s) */
        attempts++;
        if (attempts < 300) {
            requestAnimationFrame(tick);
        }
    }

    tick();

    /* ─────────────────────────────────────────────
     * Library gate: usuarios no-admin no deben ver
     * /if/user/ (el "Mis aplicaciones" / library de Authentik) — se
     * redirigen a Starter. Los admins (is_superuser) lo ven normal.
     * El caso de "vengo de una app específica" ya funciona solo: ese
     * flujo pasa por /if/flow/ con `next=`, nunca toca /if/user/.
     * ───────────────────────────────────────────── */
    if (url.pathname.startsWith('/if/user/')) {
        // Fallback solo por si /tenant/resolve falla o el tenant no configuró
        // nada todavía — no debe ser el camino normal en producción.
        const FALLBACK_URL = 'https://starter-frontend-dev.casmart.internal/';

        Promise.all([
            fetch('/api/v3/core/users/me/', { credentials: 'same-origin' })
                .then(res => (res.ok ? res.json() : null))
                .catch(() => null),
            fetch('/lm/api/v1/tenant/resolve', { credentials: 'same-origin' })
                .then(res => (res.ok ? res.json() : null))
                .catch(() => null),
        ])
            .then(([sessionData, tenantData]) => {
                const user = sessionData && sessionData.user;
                if (!user || user.is_superuser) return;
                const targetUrl = (tenantData && tenantData.default_app_url) || FALLBACK_URL;
                console.log('[CASmartS] Usuario no-admin en /if/user/, redirigiendo a', targetUrl);
                window.location.replace(targetUrl);
            })
            .catch(err => {
                console.error('[CASmartS] No se pudo verificar el usuario/tenant para el library gate:', err);
            });
    }
})();
