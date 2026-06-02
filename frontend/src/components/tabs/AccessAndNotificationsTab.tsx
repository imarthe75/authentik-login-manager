import React, { useState } from 'react';
import { Theme, EmailEventType, EmailBody, EMAIL_EVENT_TYPES, EMAIL_EVENT_LABELS, EMPTY_EMAIL_BODY } from '../../types/theme';

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

// ── Variable guide ─────────────────────────────────────────────────────────

const VARIABLE_GUIDE = [
  { var: '{{ user.username }}', desc: 'Nombre de usuario' },
  { var: '{{ user.email }}', desc: 'Correo electrónico del usuario' },
  { var: '{{ url }}', desc: 'Enlace de acción (reset, activación, etc.)' },
  { var: '{{ token }}', desc: 'Token de un solo uso' },
  { var: '{{ tenant.name }}', desc: 'Nombre del tenant/sistema' },
];

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
  onUpdateEmailBody: (eventType: string, body: EmailBody) => void;
}

export const AccessAndNotificationsTab: React.FC<Props> = ({
  theme,
  onUpdateField,
  onUpdateEmailBody,
}) => {
  const [activeEvent, setActiveEvent] = useState<EmailEventType>('password_reset');
  const [copiedVar, setCopiedVar] = useState<string | null>(null);

  const currentBody: EmailBody = theme.email_bodies?.[activeEvent] ?? { ...EMPTY_EMAIL_BODY };

  const handleCopyVar = (v: string) => {
    navigator.clipboard.writeText(v).catch(() => {});
    setCopiedVar(v);
    setTimeout(() => setCopiedVar(null), 1500);
  };

  const handleBodyChange = (field: keyof EmailBody, value: string) => {
    onUpdateEmailBody(activeEvent, { ...currentBody, [field]: value });
  };

  return (
    <div className="space-y-8">

      {/* ── ACCESOS Y SEGURIDAD ──────────────────────────────────── */}
      <section>
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">
          Accesos y Seguridad
        </h3>

        <div className="space-y-4">
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
          <Toggle
            label="Heredar diseño del login en correos"
            description="Usa los colores y logo del portal como base de las plantillas"
            checked={theme.email_template_type === 'integrated'}
            onChange={v => onUpdateField('email_template_type', v ? 'integrated' : 'custom_per_event')}
          />

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
        </div>

        {/* Event selector */}
        <div className="mt-5">
          <p className="text-xs font-semibold text-gray-700 mb-2">Evento de correo</p>
          <div className="flex flex-wrap gap-1.5">
            {EMAIL_EVENT_TYPES.map(evt => (
              <button
                key={evt}
                type="button"
                onClick={() => setActiveEvent(evt)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors border ${
                  activeEvent === evt
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {EMAIL_EVENT_LABELS[evt]}
              </button>
            ))}
          </div>
        </div>

        {/* Email body editor */}
        <div className="mt-4 border border-gray-200 rounded-xl overflow-hidden">
          {/* Subject */}
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Asunto
              <span className="ml-1 text-gray-400 font-normal">
                ({(currentBody.subject ?? '').length}/200)
              </span>
            </label>
            <input
              type="text"
              maxLength={200}
              value={currentBody.subject}
              onChange={e => handleBodyChange('subject', e.target.value)}
              placeholder={`Asunto para: ${EMAIL_EVENT_LABELS[activeEvent]}`}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

          {/* Body HTML */}
          <div className="px-4 pt-3 pb-1">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-gray-700">Cuerpo del correo (HTML)</label>
            </div>
            <textarea
              rows={8}
              value={currentBody.body_html}
              onChange={e => handleBodyChange('body_html', e.target.value)}
              placeholder={`<p>Hola {{ user.username }},</p>\n<p>Contenido del correo para <em>${EMAIL_EVENT_LABELS[activeEvent]}</em>...</p>`}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
              style={{ minHeight: '160px' }}
              spellCheck={false}
            />
            {currentBody.body_html.length === 0 && (
              <p className="text-xs text-amber-600 mt-1">
                Sin contenido — se usará el texto por defecto del sistema al enviar.
              </p>
            )}
          </div>

          {/* Variable guide */}
          <div className="px-4 pb-4 pt-2">
            <p className="text-xs font-semibold text-gray-500 mb-2">Variables disponibles (clic para copiar)</p>
            <div className="flex flex-wrap gap-1.5">
              {VARIABLE_GUIDE.map(({ var: v, desc }) => (
                <button
                  key={v}
                  type="button"
                  title={desc}
                  onClick={() => handleCopyVar(v)}
                  className={`px-2 py-1 rounded text-xs font-mono border transition-colors ${
                    copiedVar === v
                      ? 'border-green-400 bg-green-50 text-green-700'
                      : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50 hover:border-gray-400'
                  }`}
                >
                  {copiedVar === v ? '✓ copiado' : v}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
