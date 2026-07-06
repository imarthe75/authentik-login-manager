import React, { useEffect, useState } from 'react';
import { themesApi } from '../api/themesApi';

export interface TenantOption {
  tenant_id: string;
  tenant_name: string;
  domain_pattern: string;
  primary_color: string;
  secondary_color: string;
}

interface TenantSelectorProps {
  selectedTenantId: string | null;
  onSelectTenant: (tenantId: string, tenantName: string) => void;
  disabled?: boolean;
}

export const TenantSelector: React.FC<TenantSelectorProps> = ({
  selectedTenantId,
  onSelectTenant,
  disabled = false,
}) => {
  const [tenants, setTenants] = useState<TenantOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTenants = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(
          `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/tenant/list`
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setTenants(data);
      } catch (err: any) {
        const msg = err?.message || 'Error al cargar tenants';
        setError(msg);
        console.error('Tenant fetch error:', msg);
      } finally {
        setLoading(false);
      }
    };

    fetchTenants();
  }, []);

  const selectedTenant = tenants.find(t => t.tenant_id === selectedTenantId);

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-semibold text-gray-700">
        Seleccionar Tenant
      </label>

      {loading ? (
        <div className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-500">
          Cargando tenants…
        </div>
      ) : error ? (
        <div className="px-3 py-2 border border-red-300 rounded-lg text-sm text-red-600 bg-red-50">
          ⚠️ {error}
        </div>
      ) : tenants.length === 0 ? (
        <div className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-500">
          No hay tenants disponibles
        </div>
      ) : (
        <select
          disabled={disabled}
          value={selectedTenantId || ''}
          onChange={(e) => {
            const tenantId = e.target.value;
            const tenant = tenants.find(t => t.tenant_id === tenantId);
            if (tenant) {
              onSelectTenant(tenantId, tenant.tenant_name);
            }
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">-- Selecciona un tenant --</option>
          {tenants.map((tenant) => (
            <option key={tenant.tenant_id} value={tenant.tenant_id}>
              {tenant.tenant_name} ({tenant.domain_pattern})
            </option>
          ))}
        </select>
      )}

      {selectedTenant && (
        <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-gray-600">
            <span className="font-semibold">Actual:</span> {selectedTenant.tenant_name}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Dominio: <code className="bg-white px-1 rounded">{selectedTenant.domain_pattern}</code>
          </p>
          <div className="flex gap-2 mt-2">
            <div className="flex items-center gap-1">
              <div
                className="w-6 h-6 rounded border border-gray-300"
                style={{ backgroundColor: selectedTenant.primary_color }}
                title="Color primario"
              />
              <span className="text-xs text-gray-500">{selectedTenant.primary_color}</span>
            </div>
            <div className="flex items-center gap-1">
              <div
                className="w-6 h-6 rounded border border-gray-300"
                style={{ backgroundColor: selectedTenant.secondary_color }}
                title="Color secundario"
              />
              <span className="text-xs text-gray-500">{selectedTenant.secondary_color}</span>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-blue-100 flex justify-between items-center">
            <a
              href={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/themes/blueprint/download?brand_name=${encodeURIComponent(selectedTenant.tenant_name)}&domain=${encodeURIComponent(selectedTenant.domain_pattern)}`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-blue-600 hover:text-blue-800 font-bold underline flex items-center gap-1"
            >
              📥 Descargar Blueprint inicializador
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
