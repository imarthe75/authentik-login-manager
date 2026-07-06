const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const authApi = {
  async status(): Promise<boolean> {
    const response = await fetch(`${API_BASE}/api/v1/auth/status`, {
      method: 'GET',
      credentials: 'include',
    });
    if (!response.ok) return false;
    const data = await response.json();
    return !!data.authenticated;
  },

  async login(adminKey: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_key: adminKey }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(detail?.detail || 'Credenciales inválidas');
    }
  },

  async logout(): Promise<void> {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  },
};
