// Patrones que sugieren que un mensaje de error trae detalles internos del
// backend (rutas de archivo, stack traces, nombres de tabla/conexión) que no
// deben mostrarse tal cual al usuario final.
const INTERNAL_DETAIL_PATTERNS = [
  /traceback/i,
  /file "/i,
  /\bat\s+\S+\.(py|ts|js):\d+/i,
  /sqlalchemy/i,
  /postgres|asyncpg|psycopg/i,
  /connection refused/i,
  /\btable\b.*\bnot found\b/i,
  /\/[a-z0-9_\-./]+\.(py|json|env)\b/i,
  /valkey|redis/i,
];

const GENERIC_FALLBACK = 'Ocurrió un error inesperado. Intenta de nuevo o contacta a soporte.';

/**
 * Devuelve un mensaje seguro para mostrar en la UI. Los mensajes cortos y sin
 * patrones de detalle interno se muestran tal cual (siguen siendo útiles,
 * ej. "Email inválido"); el resto se reemplaza por un mensaje genérico para
 * evitar filtrar detalles de infraestructura al usuario final.
 */
export function toUserMessage(err: unknown, fallback: string = GENERIC_FALLBACK): string {
  const raw = err instanceof Error ? err.message : typeof err === 'string' ? err : '';
  if (!raw) return fallback;
  if (raw.length > 150) return fallback;
  if (INTERNAL_DETAIL_PATTERNS.some((pattern) => pattern.test(raw))) return fallback;
  return raw;
}
