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
        className="relative z-10 w-full h-full flex items-center px-12 py-10 gap-6 transition-all duration-350"
        style={{ justifyContent: getJustifyContent() }}
      >
        {/* FORM PANEL */}
        <div
          className="flex items-stretch shrink-0 transition-all duration-300"
          style={{ order: getFlexOrder('login') }}
        >
          <div
            id="login-card"
            className="w-[340px] min-w-[300px] rounded-2xl p-10 flex flex-col justify-center shadow-2xl backdrop-blur-[2px] transition-all duration-300"
            style={{
              background: hexToRgba(theme.card_bg_color || '#FFFFFF', theme.form_opacity),
              height: theme.form_height_pct ? `${theme.form_height_pct}vh` : 'auto',
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
              className="w-full py-3 text-white rounded-full font-bold text-xs tracking-widest uppercase transition-all shadow-md select-none font-sans"
              style={{
                backgroundColor: primaryColor,
                cursor: 'not-allowed',
              }}
            >
              INICIAR SESIÓN
            </button>

            <span
              onClick={() => setShowModal(true)}
              className="text-xs text-gray-600 font-sans cursor-pointer underline hover:text-[#8B3A2A] mt-2 block"
              style={{
                textAlign: theme.privacy_align,
                '--hover-c': hoverColor,
              } as any}
            >
              Privacidad
            </span>
          </div>
        </div>

        {/* LOGOS PANEL */}
        <div
          className="flex flex-col items-center justify-center gap-14 px-9 py-10 rounded-2xl shadow-2xl backdrop-blur-[2px] overflow-hidden transition-all duration-300"
          style={{
            order: getFlexOrder('logos'),
            background: hexToRgba(theme.panel_bg_color || '#F6F9FD', theme.logos_opacity),
            height: theme.logos_height_pct ? `${theme.logos_height_pct}vh` : 'auto',
          }}
        >
          {/* Logo Superior */}
          <div className="flex items-center gap-6">
            {theme.logo_top_base64 ? (
              <img
                src={theme.logo_top_base64}
                alt="Logo superior"
                className="max-h-[110px] max-w-[380px] object-contain transition-all"
              />
            ) : (
              /* Shield placeholder */
              <div className="flex items-center gap-4 bg-white/10 rounded-xl px-5 py-3 border border-white/20 select-none">
                <svg className="w-16 h-20 shrink-0" viewBox="0 0 72 82" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M36 2 L70 16 L70 46 C70 64 36 80 36 80 C36 80 2 64 2 46 L2 16 Z" fill="#c8a05a" stroke="#8B6914" strokeWidth="2"/>
                  <path d="M36 8 L64 20 L64 45 C64 61 36 75 36 75 C36 75 8 61 8 45 L8 20 Z" fill="#b08840"/>
                  <text x="36" y="36" textAnchor="middle" fontSize="8" fill="#fff" fontFamily="serif" fontWeight="bold">GEM</text>
                  <text x="36" y="48" textAnchor="middle" fontSize="5.5" fill="#fff" fontFamily="serif">TOLUCA</text>
                </svg>
                <div className="text-left text-white leading-tight">
                  <div className="text-[10px] font-semibold tracking-wider opacity-85 text-shadow">GOBIERNO DEL</div>
                  <div className="font-extrabold text-2xl text-shadow font-sans">ESTADO DE<br />MÉXICO</div>
                </div>
                <div className="w-0.5 h-20 bg-white/50" />
                <div className="flex flex-col items-center text-white text-shadow leading-none">
                  <span className="text-4xl">🦅</span>
                  <span className="font-black text-xl text-[#c0392b] tracking-wider font-sans">MÉXICO</span>
                  <span className="italic text-[9px] opacity-90 mt-1 font-sans">¡El poder de servir!</span>
                </div>
              </div>
            )}
          </div>

          {/* Logo Inferior */}
          <div className="text-center">
            {theme.logo_bottom_base64 ? (
              <img
                src={theme.logo_bottom_base64}
                alt="Logo inferior"
                className="max-h-[90px] max-w-[380px] object-contain transition-all"
              />
            ) : (
              /* COMPRAMEX placeholder */
              <div className="select-none text-left">
                <div className="font-sans font-black text-[3.2rem] tracking-wider text-shadow">
                  <span className="text-[#2c2c2c]">COMPRA</span>
                  <span className="text-[#c8963a]">MEX</span>
                </div>
                <div className="font-sans text-[#c8963a] text-xs tracking-wider border-t border-[#c8963a] pt-1.5 mt-1 text-center font-semibold">
                  Portal Público de Compras
                </div>
              </div>
            )}
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
