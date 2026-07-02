import { Theme, EmailBodies } from '../types/theme';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY || '';

const getHeaders = (hostname?: string) => {
  const headers: any = {
    'Content-Type': 'application/json',
    'X-Admin-Key': ADMIN_KEY,
  };

  // Agregar X-Tenant-Domain si se proporciona hostname
  if (hostname) {
    headers['X-Tenant-Domain'] = hostname;
  } else {
    // Si no se proporciona, usar el hostname actual
    headers['X-Tenant-Domain'] = window.location.hostname;
  }

  return headers;
};

// Truncates 8-digit hex (#RRGGBBAA) to 6-digit (#RRGGBB) to satisfy backend validation
const toHex6 = (v: unknown): unknown => {
  if (typeof v === 'string' && /^#[0-9a-fA-F]{8}$/.test(v)) return v.slice(0, 7);
  return v;
};

const COLOR_FIELDS = [
  'primary_color', 'hover_color', 'card_bg_color', 'panel_bg_color',
  'bg_flat_color', 'bg_gradient_from', 'bg_gradient_to',
] as const;

const sanitizeColors = (theme: Theme): Theme => {
  const patched = { ...theme };
  for (const field of COLOR_FIELDS) {
    (patched as any)[field] = toHex6((patched as any)[field]);
  }
  return patched;
};

export const themesApi = {
  async getThemes(skip = 0, limit = 50): Promise<Theme[]> {
    const response = await fetch(`${API_BASE}/api/v1/themes?skip=${skip}&limit=${limit}`, {
      method: 'GET',
      headers: getHeaders(),
    });
    if (!response.ok) throw new Error(`Failed to fetch themes list: ${response.statusText}`);
    return response.json();
  },

  async getTheme(slug: string, appSlug?: string | null): Promise<Theme> {
    const url = appSlug
      ? `${API_BASE}/api/v1/themes/${slug}?app_slug=${appSlug}`
      : `${API_BASE}/api/v1/themes/${slug}`;
    const response = await fetch(url, { method: 'GET', headers: getHeaders() });
    if (!response.ok) throw new Error(`Failed to fetch theme for '${slug}': ${response.statusText}`);
    return response.json();
  },

  async upsertTheme(theme: Theme): Promise<Theme> {
    const response = await fetch(`${API_BASE}/api/v1/themes`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(sanitizeColors(theme)),
    });
    if (!response.ok) throw new Error(`Failed to save theme: ${response.statusText}`);
    return response.json();
  },

  async patchTheme(slug: string, data: Partial<Theme> & { email_bodies?: EmailBodies }): Promise<Theme> {
    const response = await fetch(`${API_BASE}/api/v1/themes/${slug}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`Failed to patch theme: ${response.statusText}`);
    return response.json();
  },

  async deleteTheme(slug: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/v1/themes/${slug}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!response.ok) throw new Error(`Failed to delete theme: ${response.statusText}`);
  },

  async invalidatePublicCache(slug: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/v1/public/theme/invalidate-cache/${slug}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      console.warn(`Failed to invalidate public Valkey cache for flow slug ${slug}`);
    }
  },

  async getAuthentikApplications(): Promise<{ slug: string; name: string }[]> {
    const response = await fetch(`${API_BASE}/api/v1/themes/authentik/applications`, {
      method: 'GET',
      headers: getHeaders(),
    });
    if (!response.ok) throw new Error(`Failed to fetch Authentik applications: ${response.statusText}`);
    return response.json();
  },

  async deployTheme(flowSlug: string): Promise<{ status: string; path: string }> {
    const response = await fetch(`${API_BASE}/api/v1/themes/${flowSlug}/deploy`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(detail?.detail || `Deploy failed: ${response.statusText}`);
    }
    return response.json();
  },

  async sendTestEmail(
    flowSlug: string,
    eventType: string,
    toEmail: string,
    appSlug?: string,
  ): Promise<{ status: string; to: string; subject: string }> {
    const response = await fetch(`${API_BASE}/api/v1/themes/${flowSlug}/emails/test`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ to_email: toEmail, event_type: eventType, app_slug: appSlug ?? null }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(detail?.detail || `Error al enviar: ${response.statusText}`);
    }
    return response.json();
  },

  async getDefaultEmailBody(
    flowSlug: string,
    eventType: string,
    appSlug?: string | null
  ): Promise<{ subject: string; body_html: string }> {
    const params = appSlug ? `?app_slug=${appSlug}` : '';
    const response = await fetch(
      `${API_BASE}/api/v1/themes/${flowSlug}/emails/default-body/${eventType}${params}`,
      { method: 'GET', headers: getHeaders() }
    );
    if (!response.ok) throw new Error(`Failed to fetch default email body: ${response.statusText}`);
    return response.json();
  },

  async getEmailPreview(flowSlug: string, eventType: string, appSlug?: string | null): Promise<string> {
    const params = appSlug ? `?app_slug=${appSlug}` : '';
    const response = await fetch(
      `${API_BASE}/api/v1/themes/${flowSlug}/emails/preview/${eventType}${params}`,
      { method: 'GET', headers: getHeaders() }
    );
    if (!response.ok) throw new Error(`Email preview failed: ${response.statusText}`);
    return response.text();
  },

  async getEmailTemplates(): Promise<{
    templates: Record<string, {
      name: string;
      description: string;
      default_subject: string;
      default_body: string;
    }>;
    variables: Array<{ variable: string; description: string }>;
    event_types: string[];
    count: number;
  }> {
    const response = await fetch(`${API_BASE}/api/v1/public/email-templates`, {
      method: 'GET',
    });
    if (!response.ok) throw new Error(`Failed to fetch email templates: ${response.statusText}`);
    return response.json();
  },
};
