import React, { useState } from 'react';
import DOMPurify from 'dompurify';
import { Eye, EyeOff } from 'lucide-react';
import { Theme } from '../types/theme';

interface LoginPreviewProps {
  theme: Theme;
}

export const LoginPreview: React.FC<LoginPreviewProps> = ({ theme }) => {
  const [showPwd, setShowPwd] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Helper to convert hex colors to RGBA for transparent container support
  const hexToRgba = (hex: string, alpha: number) => {
    try {
      const cleanHex = hex.replace('#', '');
      const r = parseInt(cleanHex.substring(0, 2), 16);
      const g = parseInt(cleanHex.substring(2, 4), 16);
      const b = parseInt(cleanHex.substring(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    } catch (e) {
      return `rgba(255, 255, 255, ${alpha})`;
    }
  };

  // Setup dynamic styles according to the config parameters
  const primaryColor = theme.primary_color;
  const hoverColor = theme.hover_color;

  const bgStyle = (): React.CSSProperties => {
    const style: React.CSSProperties = {
      opacity: theme.bg_opacity,
      transition: 'opacity 0.4s, background 0.3s',
    };

    if (theme.bg_type === 'color' && theme.bg_flat_color) {
      style.background = theme.bg_flat_color;
    } else if (theme.bg_type === 'image' && theme.bg_image_base64) {
      style.backgroundImage = `url(${theme.bg_image_base64})`;
      style.backgroundSize = 'cover';
      style.backgroundPosition = 'center';
    } else {
      // gradient (default)
      style.background = `linear-gradient(135deg, ${theme.bg_gradient_from} 0%, ${theme.bg_gradient_to} 100%)`;
    }

    return style;
  };

  const getFlexOrder = (col: 'login' | 'logos') => {
    if (theme.layout_position === 'left') {
      return col === 'login' ? 1 : 2;
    } else if (theme.layout_position === 'right') {
      return col === 'login' ? 2 : 1;
    } else {
      // center
      return col === 'login' ? 1 : 2;
    }
  };

  const getJustifyContent = () => {
    if (theme.layout_position === 'left') return 'flex-start';
    if (theme.layout_position === 'right') return 'flex-end';
    return 'center';
  };

  // Safe sanitization helper for system name accepting <br> or basic tags
  const sanitizedSysName = DOMPurify.sanitize(theme.system_name);

  return (
    <div className="relative w-full h-full overflow-hidden flex items-stretch select-none">
      {/* Dynamic Background layer */}
      <div className="absolute inset-0 z-0" style={bgStyle()} />
      <div className="absolute inset-0 z-[1] bg-black/10 backdrop-brightness-95" />

      {/* Main Preview Container */}
      <div
        className="relative z-10 w-full h-full flex items-center px-12 py-10 transition-all duration-350"
        style={{
          justifyContent: theme.layout_position === 'left' ? 'flex-start' : theme.layout_position === 'right' ? 'flex-end' : 'center',
          paddingLeft: theme.layout_position === 'left' ? '6vw' : '3rem',
          paddingRight: theme.layout_position === 'right' ? '6vw' : '3rem',
        }}
      >
        {/* UNIFIED SPLIT CARD */}
        <div
          className="relative flex items-stretch border border-white/60 rounded-3xl shadow-2xl overflow-hidden transition-all duration-300 bg-white/70 backdrop-blur-xl"
          style={{
            flexDirection: theme.layout_position === 'right' ? 'row-reverse' : 'row',
            width: '780px',
            maxWidth: '90vw',
            height: theme.form_height_pct || theme.logos_height_pct ? `${theme.form_height_pct || theme.logos_height_pct}vh` : '500px',
            maxHeight: '560px',
            background: hexToRgba(theme.card_bg_color || '#FFFFFF', theme.form_opacity),
          }}
        >
          {/* FORM PANEL */}
          <div
            id="login-card"
            className="w-[390px] shrink-0 p-10 flex flex-col justify-center transition-all duration-300 overflow-y-auto"
            style={{
              background: 'transparent',
              height: '100%',
            }}
          >
            {/* System Title */}
            <div
              className="font-extrabold text-3xl leading-none text-gray-900 mb-2 font-sans"
              style={{ textAlign: theme.name_align }}
              dangerouslySetInnerHTML={{ __html: sanitizedSysName }}
            />

            {/* System Subtitle */}
            <div
              className="text-sm text-gray-700 mb-8 font-sans"
              style={{ textAlign: theme.subtitle_align }}
            >
              {theme.system_subtitle}
            </div>

            {/* Dummy Input User */}
            <div className="mb-4 text-left">
              <label className="block text-xs font-semibold text-gray-700 mb-1.5 font-sans">
                Usuario / Correo electrónico
              </label>
              <input
                type="text"
                disabled
                placeholder="usuario@casmarts.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white/80 outline-none text-gray-400 font-sans cursor-not-allowed"
              />
            </div>

            {/* Dummy Input Password */}
            <div className="mb-4 text-left">
              <label className="block text-xs font-semibold text-gray-700 mb-1.5 font-sans">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  disabled
                  value="supersecretpassword"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white/80 outline-none text-gray-400 font-sans cursor-not-allowed pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 cursor-pointer"
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="text-center text-xs text-gray-600 font-sans cursor-not-allowed mb-5 hover:underline">
              ¿Olvidaste tu contraseña?
            </div>

            {/* Login Button with variables inline styling */}
            <button
              type="button"
              disabled
              className="w-full py-3 text-white rounded-lg font-bold text-xs tracking-widest uppercase transition-all shadow-sm select-none font-sans"
              style={{
                backgroundColor: primaryColor,
                cursor: 'not-allowed',
              }}
            >
              INICIAR SESIÓN
            </button>

            <span
              onClick={() => setShowModal(true)}
              className="text-xs text-gray-600 font-sans cursor-pointer underline hover:text-[#4272A5] mt-2 block"
              style={{
                textAlign: theme.privacy_align,
                '--hover-c': hoverColor,
              } as any}
            >
              Privacidad
            </span>
          </div>

          {/* LOGOS PANEL */}
          <div
            className="flex-1 flex flex-col items-center justify-center gap-8 px-9 py-10 overflow-hidden transition-all duration-300"
            style={{
              background: hexToRgba(theme.panel_bg_color || '#F6F9FD', theme.logos_opacity ?? 0.55),
              height: '100%',
              borderLeft: theme.layout_position === 'right' ? 'none' : '1px solid rgba(255, 255, 255, 0.4)',
              borderRight: theme.layout_position === 'right' ? '1px solid rgba(255, 255, 255, 0.4)' : 'none',
            }}
          >
            {/* Logo Superior */}
            <div className="flex items-center justify-center w-full">
              {theme.logo_top_base64 ? (
                <img
                  src={theme.logo_top_base64}
                  alt="Logo superior"
                  className="max-h-[90px] max-w-[280px] object-contain transition-all"
                />
              ) : theme.logo_top_text ? (
                <div
                  className="text-center font-extrabold text-2xl leading-tight text-white select-none"
                  style={{ textShadow: '0 2px 8px rgba(0,0,0,0.35)' }}
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(theme.logo_top_text) }}
                />
              ) : (
                <div className="text-center text-white/40 text-xs font-sans italic select-none">
                  Sin logotipo superior
                </div>
              )}
            </div>

            {/* Logo Inferior */}
            <div className="flex items-center justify-center w-full">
              {theme.logo_bottom_base64 ? (
                <img
                  src={theme.logo_bottom_base64}
                  alt="Logo inferior"
                  className="max-h-[85px] max-w-[280px] object-contain transition-all"
                />
              ) : theme.logo_bottom_text ? (
                <div
                  className="text-center font-extrabold text-xl leading-tight text-white select-none"
                  style={{ textShadow: '0 2px 8px rgba(0,0,0,0.35)' }}
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(theme.logo_bottom_text) }}
                />
              ) : (
                <div className="text-center text-white/40 text-xs font-sans italic select-none">
                  Sin logotipo inferior
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* PDF Modal Preview */}
      {showModal && (
        <div className="fixed inset-0 bg-black/75 z-40 flex items-center justify-center p-8 animate-fadeIn">
          <div className="bg-white rounded-2xl w-[80vw] h-[85vh] flex flex-col overflow-hidden shadow-2xl animate-scaleUp">
            <div
              className="flex items-center justify-between px-5 py-4 text-white text-sm font-bold font-sans"
              style={{ backgroundColor: primaryColor }}
            >
              <span>Aviso de Privacidad (Vista Previa)</span>
              <button
                onClick={() => setShowModal(false)}
                className="text-xl cursor-pointer hover:opacity-85 font-sans"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 bg-gray-50 flex items-center justify-center p-4">
              {theme.privacy_pdf_url ? (
                <embed
                  src={`${theme.privacy_pdf_url}#toolbar=0&navpanes=0`}
                  type="application/pdf"
                  className="w-full h-full border-none rounded-xl"
                />
              ) : (
                <div className="text-center text-gray-500 font-sans">
                  <div className="text-5xl mb-4">📄</div>
                  <p className="font-semibold text-sm">Ningún aviso de privacidad en PDF asignado.</p>
                  <p className="text-xs text-gray-400 mt-1">Cárguelo desde el panel de control derecho para previsualizarlo.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
