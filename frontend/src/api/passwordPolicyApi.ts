import { PasswordPolicy, PasswordPolicyUpdate } from '../types/passwordPolicy';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const HEADERS = {
  'Content-Type': 'application/json',
};

// Política global (Authentik solo tiene una PasswordPolicy real hoy) — a
// diferencia de themesApi, no lleva X-Tenant-Domain. Autenticación admin vía
// cookie de sesión HttpOnly (credentials: 'include'), no header estático.
export const passwordPolicyApi = {
  async get(): Promise<PasswordPolicy> {
    const response = await fetch(`${API_BASE}/api/v1/password-policy`, {
      method: 'GET',
      headers: HEADERS,
      credentials: 'include',
    });
    if (!response.ok) throw new Error(`Failed to fetch password policy: ${response.statusText}`);
    return response.json();
  },

  async update(patch: PasswordPolicyUpdate): Promise<PasswordPolicy> {
    const response = await fetch(`${API_BASE}/api/v1/password-policy`, {
      method: 'PATCH',
      headers: HEADERS,
      credentials: 'include',
      body: JSON.stringify(patch),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail ? JSON.stringify(body.detail) : `Failed to update password policy: ${response.statusText}`);
    }
    return response.json();
  },

  async resync(): Promise<PasswordPolicy> {
    const response = await fetch(`${API_BASE}/api/v1/password-policy/resync`, {
      method: 'POST',
      headers: HEADERS,
      credentials: 'include',
    });
    if (!response.ok) throw new Error(`Failed to resync password policy: ${response.statusText}`);
    return response.json();
  },
};
