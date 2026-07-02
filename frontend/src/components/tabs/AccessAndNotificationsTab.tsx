import React from 'react';
import { Theme } from '../../types/theme';

// ── Inline SVG icons for social providers ─────────────────────────────────

const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
);

const MicrosoftIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="1" y="1" width="10" height="10" fill="#F25022"/>
    <rect x="13" y="1" width="10" height="10" fill="#7FBA00"/>
    <rect x="1" y="13" width="10" height="10" fill="#00A4EF"/>
    <rect x="13" y="13" width="10" height="10" fill="#FFB900"/>
  </svg>
);

const GovIdIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="2" y="5" width="20" height="14" rx="2" stroke="#374151" strokeWidth="1.5" fill="none"/>
    <circle cx="8" cy="12" r="2.5" stroke="#374151" strokeWidth="1.5" fill="none"/>
    <path d="M13 9h5M13 12h4M13 15h3" stroke="#374151" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

// ── Toggle helper ──────────────────────────────────────────────────────────

interface ToggleProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
  description?: string;
}

const Toggle: React.FC<ToggleProps> = ({ checked, onChange, disabled, label, description }) => (
  <label className={`flex items-start gap-3 cursor-pointer ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}>
    <div className="relative mt-0.5 shrink-0">
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
      />
      <div
        className="w-10 h-5 rounded-full transition-colors duration-200"
        style={{ backgroundColor: checked ? '#4272A5' : '#d1d5db' }}
      />
      <div
        className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200"
        style={{ transform: checked ? 'translateX(20px)' : 'translateX(0)' }}
      />
    </div>
    <div className="min-w-0">
      <p className="text-sm font-medium text-gray-800">{label}</p>
      {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
    </div>
  </label>
);

// ── Main component ─────────────────────────────────────────────────────────

interface Props {
  theme: Theme;
  onUpdateField: <K extends keyof Theme>(key: K, value: Theme[K]) => void;
}

export const AccessAndNotificationsTab: React.FC<Props> = ({
  theme,
  onUpdateField,
}) => {
  return (
    <div className="space-y-8">

      {/* ── ELEMENTOS VISIBLES ──────────────────────────────────── */}
      <section>
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">
          Elementos visibles
        </h3>
        <div className="space-y-4">
          <Toggle
            label="Mostrar panel de logos"
            description="Muestra u oculta el panel lateral de logotipos institucionales"
            checked={theme.show_logos_panel}
            onChange={v => onUpdateField('show_logos_panel', v)}
          />
          <Toggle
            label="Mostrar nombre del sistema"
            description="Muestra u oculta el título principal en el formulario"
            checked={theme.show_system_name}
            onChange={v => onUpdateField('show_system_name', v)}
          />
          <Toggle
            label="Mostrar subtítulo"
            description="Muestra u oculta el subtítulo debajo del nombre del sistema"
            checked={theme.show_system_subtitle}
            onChange={v => onUpdateField('show_system_subtitle', v)}
          />
          <Toggle
            label="Mostrar ojo de contraseña"
            description="Muestra u oculta el botón para ver/ocultar la contraseña"
            checked={theme.show_password_toggle}
            onChange={v => onUpdateField('show_password_toggle', v)}
          />
          <Toggle
            label="Mostrar etiquetas de campos"
            description="Muestra u oculta las etiquetas Usuario / Contraseña sobre los campos"
            checked={theme.show_field_labels}
            onChange={v => onUpdateField('show_field_labels', v)}
          />
          <Toggle
            label="Mostrar mensaje de aplicación"
            description="Muestra u oculta 'Inicia sesión para continuar a [Aplicación]' en el consent flow"
            checked={theme.show_app_message}
            onChange={v => onUpdateField('show_app_message', v)}
          />
        </div>
      </section>

      {/* ── ACCESOS Y SEGURIDAD ──────────────────────────────────── */}
      <section>
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">
          Accesos y Seguridad
        </h3>

        <div className="space-y-4">
          <Toggle
            label="Mostrar recuperación de contraseña"
            description="Muestra el enlace '¿Olvidaste tu contraseña?' en el portal"
            checked={theme.show_forgot_password}
            onChange={v => onUpdateField('show_forgot_password', v)}
          />

          <Toggle
            label="Permitir auto-registro"
            description="Muestra el enlace '¿No tienes cuenta?' en el portal"
            checked={theme.allow_self_registration}
            onChange={v => onUpdateField('allow_self_registration', v)}
          />

          <Toggle
            label="Requerir verificación por correo"
            description="El usuario debe confirmar su correo antes de acceder"
            checked={theme.require_email_verification}
            disabled={!theme.allow_self_registration}
            onChange={v => onUpdateField('require_email_verification', v)}
          />
        </div>

        {/* Social providers */}
        <div className="mt-6">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
            Proveedores de identidad social
          </p>
          <div className="space-y-3">
            <Toggle
              label="Google"
              description="Mostrar botón de inicio con Google"
              checked={theme.show_social_google}
              onChange={v => onUpdateField('show_social_google', v)}
            />
            <div className="flex items-center gap-2 -mt-1 ml-[52px]">
              <GoogleIcon />
            </div>

            <Toggle
              label="Microsoft / Azure AD"
              description="Mostrar botón de inicio con Microsoft"
              checked={theme.show_social_microsoft}
              onChange={v => onUpdateField('show_social_microsoft', v)}
            />
            <div className="flex items-center gap-2 -mt-1 ml-[52px]">
              <MicrosoftIcon />
            </div>

            <Toggle
              label="ID Institucional"
              description="Mostrar botón de identificación oficial"
              checked={theme.show_social_gov_id}
              onChange={v => onUpdateField('show_social_gov_id', v)}
            />
            <div className="flex items-center gap-2 -mt-1 ml-[52px]">
              <GovIdIcon />
            </div>
          </div>
        </div>
      </section>

      {/* ── NOTIFICACIONES POR CORREO ────────────────────────────── */}
      <section>
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">
          Notificaciones por Correo
        </h3>

        <div className="space-y-4">
          <div className="px-3 py-2 bg-blue-50 border border-blue-100 rounded-lg">
            <p className="text-[10px] text-blue-700 leading-relaxed">
              ℹ️ Los correos siempre usan el color primario y el logo de este portal — no hay una opción de diseño independiente por correo.
            </p>
          </div>

          {/* Footer text */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Texto de pie de correo
              <span className="ml-1 text-gray-400 font-normal">
                ({(theme.email_footer_text ?? '').length}/255)
              </span>
            </label>
            <textarea
              rows={2}
              maxLength={255}
              value={theme.email_footer_text ?? ''}
              onChange={e => onUpdateField('email_footer_text', e.target.value || null)}
              placeholder="© 2026 CASMARTS Core. Todos los derechos reservados."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

          <p className="text-[10px] text-gray-400 leading-relaxed">
            💡 Para editar el asunto y contenido de cada tipo de correo (restablecer contraseña, alta de usuario, etc.), usa la pestaña <strong>📧 Vista Correo</strong>.
          </p>
        </div>

      </section>
    </div>
  );
};
