// Wrapper mínimo sobre fetch para endpoints que requieren la cookie de sesión
// de admin (ver AdminLoginGate). La cookie tiene un TTL de 8h (session.py) —
// sin esto, un 401 por sesión vencida se veía como un error genérico
// ("Failed to save theme") en vez de devolver al usuario al login.
export const SESSION_EXPIRED_EVENT = 'admin-session-expired';

export async function adminFetch(input: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
  return response;
}
