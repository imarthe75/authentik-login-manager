import React, { useState, useEffect, useRef } from 'react';
import DOMPurify from 'dompurify';
import { Theme, EmailEventType, EMAIL_EVENT_TYPES, EMAIL_EVENT_LABELS, EmailBody, EMPTY_EMAIL_BODY } from '../types/theme';
import { themesApi } from '../api/themesApi';
import { toUserMessage } from '../utils/errors';
import RichTextEditor from './RichTextEditor';

// El preview "completo" (renderedHtml) viene siempre del backend, que lee de
// BD — nunca refleja lo que se está tecleando sin guardar. Para dar feedback
// instantáneo mientras se edita, se envuelve el body_html actual (sin guardar)
// en un sobre de correo simplificado, sanitizado con DOMPurify.
function buildLiveHtml(bodyHtml: string): string {
  const safeBody = DOMPurify.sanitize(bodyHtml || '', { ADD_ATTR: ['style', 'target'] });
  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; color: #1a1a2e; background: #f4f4f4; margin: 0; padding: 24px 16px; }
  .envelope { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .env-body { padding: 28px; }
  .env-body h1 { font-size: 1.4em; margin: 0 0 0.5em; }
  .env-body h2 { font-size: 1.2em; margin: 0 0 0.4em; }
  .env-body p { margin: 0.4em 0; line-height: 1.6; }
  .env-body a { color: #4272A5; }
  .env-body table { width: 100%; }
</style>
</head>
<body>
<div class="envelope">
  <div class="env-body">${safeBody || '<p style="color:#9ca3af;font-style:italic">Sin contenido aún…</p>'}</div>
</div>
</body>
</html>`;
}

interface EmailEditorSplitProps {
  theme: Theme;
  activeEventType: string;
  onUpdateEmailBody: (eventType: string, body: EmailBody) => void;
  onSelectEvent: (eventType: string) => void;
}

const EMAIL_EVENT_META: Record<string, { icon: string; desc: string; badgeClass: string }> = {
  password_reset: {
    icon: '🔑',
    desc: 'Solicitud para crear una nueva contraseña',
    badgeClass: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  new_account: {
    icon: '✨',
    desc: 'Bienvenida con enlace para establecer contraseña por primera vez',
    badgeClass: 'bg-green-100 text-green-700 border-green-200',
  },
  account_lockout: {
    icon: '🔒',
    desc: 'Alerta de seguridad por intentos fallidos de acceso',
    badgeClass: 'bg-red-100 text-red-700 border-red-200',
  },
  security_change: {
    icon: '📝',
    desc: 'Confirmación de que la contraseña fue actualizada',
    badgeClass: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  email_verification: {
    icon: '✅',
    desc: 'Confirmación de dirección de correo electrónico',
    badgeClass: 'bg-blue-100 text-blue-700 border-blue-200',
  },
};

const DEFAULT_VARIABLES = [
  { var: '{{nombre_usuario}}', desc: 'Nombre completo (Israel Martínez)' },
  { var: '{{nombre_usuario_nombre}}', desc: 'Solo nombre (Israel)' },
  { var: '{{nombre_usuario_apellido}}', desc: 'Solo apellido (Martínez)' },
  { var: '{{usuario_login}}', desc: 'Usuario/ID (israelm)' },
  { var: '{{usuario_email}}', desc: 'Correo electrónico' },
  { var: '{{nombre_sistema}}', desc: 'Sistema donde ocurre el evento' },
  { var: '{{empresa_nombre}}', desc: 'Nombre de la empresa' },
  { var: '{{aplicacion_nombre}}', desc: 'Aplicación (Portal RH, CRM, etc.)' },
  { var: '{{aplicacion_slug}}', desc: 'ID único de la aplicación' },
  { var: '{{color_primario}}', desc: 'Color primario (hex)' },
  { var: '{{logo_url}}', desc: 'URL del logo' },
  { var: '{{ip_origen}}', desc: 'IP remota (192.168.1.100)' },
  { var: '{{navegador}}', desc: 'User-Agent/Navegador' },
  { var: '{{dispositivo}}', desc: 'Dispositivo (Windows, macOS, etc.)' },
  { var: '{{fecha_evento}}', desc: 'Fecha/hora legible (30/06/2026 14:32)' },
  { var: '{{fecha_hora_cambio}}', desc: 'Fecha/hora ISO del cambio' },
  { var: '{{realizado_por}}', desc: 'Quién ejecutó la acción' },
  { var: '{{url_acceso}}', desc: 'Enlace de acceso al sistema' },
  { var: '{{contacto_soporte}}', desc: 'Correo/teléfono de soporte' },
  { var: '{{footer_legal}}', desc: 'Leyenda legal' },
  { var: '{{anio}}', desc: 'Año para copyright' },
  { var: '{{rol_asignado}}', desc: '[Alta] Rol asignado' },
];

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Tipos con username requerido para la prueba real: se manda a un usuario
// real existente (password_reset/email_verification) o se le provocan
// intentos fallidos reales (account_lockout). new_account/security_change
// usan su propio usuario descartable (qa-email-test) en el backend.
const REAL_TEST_NEEDS_USERNAME = new Set(['password_reset', 'email_verification', 'account_lockout']);

export const EmailEditorSplit: React.FC<EmailEditorSplitProps> = ({
  theme,
  activeEventType,
  onUpdateEmailBody,
  onSelectEvent,
}) => {
  const savedBody: EmailBody = theme.email_bodies?.[activeEventType as EmailEventType] ?? { ...EMPTY_EMAIL_BODY };
  const [renderedHtml, setRenderedHtml] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [defaultBody, setDefaultBody] = useState<EmailBody | null>(null);
  const [variables, setVariables] = useState(DEFAULT_VARIABLES);
  const [copiedVar, setCopiedVar] = useState<string | null>(null);
  const [testEmail, setTestEmail] = useState('');
  const [testDisplayName, setTestDisplayName] = useState('');
  const [testStatus, setTestStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [testSending, setTestSending] = useState(false);
  const [testUsername, setTestUsername] = useState('');
  const [testRealStatus, setTestRealStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [testRealSending, setTestRealSending] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [liveHtml, setLiveHtml] = useState('');
  const [showVariables, setShowVariables] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const liveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toggleVariables = () => setShowVariables((prev) => {
    const next = !prev;
    if (next) setShowTemplates(false);
    return next;
  });
  const toggleTemplates = () => setShowTemplates((prev) => {
    const next = !prev;
    if (next) setShowVariables(false);
    return next;
  });
  const closeDrawers = () => { setShowVariables(false); setShowTemplates(false); };

  const eventHasCustomContent = (eventType: string) => {
    const body = theme.email_bodies?.[eventType as EmailEventType];
    return !!(body?.subject || body?.body_html);
  };

  // Si el tenant aún no personalizó este evento, se muestra (sin persistir) el
  // default definido en el backend — así el editor coincide con lo que ve el preview.
  const hasCustomContent = !!(savedBody.subject || savedBody.body_html);
  const currentBody: EmailBody = hasCustomContent
    ? savedBody
    : (defaultBody ?? { ...EMPTY_EMAIL_BODY });

  const loadPreview = async () => {
    try {
      setLoading(true);
      const html = await themesApi.getEmailPreview(
        theme.authentik_flow_slug,
        activeEventType,
        theme.authentik_app_slug
      );
      setRenderedHtml(html);
    } catch (err) {
      console.error('Error loading email preview:', err);
      setRenderedHtml('');
    } finally {
      setLoading(false);
    }
  };

  // Load rendered email preview (backend, refleja lo último GUARDADO) + default
  // body (para precargar el editor) cada vez que se cambia de evento/flow/app.
  useEffect(() => {
    const loadDefaultBody = async () => {
      try {
        const data = await themesApi.getDefaultEmailBody(
          theme.authentik_flow_slug,
          activeEventType,
          theme.authentik_app_slug
        );
        setDefaultBody({ subject: data.subject, body_html: data.body_html });
      } catch (err) {
        console.error('Error loading default email body:', err);
        setDefaultBody(null);
      }
    };
    setIsLive(false); // al cambiar de evento, siempre partir del estado guardado real
    loadPreview();
    loadDefaultBody();
  }, [activeEventType, theme.authentik_flow_slug, theme.authentik_app_slug]);

  // Cleanup del debounce del preview en vivo al desmontar.
  useEffect(() => {
    return () => {
      if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
    };
  }, []);

  // Catálogo de variables: se intenta cargar el real desde el backend (única
  // fuente de verdad); si falla, se mantiene la lista estática de arriba.
  useEffect(() => {
    const loadVariables = async () => {
      try {
        const data = await themesApi.getEmailTemplates();
        if (data.variables && data.variables.length > 0) {
          setVariables(data.variables.map((v: any) => ({ var: v.variable, desc: v.description })));
        }
      } catch (err) {
        console.error('Error loading email variables:', err);
      }
    };
    loadVariables();
  }, []);

  const handleCopyVar = (v: string) => {
    navigator.clipboard.writeText(v).catch(() => {});
    setCopiedVar(v);
    setTimeout(() => setCopiedVar(null), 1500);
  };

  const handleSendTest = async () => {
    const trimmed = testEmail.trim();
    if (!trimmed) return;
    if (trimmed.length > 254 || !EMAIL_RE.test(trimmed)) {
      setTestStatus({ ok: false, msg: '❌ Ingresa un correo electrónico válido.' });
      return;
    }
    setTestSending(true);
    setTestStatus(null);
    try {
      await themesApi.sendTestEmail(
        theme.authentik_flow_slug,
        activeEventType,
        trimmed,
        theme.authentik_app_slug ?? undefined,
        testDisplayName.trim() || undefined,
      );
      setTestStatus({ ok: true, msg: `✅ Enviado a ${trimmed}` });
    } catch (err: any) {
      setTestStatus({ ok: false, msg: `❌ ${toUserMessage(err, 'Error al enviar')}` });
    } finally {
      setTestSending(false);
    }
  };

  const handleSendTestReal = async () => {
    const needsUsername = REAL_TEST_NEEDS_USERNAME.has(activeEventType);
    const trimmed = testUsername.trim();
    if (needsUsername && !trimmed) return;
    setTestRealSending(true);
    setTestRealStatus(null);
    try {
      await themesApi.sendTestEmailReal(theme.authentik_flow_slug, activeEventType, trimmed);
      setTestRealStatus({ ok: true, msg: '✅ Disparado vía Authentik real' });
    } catch (err: any) {
      setTestRealStatus({ ok: false, msg: `❌ ${toUserMessage(err, 'Error al disparar')}` });
    } finally {
      setTestRealSending(false);
    }
  };

  const handleBodyChange = (field: keyof EmailBody, value: string) => {
    const updated = { ...currentBody, [field]: value };
    onUpdateEmailBody(activeEventType, updated);

    if (field === 'body_html') {
      // Debounce: no re-renderizar el preview en vivo en cada tecla, solo tras
      // una pausa breve.
      if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
      liveTimerRef.current = setTimeout(() => {
        setIsLive(true);
        setLiveHtml(buildLiveHtml(updated.body_html));
      }, 400);
    }
  };

  const handleDragStart = (e: React.DragEvent, variable: string) => {
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('text/plain', variable);
  };

  const handleShowFullPreview = () => {
    if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
    setIsLive(false);
    loadPreview();
  };

  return (
    <div className="w-full h-full relative flex gap-3 p-3 bg-gray-100 overflow-hidden">
      {/* Left: Editor (50%) */}
      <div className="flex-1 flex flex-col min-w-0 bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-3 border-b border-gray-200 bg-gray-50">
          <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
            ✏️ Editar: {EMAIL_EVENT_LABELS[activeEventType as EmailEventType] || activeEventType}
          </h3>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {/* Subject */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Asunto ({(currentBody.subject ?? '').length}/200)
            </label>
            <input
              type="text"
              maxLength={200}
              value={currentBody.subject}
              onChange={(e) => handleBodyChange('subject', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="Ej: Bienvenido a {{nombre_sistema}}"
            />
          </div>

          {/* Body HTML */}
          <div className="flex-1 flex flex-col min-h-0">
            <label className="block text-xs font-semibold text-gray-700 mb-1">Contenido HTML</label>
            <div className="flex-1 min-h-0">
              <RichTextEditor
                value={currentBody.body_html}
                onChange={(v) => handleBodyChange('body_html', v)}
                placeholder={`Edita el contenido del correo... (escribe {{ para insertar una variable)`}
                minHeight="100%"
                variables={variables}
              />
            </div>
          </div>

          {/* Enviar correo de prueba */}
          <div className="pt-3 border-t border-gray-100 shrink-0">
            <p className="text-xs font-semibold text-gray-600 mb-2">
              Correo de prueba
              <span className="ml-1.5 text-gray-400 font-normal">
                — {EMAIL_EVENT_LABELS[activeEventType as EmailEventType] || activeEventType}
              </span>
            </p>
            <div className="flex gap-2">
              <input
                type="email"
                value={testEmail}
                onChange={(e) => { setTestEmail(e.target.value); setTestStatus(null); }}
                onKeyDown={(e) => e.key === 'Enter' && handleSendTest()}
                placeholder="destinatario@ejemplo.com"
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <input
                type="text"
                value={testDisplayName}
                onChange={(e) => { setTestDisplayName(e.target.value); setTestStatus(null); }}
                onKeyDown={(e) => e.key === 'Enter' && handleSendTest()}
                placeholder="Nombre (opcional, ej. Israel Martínez)"
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button
                type="button"
                onClick={handleSendTest}
                disabled={testSending || !testEmail.trim()}
                className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {testSending ? 'Enviando…' : '✉ Enviar prueba'}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Sin nombre, se adivina del correo (israel.martinez@... → "Israel Martinez") — útil poner uno real para buzones personales (gmail, hotmail).
            </p>
            {testStatus && (
              <p className={`text-xs mt-1.5 font-medium ${testStatus.ok ? 'text-green-600' : 'text-red-600'}`}>
                {testStatus.msg}
              </p>
            )}

            {/* Prueba real vía Authentik: EmailStage/evento real, no SMTP directo */}
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-2">
                Prueba real (Authentik)
                {activeEventType === 'account_lockout' && (
                  <span className="ml-1.5 text-amber-600 font-normal">— provoca 6 intentos fallidos reales, puede bloquear la cuenta</span>
                )}
              </p>
              <div className="flex gap-2">
                {REAL_TEST_NEEDS_USERNAME.has(activeEventType) && (
                  <input
                    type="text"
                    value={testUsername}
                    onChange={(e) => { setTestUsername(e.target.value); setTestRealStatus(null); }}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendTestReal()}
                    placeholder="username existente en Authentik"
                    className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                  />
                )}
                <button
                  type="button"
                  onClick={handleSendTestReal}
                  disabled={testRealSending || (REAL_TEST_NEEDS_USERNAME.has(activeEventType) && !testUsername.trim())}
                  className="px-3 py-1.5 bg-amber-600 text-white text-xs font-semibold rounded-lg hover:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                >
                  {testRealSending ? 'Disparando…' : '⚡ Prueba real'}
                </button>
              </div>
              {testRealStatus && (
                <p className={`text-xs mt-1.5 font-medium ${testRealStatus.ok ? 'text-green-600' : 'text-red-600'}`}>
                  {testRealStatus.msg}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Preview (50%) */}
      <div className="flex-1 flex flex-col min-w-0 bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-3 border-b border-gray-200 bg-gray-50 shrink-0 flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
              👁️ Preview
              {isLive && (
                <span className="text-[10px] bg-blue-50 text-blue-600 border border-blue-200 rounded px-1.5 py-0.5 font-medium normal-case">
                  En vivo
                </span>
              )}
            </h3>
            {loading && <p className="text-xs text-gray-500 mt-1">⏳ Renderizando...</p>}
            {isLive && !loading && (
              <p className="text-[10px] text-gray-400 mt-1">Aproximación sin guardar — colores/logo reales al ver la plantilla completa</p>
            )}
          </div>
          <button
            type="button"
            onClick={handleShowFullPreview}
            disabled={loading}
            className="shrink-0 text-[10px] text-gray-500 hover:text-blue-600 border border-gray-300 hover:border-blue-400 rounded px-2 py-1 transition-colors disabled:opacity-40"
            title="Recargar la vista previa completa con la plantilla guardada"
          >
            ↻ Completa
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-hidden bg-gray-50 p-2">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <div className="animate-spin text-2xl mb-2">⌛</div>
                <p className="text-xs font-medium">Cargando...</p>
              </div>
            </div>
          ) : (isLive ? liveHtml : renderedHtml) ? (
            <div className="bg-white rounded border border-gray-200 w-full h-full overflow-hidden">
              <iframe
                srcDoc={isLive ? liveHtml : renderedHtml}
                className="w-full h-full border-none rounded"
                title="Email preview"
                sandbox=""
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center text-xs">
                <p className="font-medium">📧 Sin contenido</p>
                <p className="mt-1 opacity-70">Edita para ver preview</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Backdrop: cierra el drawer abierto al hacer clic fuera */}
      {(showVariables || showTemplates) && (
        <div
          className="absolute inset-0 bg-black/10 z-20"
          onClick={closeDrawers}
        />
      )}

      {/* Pestaña fija para abrir/cerrar el drawer de plantillas (izquierda) */}
      <button
        type="button"
        onClick={toggleTemplates}
        className={`absolute top-1/2 -translate-y-1/2 z-40 flex items-center gap-1.5 px-1.5 py-3 rounded-r-lg shadow-md border border-l-0 border-blue-700 bg-blue-600 text-white text-[11px] font-semibold hover:bg-blue-700 transition-[left] duration-300 ${
          showTemplates ? 'left-80' : 'left-0'
        }`}
        style={{ writingMode: 'vertical-rl', transform: 'translateY(-50%) rotate(180deg)' }}
        title={showTemplates ? 'Ocultar plantillas' : 'Mostrar plantillas'}
      >
        {showTemplates ? '›' : '‹'} 🗂️ Plantillas ({EMAIL_EVENT_TYPES.length})
      </button>

      {/* Drawer de Plantillas (colapsable, se superpone sobre el Editor) */}
      <div
        className={`absolute top-0 left-0 h-full w-80 bg-white shadow-2xl border-r border-gray-200 z-30 flex flex-col transition-transform duration-300 ${
          showTemplates ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-blue-100 flex items-center justify-between shrink-0">
          <div>
            <h3 className="text-xs font-bold text-blue-900 uppercase tracking-wider">
              🗂️ Plantillas
            </h3>
            <p className="text-[10px] text-blue-700 mt-0.5">Selecciona el correo a editar</p>
          </div>
          <button
            type="button"
            onClick={() => setShowTemplates(false)}
            className="text-blue-900 hover:text-blue-600 text-lg leading-none px-1"
            title="Cerrar"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {EMAIL_EVENT_TYPES.map((et) => {
            const meta = EMAIL_EVENT_META[et];
            const isActive = et === activeEventType;
            const customized = eventHasCustomContent(et);
            return (
              <button
                key={et}
                type="button"
                onClick={() => { onSelectEvent(et); setShowTemplates(false); }}
                className={`w-full text-left p-2.5 rounded-lg border transition-all ${
                  isActive
                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-300'
                    : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/50'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${meta.badgeClass}`}>
                    {meta.icon} {EMAIL_EVENT_LABELS[et]}
                  </span>
                  {customized && (
                    <span className="text-[9px] text-green-600 font-medium shrink-0" title="Este tenant personalizó este correo">
                      ● Personalizado
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-gray-500 mt-1.5 leading-snug">{meta.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Pestaña fija para abrir/cerrar el drawer de variables (derecha) */}
      <button
        type="button"
        onClick={toggleVariables}
        className={`absolute top-1/2 -translate-y-1/2 z-40 flex items-center gap-1.5 px-1.5 py-3 rounded-l-lg shadow-md border border-r-0 border-blue-700 bg-blue-600 text-white text-[11px] font-semibold hover:bg-blue-700 transition-[right] duration-300 ${
          showVariables ? 'right-80' : 'right-0'
        }`}
        style={{ writingMode: 'vertical-rl' }}
        title={showVariables ? 'Ocultar variables' : 'Mostrar variables'}
      >
        {showVariables ? '›' : '‹'} 📋 Variables ({variables.length})
      </button>

      {/* Drawer de Variables (colapsable, se superpone sobre el Preview) */}
      <div
        className={`absolute top-0 right-0 h-full w-80 bg-white shadow-2xl border-l border-gray-200 z-30 flex flex-col transition-transform duration-300 ${
          showVariables ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="p-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-blue-100 flex items-center justify-between shrink-0">
          <div>
            <h3 className="text-xs font-bold text-blue-900 uppercase tracking-wider">
              📋 Variables
            </h3>
            <p className="text-[10px] text-blue-700 mt-0.5">Arrastra o haz clic para copiar</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-blue-900 bg-white px-2 py-1 rounded">
              {variables.length}
            </span>
            <button
              type="button"
              onClick={() => setShowVariables(false)}
              className="text-blue-900 hover:text-blue-600 text-lg leading-none px-1"
              title="Cerrar"
            >
              ×
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          <div className="space-y-2">
            {variables.map((item) => (
              <div
                key={item.var}
                draggable
                onDragStart={(e) => handleDragStart(e, item.var)}
                onClick={() => handleCopyVar(item.var)}
                className={`p-2.5 rounded-lg border cursor-grab active:cursor-grabbing transition-all group ${
                  copiedVar === item.var
                    ? 'border-green-400 bg-green-50'
                    : 'bg-gradient-to-r from-blue-50 to-blue-100 border-blue-200 hover:from-blue-100 hover:to-blue-200 hover:border-blue-400'
                }`}
                title={`${item.desc} (clic para copiar)`}
              >
                <div className={`text-xs font-mono font-bold break-words ${copiedVar === item.var ? 'text-green-700' : 'text-blue-800 group-hover:text-blue-900'}`}>
                  {copiedVar === item.var ? `✓ ${item.var}` : item.var}
                </div>
                <div className="text-xs text-blue-600 group-hover:text-blue-700 mt-0.5 leading-snug">
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
