import React from 'react';
import { useTenant } from '../contexts/TenantContext';

export const TenantInfo: React.FC = () => {
  const { tenant, hostname } = useTenant();

  if (!tenant) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center gap-3">
        {/* Color indicator */}
        <div
          className="w-12 h-12 rounded-lg border-2 border-gray-200"
          style={{ backgroundColor: tenant.primary_color }}
          title={`Primary Color: ${tenant.primary_color}`}
        />

        {/* Tenant info */}
        <div className="flex-1">
          <h3 className="font-bold text-gray-800">{tenant.tenant_name}</h3>
          <p className="text-sm text-gray-500">{hostname}</p>
          <p className="text-xs text-gray-400 mt-1">ID: {tenant.tenant_id.slice(0, 8)}...</p>
        </div>

        {/* Secondary color indicator */}
        <div
          className="w-8 h-8 rounded-full border-2 border-gray-200"
          style={{ backgroundColor: tenant.secondary_color }}
          title={`Secondary Color: ${tenant.secondary_color}`}
        />
      </div>
    </div>
  );
};

export default TenantInfo;
