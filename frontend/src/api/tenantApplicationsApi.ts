import { adminFetch } from './adminFetch';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface TenantApplicationLink {
  id: string;
  tenant_id: string;
  application_slug: string;
  application_name: string;
  link_source: 'group_convention' | 'manual';
  is_confirmed: boolean;
}

export interface AuthentikAppRef {
  slug: string;
  name: string;
}

export interface TenantApplicationsResponse {
  linked: TenantApplicationLink[];
  unassigned: AuthentikAppRef[];
}

const headers = { 'Content-Type': 'application/json' };

export const tenantApplicationsApi = {
  async list(tenantId?: string | null): Promise<TenantApplicationsResponse> {
    const url = tenantId
      ? `${API_BASE}/api/v1/tenant/applications?tenant_id=${tenantId}`
      : `${API_BASE}/api/v1/tenant/applications`;
    const response = await adminFetch(url, { method: 'GET', headers, credentials: 'include' });
    if (!response.ok) throw new Error(`Failed to fetch tenant applications: ${response.statusText}`);
    return response.json();
  },

  async link(tenantId: string, applicationSlug: string, applicationName?: string): Promise<TenantApplicationLink> {
    const response = await adminFetch(`${API_BASE}/api/v1/tenant/applications`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ tenant_id: tenantId, application_slug: applicationSlug, application_name: applicationName ?? null }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(detail?.detail || `Error al enlazar aplicación: ${response.statusText}`);
    }
    return response.json();
  },

  async unlink(linkId: string): Promise<void> {
    const response = await adminFetch(`${API_BASE}/api/v1/tenant/applications/${linkId}`, {
      method: 'DELETE',
      headers,
      credentials: 'include',
    });
    if (!response.ok) throw new Error(`Failed to unlink application: ${response.statusText}`);
  },
};
