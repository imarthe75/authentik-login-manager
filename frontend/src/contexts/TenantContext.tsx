import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface Tenant {
  tenant_id: string;
  tenant_name: string;
  domain_pattern: string;
  primary_color: string;
  secondary_color: string;
}

const DEFAULT_TENANT: Tenant = {
  tenant_id: '00000000-0000-0000-0000-000000000001',
  tenant_name: 'CASMARTS Core',
  domain_pattern: 'casmarts.local',
  primary_color: '#4272A5',
  secondary_color: '#2d5580',
};

export interface TenantContextType {
  tenant: Tenant;
  hostname: string;
  loading: boolean;
  error: string | null;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

/**
 * Aplica los colores de marca del tenant como custom properties CSS sobre
 * <html> — consumidas por .tenant-accent-* en index.css. Exportada para que
 * TenantSelector.tsx pueda reusarla cuando el admin elige a mano qué tenant
 * editar (que puede ser distinto del tenant detectado por hostname aquí).
 */
export function applyTenantAccent(primaryColor?: string | null, hoverColor?: string | null): void {
  const root = document.documentElement;
  if (primaryColor) root.style.setProperty('--tenant-accent', primaryColor);
  if (hoverColor) root.style.setProperty('--tenant-accent-hover', hoverColor);
}

export const TenantProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tenant, setTenant] = useState<Tenant>(DEFAULT_TENANT);
  const [hostname, setHostname] = useState<string>(window.location.hostname || 'localhost');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const detectAndResolveTenant = async () => {
      try {
        const detectedHostname = window.location.hostname;
        setHostname(detectedHostname);

        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const response = await fetch(`${apiBase}/api/v1/tenant/resolve`, {
          method: 'GET',
          headers: {
            'X-Tenant-Domain': detectedHostname,
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          setTenant(data);
          applyTenantAccent(data.primary_color, data.secondary_color);
          setError(null);
        } else {
          setTenant(DEFAULT_TENANT);
          setError(`HTTP ${response.status}`);
        }
      } catch (err) {
        setTenant(DEFAULT_TENANT);
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        console.debug('Tenant resolution fallback:', errorMsg);
      } finally {
        setLoading(false);
      }
    };

    detectAndResolveTenant();
  }, []);

  return (
    <TenantContext.Provider value={{ tenant, hostname, loading, error }}>
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = (): TenantContextType => {
  const context = useContext(TenantContext);
  if (!context) {
    return {
      tenant: DEFAULT_TENANT,
      hostname: window.location.hostname || 'localhost',
      loading: false,
      error: 'TenantContext not found',
    };
  }
  return context;
};
