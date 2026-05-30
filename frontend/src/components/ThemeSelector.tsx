import React, { useState } from 'react';
import { Plus, Check, ChevronDown } from 'lucide-react';
import { Theme } from '../types/theme';

interface ThemeSelectorProps {
  themes: Theme[];
  currentSlug: string;
  onSelectSlug: (slug: string) => void;
  onCreateTheme: (displayName: string, flowSlug: string) => void;
}

export const ThemeSelector: React.FC<ThemeSelectorProps> = ({
  themes,
  currentSlug,
  onSelectSlug,
  onCreateTheme
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [newDisplayName, setNewDisplayName] = useState('');
  const [newFlowSlug, setNewFlowSlug] = useState('');
  const [slugError, setSlugError] = useState('');

  const currentTheme = themes.find((t) => t.authentik_flow_slug === currentSlug) || {
    display_name: currentSlug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    authentik_flow_slug: currentSlug
  };

  const handleSlugChange = (val: string) => {
    // Format to strictly lower alphanumeric and hyphens
    const formatted = val
      .toLowerCase()
      .replace(/[^a-z0-9\-]/g, '-')
      .replace(/-+/g, '-');
    setNewFlowSlug(formatted);
    if (!formatted) {
      setSlugError('El identificador del flujo es obligatorio.');
    } else {
      setSlugError('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDisplayName.trim()) return;
    if (!newFlowSlug.trim()) {
      setSlugError('El identificador del flujo es obligatorio.');
      return;
    }
    onCreateTheme(newDisplayName.trim(), newFlowSlug.trim());
    setNewDisplayName('');
    setNewFlowSlug('');
    setShowModal(false);
  };

  return (
    <div className="relative flex items-center gap-4">
      {/* Selector Dropdown */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-between gap-3 px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm hover:border-[#8B3A2A] focus:outline-none min-w-[260px] text-gray-800 font-medium text-sm transition-all"
        >
          <div className="flex flex-col items-start text-left">
            <span className="text-xs text-gray-400 font-normal">Portal Activo</span>
            <span>{currentTheme.display_name}</span>
          </div>
          <ChevronDown className="w-4 h-4 text-gray-500" />
        </button>

        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)}></div>
            <div className="absolute left-0 mt-2 w-72 bg-white border border-gray-200 rounded-xl shadow-xl z-20 overflow-hidden animate-fadeIn">
              <div className="max-h-64 overflow-y-auto py-1">
                {themes.map((t) => (
                  <button
                    key={t.authentik_flow_slug}
                    onClick={() => {
                      onSelectSlug(t.authentik_flow_slug);
                      setIsOpen(false);
                    }}
                    className={`flex items-center justify-between w-full px-4 py-3 text-left text-sm hover:bg-gray-50 transition-colors ${
                      t.authentik_flow_slug === currentSlug ? 'text-[#8B3A2A] font-semibold bg-red-50/30' : 'text-gray-700'
                    }`}
                  >
                    <div className="flex flex-col">
                      <span>{t.display_name}</span>
                      <span className="text-xs text-gray-400 font-normal">{t.authentik_flow_slug}</span>
                    </div>
                    {t.authentik_flow_slug === currentSlug && <Check className="w-4 h-4 text-[#8B3A2A]" />}
                  </button>
                ))}
              </div>
              <div className="border-t border-gray-100 p-2">
                <button
                  onClick={() => {
                    setShowModal(true);
                    setIsOpen(false);
                  }}
                  className="flex items-center justify-center gap-2 w-full py-2 bg-[#8B3A2A] text-white text-xs font-semibold rounded-lg hover:bg-[#a04535] transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Agregar Nuevo Portal
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Creation Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl p-6 overflow-hidden animate-scaleUp">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Crear Portal / Flow</h3>
            <p className="text-xs text-gray-500 mb-5">
              Configura un nuevo portal visual asignándole un nombre descriptivo y enlazándolo al identificador (Slug) de tu flujo en Authentik.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Nombre Amigable del Portal</label>
                <input
                  type="text"
                  required
                  placeholder="Ej. Transparencia Edomex"
                  value={newDisplayName}
                  onChange={(e) => setNewDisplayName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-[#8B3A2A] placeholder-gray-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Slug del Flujo (authentik_flow_slug)</label>
                <input
                  type="text"
                  required
                  placeholder="Ej. flow-transparencia"
                  value={newFlowSlug}
                  onChange={(e) => handleSlugChange(e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none placeholder-gray-400 ${
                    slugError ? 'border-red-500 focus:border-red-500' : 'border-gray-300 focus:border-[#8B3A2A]'
                  }`}
                />
                {slugError && <p className="text-red-500 text-xxs mt-1 font-semibold">{slugError}</p>}
                <p className="text-gray-400 text-[10px] mt-1 italic">
                  Este valor debe coincidir con el identificador exacto de tu flujo en Authentik.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-600 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#8B3A2A] text-white rounded-lg text-xs font-semibold hover:bg-[#a04535]"
                >
                  Crear Portal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
