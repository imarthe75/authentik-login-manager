import React, { useState } from 'react';
import DOMPurify from 'dompurify';
import { Eye, EyeOff } from 'lucide-react';
import { Theme } from '../types/theme';

interface LoginPreviewProps {
  theme: Theme;
}

// ── Inline SVGs for social buttons ────────────────────────────────────────

const GoogleIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
);

const MicrosoftIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="1" y="1" width="10" height="10" fill="#F25022"/>
    <rect x="13" y="1" width="10" height="10" fill="#7FBA00"/>
    <rect x="1" y="13" width="10" height="10" fill="#00A4EF"/>
    <rect x="13" y="13" width="10" height="10" fill="#FFB900"/>
  </svg>
);

const GovIdIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none"/>
    <circle cx="8" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.5" fill="none"/>
    <path d="M13 9h5M13 12h4M13 15h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const hasSocial = (theme: Theme) =>
  theme.show_social_google || theme.show_social_microsoft || theme.show_social_gov_id;

// ── Component ──────────────────────────────────────────────────────────────

export const LoginPreview: React.FC<LoginPreviewProps> = ({ theme }) => {
  const [showPwd, setShowPwd] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const hexToRgba = (hex: string, alpha: number) => {
    try {
      const h = hex.replace('#', '');
      return `rgba(${parseInt(h.slice(0,2),16)}, ${parseInt(h.slice(2,4),16)}, ${parseInt(h.slice(4,6),16)}, ${alpha})`;
    } catch {
      return `rgba(255,255,255,${alpha})`;
    }
  };

  const bgStyle = (): React.CSSProperties => {
    const style: React.CSSProperties = { opacity: theme.bg_opacity, transition: 'opacity 0.4s, background 0.3s' };
    if (theme.bg_type === 'color' && theme.bg_flat_color) {
      style.background = theme.bg_flat_color;
    } else if (theme.bg_type === 'image' && theme.bg_image_base64) {
      style.backgroundImage = `url(${theme.bg_image_base64})`;
      style.backgroundSize = 'cover';
      style.backgroundPosition = 'center';
    } else {
      style.background = `linear-gradient(135deg, ${theme.bg_gradient_from} 0%, ${theme.bg_gradient_to} 100%)`;
    }
    return style;
  };

  const sanitizedSysName = DOMPurify.sanitize(theme.system_name);
  const primaryColor = theme.primary_color;

  return (
    <div className="relative w-full h-full overflow-hidden flex items-stretch select-none">
      {/* Background */}
      <div className="absolute inset-0 z-0" style={bgStyle()} />
      <div className="absolute inset-0 z-[1] bg-black/10 backdrop-brightness-95" />

      {/* Main card */}
      <div
        className="relative z-10 w-full h-full flex items-center px-12 py-10 transition-all duration-350"
        style={{
          justifyContent: theme.layout_position === 'left' ? 'flex-start' : theme.layout_position === 'right' ? 'flex-end' : 'center',
          paddingLeft: theme.layout_position === 'left' ? '6vw' : '3rem',
          paddingRight: theme.layout_position === 'right' ? '6vw' : '3rem',
        }}
      >
        <div
          className="relative flex items-stretch border border-white/60 rounded-3xl shadow-2xl overflow-hidden transition-all duration-300"
          style={{
            flexDirection: theme.layout_position === 'right' ? 'row-reverse' : 'row',
            width: '780px',
            maxWidth: '90vw',
            height: theme.form_height_pct || theme.logos_height_pct ? `${theme.form_height_pct || theme.logos_height_pct}vh` : '500px',
            maxHeight: '580px',
            background: hexToRgba(theme.card_bg_color || '#FFFFFF', theme.form_opacity),
          }}
        >
          {/* FORM PANEL */}
          <div
            id="login-card"
            className="w-[390px] shrink-0 px-9 py-8 flex flex-col justify-center overflow-y-auto"
            style={{ background: 'transparent', height: '100%' }}
          >
            {theme.show_system_name && (
              <div
                className="font-extrabold text-3xl leading-none mb-1.5 font-sans"
                style={{ textAlign: theme.name_align, color: theme.system_name_color || '#111827' }}
                dangerouslySetInnerHTML={{ __html: sanitizedSysName }}
              />
            )}
            {theme.show_system_subtitle && (
              <div
                className="text-sm mb-5 font-sans"
                style={{ textAlign: theme.subtitle_align, color: theme.system_subtitle_color || '#374151' }}
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(theme.system_subtitle) }}
              />
            )}

            {/* User input */}
            <div className="mb-3 text-left">
              {theme.show_field_labels && (
                <label className="block text-xs font-semibold mb-1.5 font-sans" style={{ color: theme.field_label_color || '#374151' }}>
                  Usuario / Correo electrónico
                </label>
              )}
              <input type="text" disabled placeholder="usuario@casmarts.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white/80 outline-none text-gray-400 font-sans cursor-not-allowed" />
            </div>

            {/* Password input */}
            <div className="mb-3 text-left">
              {theme.show_field_labels && (
                <label className="block text-xs font-semibold mb-1.5 font-sans" style={{ color: theme.field_label_color || '#374151' }}>Contraseña</label>
              )}
              <div className="relative">
                <input type={showPwd ? 'text' : 'password'} disabled value="supersecretpassword"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white/80 outline-none text-gray-400 font-sans cursor-not-allowed pr-10" />
                {theme.show_password_toggle && (
                  <button type="button" onClick={() => setShowPwd(!showPwd)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </div>

            {theme.show_forgot_password && (
              <div className="text-center text-xs text-gray-600 font-sans cursor-not-allowed mb-4 hover:underline">
                {theme.custom_messages?.["forgot your username or password?"] || '¿Olvidaste tu contraseña?'}
              </div>
            )}

            {/* Login button */}
            <button type="button" disabled
              className="w-full py-2.5 text-white rounded-lg font-bold text-xs tracking-widest uppercase transition-all shadow-sm select-none font-sans"
              style={{ backgroundColor: primaryColor, cursor: 'not-allowed' }}>
              INICIAR SESIÓN
            </button>

            {/* Social providers divider */}
            {hasSocial(theme) && (
              <>
                <div className="flex items-center gap-2 my-3">
                  <div className="flex-1 h-px bg-gray-200" />
                  <span className="text-xs text-gray-400 font-sans">— O ingresar con —</span>
                  <div className="flex-1 h-px bg-gray-200" />
                </div>
                <div className="flex gap-2 justify-center flex-wrap">
                  {theme.show_social_google && (
                    <button type="button" disabled
                      className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-xs text-gray-600 bg-white cursor-not-allowed font-sans">
                      <GoogleIcon /> Google
                    </button>
                  )}
                  {theme.show_social_microsoft && (
                    <button type="button" disabled
                      className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-xs text-gray-600 bg-white cursor-not-allowed font-sans">
                      <MicrosoftIcon /> Microsoft
                    </button>
                  )}
                  {theme.show_social_gov_id && (
                    <button type="button" disabled
                      className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-xs text-gray-600 bg-white cursor-not-allowed font-sans">
                      <GovIdIcon /> ID Institucional
                    </button>
                  )}
                </div>
              </>
            )}

            {/* Self-registration link */}
            {theme.allow_self_registration && (
              <div className="mt-3 text-center">
                <span className="text-xs text-gray-600 font-sans cursor-not-allowed">
                  ¿No tienes cuenta?{' '}
                  <span className="underline" style={{ color: primaryColor }}>Regístrate aquí</span>
                </span>
              </div>
            )}

            {/* Privacy link */}
            <span
              onClick={() => setShowModal(true)}
              className="text-xs text-gray-600 font-sans cursor-pointer underline hover:text-[#4272A5] mt-2 block"
              style={{ textAlign: theme.privacy_align }}
            >
              Privacidad
            </span>
          </div>

          {/* LOGOS PANEL */}
          {theme.show_logos_panel && <div
            className="flex-1 flex flex-col items-center justify-center gap-8 px-9 py-10 overflow-hidden transition-all duration-300"
            style={{
              background: hexToRgba(theme.panel_bg_color || '#F6F9FD', theme.logos_opacity ?? 0.55),
              height: '100%',
              borderLeft: theme.layout_position === 'right' ? 'none' : '1px solid rgba(255,255,255,0.4)',
              borderRight: theme.layout_position === 'right' ? '1px solid rgba(255,255,255,0.4)' : 'none',
            }}
          >
            <div className="flex items-center justify-center w-full">
              {theme.logo_top_base64 ? (
                <img src={theme.logo_top_base64} alt="Logo superior"
                  className="max-h-[90px] max-w-[280px] object-contain transition-all" />
              ) : theme.logo_top_text ? (
                <div className="text-center font-extrabold leading-tight select-none"
                  style={{
                    textShadow: '0 2px 8px rgba(0,0,0,0.35)',
                    color: theme.logo_top_text_color || '#FFFFFF',
                    fontSize: theme.logo_top_text_size ? `${theme.logo_top_text_size}px` : '24px'
                  }}
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(theme.logo_top_text) }} />
              ) : (
                <div className="text-center text-white/40 text-xs font-sans italic select-none">Sin logotipo superior</div>
              )}
            </div>
            <div className="flex items-center justify-center w-full">
              {theme.logo_bottom_base64 ? (
                <img src={theme.logo_bottom_base64} alt="Logo inferior"
                  className="max-h-[85px] max-w-[280px] object-contain transition-all" />
              ) : theme.logo_bottom_text ? (
                <div className="text-center font-extrabold leading-tight select-none"
                  style={{
                    textShadow: '0 2px 8px rgba(0,0,0,0.35)',
                    color: theme.logo_bottom_text_color || '#FFFFFF',
                    fontSize: theme.logo_bottom_text_size ? `${theme.logo_bottom_text_size}px` : '20px'
                  }}
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(theme.logo_bottom_text) }} />
              ) : (
                <div className="text-center text-white/40 text-xs font-sans italic select-none">Sin logotipo inferior</div>
              )}
            </div>
          </div>}
        </div>
      </div>

      {/* PDF Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/75 z-40 flex items-center justify-center p-8">
          <div className="bg-white rounded-2xl w-[80vw] h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-5 py-4 text-white text-sm font-bold font-sans"
              style={{ backgroundColor: primaryColor }}>
              <span>Aviso de Privacidad (Vista Previa)</span>
              <button onClick={() => setShowModal(false)} className="text-xl cursor-pointer">✕</button>
            </div>
            <div className="flex-1 bg-gray-50 flex items-center justify-center p-4">
              {theme.privacy_pdf_url ? (
                <embed src={`${theme.privacy_pdf_url}#toolbar=0&navpanes=0`} type="application/pdf"
                  className="w-full h-full border-none rounded-xl" />
              ) : (
                <div className="text-center text-gray-500 font-sans">
                  <div className="text-5xl mb-4">📄</div>
                  <p className="font-semibold text-sm">Sin aviso de privacidad asignado.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
