import React, { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { adminFetch } from '../../api/adminFetch';
import { applyTenantAccent } from '../../contexts/TenantContext';
import { BrandPaletteSwatch } from '../TenantSelector';

interface TenantBrandingTabProps {
  tenantId: string;
}

interface TenantSettings {
  default_app_url: string | null;
  brand_palette: BrandPaletteSwatch[] | null;
  primary_color: string;
  secondary_color: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const EMPTY_SWATCH: BrandPaletteSwatch = { name: '', color: '#4272A5', hover: '#2d5580' };

/**
 * Identidad de marca a nivel TENANT (no del tema de login): color primario/
 * secundario (acento del propio Manager — ver applyTenantAccent) y la
 * paleta de swatches sugeridas en el selector rápido de color de
 * ConfigPanel ("Color del botón"). Antes de esto no existía ninguna UI
 * para editar estos dos datos — la paleta de TECA solo se pudo cargar
 * a mano directo en base de datos.
 */
export const TenantBrandingTab: React.FC<TenantBrandingTabProps> = ({ tenantId }) => {
  const [settings, setSettings] = useState<TenantSettings | null>(null);
  const [swatches, setSwatches] = useState<BrandPaletteSwatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await adminFetch(`${API_BASE}/api/v1/tenant/settings?tenant_id=${tenantId}`, {
        method: 'GET',
        credentials: 'include',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: TenantSettings = await response.json();
      setSettings(data);
      setSwatches(data.brand_palette || []);
    } catch (err: any) {
      setError(err?.message || 'Error al cargar la configuración del tenant');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaveColors = async (primary: string, secondary: string) => {
    try {
      setSaving(true);
      setError(null);
      const response = await adminFetch(`${API_BASE}/api/v1/tenant/settings?tenant_id=${tenantId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ primary_color: primary, secondary_color: secondary }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setSettings((prev) => (prev ? { ...prev, primary_color: data.primary_color, secondary_color: data.secondary_color } : prev));
      applyTenantAccent(data.primary_color, data.secondary_color);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (err: any) {
      setError(err?.message || 'Error al guardar los colores del tenant');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePalette = async (next: BrandPaletteSwatch[]) => {
    try {
      setSaving(true);
      setError(null);
      const cleaned = next.filter((s) => s.name.trim() !== '');
      const response = await adminFetch(`${API_BASE}/api/v1/tenant/settings?tenant_id=${tenantId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ brand_palette: cleaned.length > 0 ? cleaned : null }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setSwatches(data.brand_palette || []);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (err: any) {
      setError(err?.message || 'Error al guardar la paleta institucional');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return <p className="text-xxs text-gray-400 font-sans">Cargando…</p>;
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="px-3 py-2 border border-red-300 rounded-lg text-xs text-red-600 bg-red-50 font-sans">
          ⚠️ {error}
        </div>
      )}
      {saved && (
        <div className="px-3 py-2 border border-green-300 rounded-lg text-xs text-green-700 bg-green-50 font-sans">
          ✓ Guardado
        </div>
      )}

      {/* Color primario/secundario del tenant */}
      <div className="space-y-2">
        <span className="text-xxs font-bold text-gray-500 uppercase font-sans">
          Color primario / secundario del tenant
        </span>
        <p className="text-[10px] text-gray-400 font-sans leading-relaxed">
          Es el acento del propio Login Manager (header, botón principal) cuando editas este tenant — no el color del botón de la página de login (ese está en "Color del botón" más abajo).
        </p>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={settings.primary_color}
              onChange={(e) => {
                setSettings((prev) => (prev ? { ...prev, primary_color: e.target.value } : prev));
              }}
              onBlur={(e) => handleSaveColors(e.target.value, settings.secondary_color)}
              className="w-9 h-7 border border-gray-300 rounded-lg cursor-pointer p-0.5"
            />
            <span className="text-[10px] text-gray-500 font-mono">{settings.primary_color}</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={settings.secondary_color}
              onChange={(e) => {
                setSettings((prev) => (prev ? { ...prev, secondary_color: e.target.value } : prev));
              }}
              onBlur={(e) => handleSaveColors(settings.primary_color, e.target.value)}
              className="w-9 h-7 border border-gray-300 rounded-lg cursor-pointer p-0.5"
            />
            <span className="text-[10px] text-gray-500 font-mono">{settings.secondary_color}</span>
          </div>
          {saving && <span className="text-[10px] text-gray-400 font-sans">Guardando…</span>}
        </div>
      </div>

      {/* Paleta institucional (swatches del selector rápido) */}
      <div className="space-y-2">
        <span className="text-xxs font-bold text-gray-500 uppercase font-sans">
          Paleta institucional (swatches sugeridas)
        </span>
        <p className="text-[10px] text-gray-400 font-sans leading-relaxed">
          Aparecen como atajos en "Color del botón 'Iniciar sesión'" al editar el tema. Si se deja vacío, se usa la paleta genérica Civika.
        </p>

        <div className="space-y-1.5">
          {swatches.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2 py-1.5">
              <input
                type="text"
                value={s.name}
                onChange={(e) => {
                  const next = [...swatches];
                  next[i] = { ...next[i], name: e.target.value };
                  setSwatches(next);
                }}
                placeholder="Nombre (ej. Guinda Edoméx)"
                className="flex-1 h-6 border border-gray-300 rounded px-1.5 text-[10px] font-sans focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <input
                type="color"
                value={s.color}
                onChange={(e) => {
                  const next = [...swatches];
                  next[i] = { ...next[i], color: e.target.value };
                  setSwatches(next);
                }}
                title="Color"
                className="w-7 h-6 border border-gray-300 rounded cursor-pointer p-0"
              />
              <input
                type="color"
                value={s.hover}
                onChange={(e) => {
                  const next = [...swatches];
                  next[i] = { ...next[i], hover: e.target.value };
                  setSwatches(next);
                }}
                title="Hover"
                className="w-7 h-6 border border-gray-300 rounded cursor-pointer p-0"
              />
              <button
                type="button"
                onClick={() => setSwatches(swatches.filter((_, idx) => idx !== i))}
                className="text-[10px] font-semibold text-red-500 hover:underline font-sans shrink-0"
              >
                Quitar
              </button>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => setSwatches([...swatches, { ...EMPTY_SWATCH }])}
            className="text-[10px] font-semibold text-[#4272A5] hover:underline font-sans flex items-center gap-1"
          >
            <Plus size={11} /> Agregar swatch
          </button>
          <button
            type="button"
            onClick={() => handleSavePalette(swatches)}
            disabled={saving}
            className="text-[10px] font-bold text-white tenant-accent-bg px-3 py-1.5 rounded-lg disabled:opacity-50"
          >
            Guardar paleta
          </button>
        </div>
      </div>
    </div>
  );
};
