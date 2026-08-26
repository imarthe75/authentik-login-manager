import React, { useCallback, useEffect, useState } from 'react';
import { tenantApplicationsApi, TenantApplicationLink, AuthentikAppRef } from '../../api/tenantApplicationsApi';

interface ApplicationsTabProps {
  selectedTenantId: string | null;
}

/**
 * Enlace app<->tenant (tenant_applications) — reemplaza el filtro por
 * substring de nombre que list_authentik_applications tenía antes. Muestra
 * qué apps ya están enlazadas al tenant seleccionado (con su origen: auto
 * por convención de grupo, o manual) y qué apps de Authentik siguen sin
 * ningún tenant asignado, para confirmarlas a mano aquí.
 */
export const ApplicationsTab: React.FC<ApplicationsTabProps> = ({ selectedTenantId }) => {
  const [linked, setLinked] = useState<TenantApplicationLink[]>([]);
  const [unassigned, setUnassigned] = useState<AuthentikAppRef[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busySlug, setBusySlug] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedTenantId) {
      setLinked([]);
      setUnassigned([]);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await tenantApplicationsApi.list(selectedTenantId);
      setLinked(data.linked);
      setUnassigned(data.unassigned);
    } catch (err: any) {
      setError(err?.message || 'Error al cargar aplicaciones');
    } finally {
      setLoading(false);
    }
  }, [selectedTenantId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAssign = async (app: AuthentikAppRef) => {
    if (!selectedTenantId) return;
    try {
      setBusySlug(app.slug);
      await tenantApplicationsApi.link(selectedTenantId, app.slug, app.name);
      await load();
    } catch (err: any) {
      setError(err?.message || 'Error al asignar la aplicación');
    } finally {
      setBusySlug(null);
    }
  };

  const handleUnlink = async (link: TenantApplicationLink) => {
    try {
      setBusySlug(link.application_slug);
      await tenantApplicationsApi.unlink(link.id);
      await load();
    } catch (err: any) {
      setError(err?.message || 'Error al quitar la aplicación');
    } finally {
      setBusySlug(null);
    }
  };

  if (!selectedTenantId) {
    return (
      <p className="text-xxs text-gray-400 font-sans">Selecciona un tenant para ver sus aplicaciones.</p>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="px-3 py-2 border border-red-300 rounded-lg text-xs text-red-600 bg-red-50 font-sans">
          ⚠️ {error}
        </div>
      )}

      <div className="space-y-2">
        <span className="text-xxs font-bold text-gray-500 uppercase font-sans">Aplicaciones de este tenant</span>
        {loading ? (
          <p className="text-xxs text-gray-400 font-sans">Cargando…</p>
        ) : linked.length === 0 ? (
          <p className="text-xxs text-gray-400 font-sans">Sin aplicaciones enlazadas todavía.</p>
        ) : (
          <div className="space-y-1.5">
            {linked.map((link) => (
              <div key={link.id} className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-2.5 py-1.5">
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-gray-700 font-sans">{link.application_name || link.application_slug}</span>
                  <span className="text-[10px] text-gray-400 font-sans">
                    {link.application_slug} · {link.link_source === 'group_convention' ? 'auto (grupo)' : 'manual'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleUnlink(link)}
                  disabled={busySlug === link.application_slug}
                  className="text-[10px] font-semibold text-red-500 hover:underline font-sans disabled:opacity-50"
                >
                  Quitar
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {unassigned.length > 0 && (
        <div className="space-y-2">
          <span className="text-xxs font-bold text-amber-600 uppercase font-sans">
            Sin asignar a ningún tenant ({unassigned.length})
          </span>
          <p className="text-[10px] text-gray-400 font-sans leading-relaxed">
            No se detectó un grupo de convención para estas apps en Authentik — asígnalas a mano al tenant correcto.
          </p>
          <div className="space-y-1.5">
            {unassigned.map((app) => (
              <div key={app.slug} className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-gray-700 font-sans">{app.name}</span>
                  <span className="text-[10px] text-gray-400 font-sans">{app.slug}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleAssign(app)}
                  disabled={busySlug === app.slug}
                  className="text-[10px] font-semibold text-[#4272A5] hover:underline font-sans disabled:opacity-50"
                >
                  Asignar a este tenant
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
