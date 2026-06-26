import React, { useEffect, useRef, useState, useCallback } from 'react';
import { EmailEventType, EMAIL_EVENT_LABELS } from '../../types/theme';
import { themesApi } from '../../api/themesApi';

interface EmailPreviewProps {
  flowSlug: string;
  eventType: EmailEventType;
  refreshKey?: number;
  liveBodyHtml?: string;
}

// Wrap raw body_html in a minimal email-like envelope for instant preview
function buildLiveHtml(bodyHtml: string): string {
  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px; color: #1a1a2e; background: #f4f4f4;
    margin: 0; padding: 24px 16px;
  }
  .envelope {
    max-width: 600px; margin: 0 auto; background: #fff;
    border-radius: 8px; overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }
  .env-header {
    background: #4272A5; padding: 20px 28px;
    color: #fff; font-size: 15px; font-weight: 600;
  }
  .env-body {
    padding: 28px;
  }
  .env-body h1 { font-size: 1.4em; margin: 0 0 0.5em; }
  .env-body h2 { font-size: 1.2em; margin: 0 0 0.4em; }
  .env-body p  { margin: 0.4em 0; line-height: 1.6; }
  .env-body a  { color: #4272A5; }
  .env-body ul { padding-left: 1.4em; margin: 0.4em 0; }
  .env-body ol { padding-left: 1.4em; margin: 0.4em 0; }
  .env-body hr { border: none; border-top: 1px solid #e5e7eb; margin: 1em 0; }
  .env-footer {
    padding: 14px 28px;
    background: #f9fafb; border-top: 1px solid #e5e7eb;
    font-size: 11px; color: #9ca3af; text-align: center;
  }
  .live-badge {
    display: inline-block; background: #dbeafe; color: #1e40af;
    font-size: 10px; font-weight: 600; letter-spacing: 0.05em;
    padding: 2px 8px; border-radius: 4px; margin-left: 8px;
    vertical-align: middle;
  }
</style>
</head>
<body>
<div class="envelope">
  <div class="env-header">
    CASMARTS <span class="live-badge">VISTA PREVIA EN VIVO</span>
  </div>
  <div class="env-body">${bodyHtml || '<p style="color:#9ca3af;font-style:italic">Sin contenido aún…</p>'}</div>
  <div class="env-footer">noreply@casmarts.internal · Este es un correo automático</div>
</div>
</body>
</html>`;
}

export const EmailPreview: React.FC<EmailPreviewProps> = ({
  flowSlug,
  eventType,
  refreshKey,
  liveBodyHtml,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const blobUrlRef = useRef<string | null>(null);
  const liveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subject, setSubject] = useState<string>('');
  const [isLive, setIsLive] = useState(false);

  const setIframeSrc = useCallback((html: string) => {
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    const blob = new Blob([html], { type: 'text/html; charset=utf-8' });
    const url = URL.createObjectURL(blob);
    blobUrlRef.current = url;
    if (iframeRef.current) iframeRef.current.src = url;
  }, []);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setIsLive(false);
    setError(null);
    try {
      const html = await themesApi.getEmailPreview(flowSlug, eventType);
      const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i);
      setSubject(titleMatch?.[1]?.trim() ?? EMAIL_EVENT_LABELS[eventType]);
      setIframeSrc(html);
    } catch (err: any) {
      setError(err?.message ?? 'Error al cargar la vista previa del correo.');
    } finally {
      setLoading(false);
    }
  }, [flowSlug, eventType, setIframeSrc]);

  // Initial load + force-refresh from refreshKey
  useEffect(() => {
    loadPreview();
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, [loadPreview, refreshKey]);

  // Debounced live preview when body_html changes
  useEffect(() => {
    if (liveBodyHtml === undefined) return;
    if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
    liveTimerRef.current = setTimeout(() => {
      setIsLive(true);
      setError(null);
      setIframeSrc(buildLiveHtml(liveBodyHtml));
    }, 400);
    return () => {
      if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
    };
  }, [liveBodyHtml, setIframeSrc]);

  return (
    <div className="flex flex-col h-full border border-gray-200 rounded-xl overflow-hidden bg-white">
      {/* Inbox simulation strip */}
      <div className="shrink-0 bg-gray-50 border-b border-gray-200 px-4 py-2.5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xs shrink-0">
          NO
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-gray-800 truncate">noreply@casmarts.internal</p>
          <p className="text-sm font-medium text-gray-900 truncate">
            {loading ? 'Cargando…' : (subject || EMAIL_EVENT_LABELS[eventType])}
          </p>
        </div>
        {isLive && (
          <span className="shrink-0 text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded px-2 py-0.5 font-medium">
            En vivo
          </span>
        )}
        <button
          type="button"
          onClick={loadPreview}
          disabled={loading}
          className="shrink-0 text-xs text-gray-500 hover:text-blue-600 border border-gray-300 hover:border-blue-400 rounded px-2 py-1 transition-colors disabled:opacity-40"
          title="Recargar vista previa completa (con plantilla guardada)"
        >
          ↻ Completa
        </button>
      </div>

      {/* iframe body */}
      <div className="flex-1 relative min-h-0">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
            <div className="text-sm text-gray-500">Cargando vista previa…</div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center p-6 z-10 bg-white">
            <p className="text-sm text-red-600 text-center">{error}</p>
          </div>
        )}
        <iframe
          ref={iframeRef}
          title={`Vista previa: ${EMAIL_EVENT_LABELS[eventType]}`}
          className="w-full h-full border-0"
          style={{ minHeight: '400px' }}
        />
      </div>
    </div>
  );
};
