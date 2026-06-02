import { Theme } from '../types/theme';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY || '';

const getHeaders = () => {
  return {
    'Content-Type': 'application/json',
    'X-Admin-Key': ADMIN_KEY,
  };
};

export const themesApi = {
  async getThemes(skip = 0, limit = 50): Promise<Theme[]> {
    const response = await fetch(`${API_BASE}/api/v1/themes?skip=${skip}&limit=${limit}`, {
      method: 'GET',
      headers: getHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch themes list: ${response.statusText}`);
    }
    return response.json();
  },

  async getTheme(slug: string, appSlug?: string | null): Promise<Theme> {
    const url = appSlug 
      ? `${API_BASE}/api/v1/themes/${slug}?app_slug=${appSlug}`
      : `${API_BASE}/api/v1/themes/${slug}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: getHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch theme for '${slug}': ${response.statusText}`);
    }
    return response.json();
  },

  async upsertTheme(theme: Theme): Promise<Theme> {
    const response = await fetch(`${API_BASE}/api/v1/themes`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(theme),
    });
    if (!response.ok) {
      throw new Error(`Failed to save theme: ${response.statusText}`);
    }
    return response.json();
  },

  async patchTheme(slug: string, theme: Partial<Theme>): Promise<Theme> {
    const response = await fetch(`${API_BASE}/api/v1/themes/${slug}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify(theme),
    });
    if (!response.ok) {
      throw new Error(`Failed to patch theme: ${response.statusText}`);
    }
    return response.json();
  },

  async deleteTheme(slug: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/v1/themes/${slug}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to delete theme: ${response.statusText}`);
    }
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
    if (!response.ok) {
      throw new Error(`Failed to fetch Authentik applications: ${response.statusText}`);
    }
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
};
