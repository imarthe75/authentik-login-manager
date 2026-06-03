import React, { useEffect, useRef, useState, useCallback } from 'react';
import { EmailEventType, EMAIL_EVENT_LABELS } from '../../types/theme';
import { themesApi } from '../../api/themesApi';

interface EmailPreviewProps {
  flowSlug: string;
  eventType: EmailEventType;
  refreshKey?: number;
}

export const EmailPreview: React.FC<EmailPreviewProps> = ({ flowSlug, eventType, refreshKey }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const blobUrlRef = useRef<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subject, setSubject] = useState<string>('');

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const html = await themesApi.getEmailPreview(flowSlug, eventType);

      // Extract subject from <title> tag for inbox simulation
      const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i);
      setSubject(titleMatch?.[1]?.trim() ?? EMAIL_EVENT_LABELS[eventType]);

      // Revoke previous blob URL to avoid memory leaks
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }

      // Use a blob: URL instead of doc.write() — avoids sandbox "allow-scripts" requirement
      const blob = new Blob([html], { type: 'text/html; charset=utf-8' });
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;

      if (iframeRef.current) {
        iframeRef.current.src = url;
      }
    } catch (err: any) {
      setError(err?.message ?? 'Error al cargar la vista previa del correo.');
    } finally {
      setLoading(false);
    }
  }, [flowSlug, eventType]);

  useEffect(() => {
    loadPreview();
    return () => {
      // Cleanup blob URL on unmount
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
    };
  }, [loadPreview, refreshKey]);

  return (
    <div className="flex flex-col h-full border border-gray-200 rounded-xl overflow-hidden bg-white">
      {/* Inbox simulation strip */}
      <div className="shrink-0 bg-gray-50 border-b border-gray-200 px-4 py-2.5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xs shrink-0">
          NO
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-gray-800 truncate">noreply@casmarts.internal</p>
          <p className="text-sm font-medium text-gray-900 truncate">
            {loading ? 'Cargando…' : (subject || EMAIL_EVENT_LABELS[eventType])}
          </p>
        </div>
        <button
          type="button"
          onClick={loadPreview}
          disabled={loading}
          className="ml-auto shrink-0 text-xs text-gray-500 hover:text-blue-600 border border-gray-300 hover:border-blue-400 rounded px-2 py-1 transition-colors disabled:opacity-40"
          title="Recargar vista previa"
        >
          ↻ Actualizar
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
        {/* blob: src avoids sandbox script-blocking issue; allow-same-origin needed for blob: */}
        <iframe
          ref={iframeRef}
          title={`Vista previa: ${EMAIL_EVENT_LABELS[eventType]}`}
          sandbox="allow-same-origin"
          className="w-full h-full border-0"
          style={{ minHeight: '400px' }}
        />
      </div>
    </div>
  );
};
