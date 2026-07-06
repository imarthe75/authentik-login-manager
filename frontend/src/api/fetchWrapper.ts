export const createFetchHeaders = (hostname: string): HeadersInit => ({
  'X-Tenant-Domain': hostname,
  'Content-Type': 'application/json',
});

export interface FetchOptions extends RequestInit {
  headers?: HeadersInit;
}

// La autenticación admin viaja como cookie de sesión HttpOnly (ver
// AdminLoginGate/authApi), de ahí `credentials: 'include'` en cada llamada —
// nunca un header con una clave estática embebida en el bundle.
export const apiFetch = async (
  url: string,
  options: FetchOptions = {},
  hostname: string,
) => {
  const headers = createFetchHeaders(hostname);
  const finalUrl = url.startsWith('/') ? `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${url}` : url;

  return fetch(finalUrl, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...options.headers },
  });
};
