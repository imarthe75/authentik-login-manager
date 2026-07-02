export const createFetchHeaders = (hostname: string, adminKey?: string): HeadersInit => {
  const headers: HeadersInit = {
    'X-Tenant-Domain': hostname,
    'Content-Type': 'application/json',
  };

  if (adminKey) {
    (headers as any)['X-Admin-Key'] = adminKey;
  }

  return headers;
};

export interface FetchOptions extends RequestInit {
  headers?: HeadersInit;
}

export const apiFetch = async (
  url: string,
  options: FetchOptions = {},
  hostname: string,
  adminKey?: string
) => {
  const headers = createFetchHeaders(hostname, adminKey);
  const finalUrl = url.startsWith('/') ? `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${url}` : url;

  return fetch(finalUrl, {
    ...options,
    headers: { ...headers, ...options.headers },
  });
};
