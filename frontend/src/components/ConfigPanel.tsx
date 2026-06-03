import React, { useRef } from 'react';
import { Upload, RotateCcw, Save, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { Theme, EmailBody } from '../types/theme';
import { SavePhase } from '../hooks/useTheme';
import { AccessAndNotificationsTab } from './tabs/AccessAndNotificationsTab';

interface ConfigPanelProps {
  theme: Theme;
  isDirty: boolean;
  savePhase: SavePhase;
  deployError: string | null;
  onUpdateField: <K extends keyof Theme>(key: K, value: Theme[K]) => void;
  onUploadFile: (key: 'logo_top_base64' | 'logo_bottom_base64' | 'bg_image_base64', file: File) => void;
  onSave: () => void;
  onRetryDeploy: () => void;
  authentikApps: { slug: string; name: string }[];
  onChangeApp: (appSlug: string | null) => void;
  onUpdateEmailBody: (eventType: string, body: EmailBody) => void;
}

const PREDEFINED_COLORS = [
  { name: 'Civika', color: '#4272A5', hover: '#2d5580' },
  { name: 'Marino', color: '#1a3a6b', hover: '#254f94' },
  { name: 'Azul', color: '#1976d2', hover: '#2196f3' },
  { name: 'Verde', color: '#2e7d32', hover: '#43a047' },
  { name: 'Morado', color: '#5e35b1', hover: '#7c4dff' },
  { name: 'Gris', color: '#424242', hover: '#616161' },
];

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  theme,
  isDirty,
  savePhase,
  deployError,
  onUpdateField,
  onUploadFile,
  onSave,
  onRetryDeploy,
  authentikApps,
  onChangeApp,
  onUpdateEmailBody,
}) => {
  const logoTopRef = useRef<HTMLInputElement>(null);
  const logoBottomRef = useRef<HTMLInputElement>(null);
  const bgImgRef = useRef<HTMLInputElement>(null);
  const pdfRef = useRef<HTMLInputElement>(null);

  const isBusy = savePhase === 'saving' || savePhase === 'deploying';

  const handleFileChange = (
    key: 'logo_top_base64' | 'logo_bottom_base64' | 'bg_image_base64',
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        alert("El tamaño máximo permitido para archivos es de 5MB.");
        return;
      }
      onUploadFile(key, file);
    }
  };

  const handlePdfChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        alert("El archivo debe ser un formato PDF válido.");
        return;
      }
      if (file.size > 8 * 1024 * 1024) {
        alert("El tamaño máximo permitido para el PDF es de 8MB.");
        return;
      }
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        onUpdateField('privacy_pdf_url', reader.result as string);
      };
      reader.onerror = () => {
        alert("Error al cargar el archivo de privacidad PDF.");
      };
    }
  };

  const renderSaveButton = () => {
    if (savePhase === 'saving') {
      return (
        <button disabled className="w-full py-3.5 text-xs font-bold tracking-widest text-white rounded-xl shadow-lg flex items-center justify-center gap-2 uppercase font-sans bg-gray-500 cursor-not-allowed">
          <Save className="w-4 h-4 animate-pulse" />
          💾 Guardando tema...
        </button>
      );
    }
    if (savePhase === 'deploying') {
      return (
        <button disabled className="w-full py-3.5 text-xs font-bold tracking-widest text-white rounded-xl shadow-lg flex items-center justify-center gap-2 uppercase font-sans bg-blue-600 cursor-not-allowed">
          <RefreshCw className="w-4 h-4 animate-spin" />
          🚀 Desplegando en Authentik...
        </button>
      );
    }
    if (savePhase === 'done') {
      return (
        <button disabled className="w-full py-3.5 text-xs font-bold tracking-widest text-white rounded-xl shadow-lg flex items-center justify-center gap-2 uppercase font-sans bg-green-600 cursor-not-allowed">
          <CheckCircle className="w-4 h-4" />
          ✅ Aplicado en Authentik
        </button>
      );
    }
    if (savePhase === 'deploy_error') {
      return (
        <div className="flex flex-col gap-2">
          <div className="w-full px-3 py-2.5 text-[10px] font-semibold text-yellow-800 bg-yellow-100 border border-yellow-300 rounded-xl flex items-start gap-2 font-sans">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-yellow-600" />
            <span>⚠️ Tema guardado pero no desplegado — revisa el volumen compartido.<br />
              <span className="font-normal opacity-80">{deployError}</span>
            </span>
          </div>
          <button
            onClick={onRetryDeploy}
            className="w-full py-2.5 text-xs font-bold tracking-widest text-white rounded-xl flex items-center justify-center gap-2 uppercase font-sans bg-orange-600 hover:bg-orange-700 cursor-pointer transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reintentar despliegue
          </button>
        </div>
      );
    }
    // idle state
    return (
      <button
        onClick={onSave}
        disabled={!isDirty}
        className={`w-full py-3.5 text-xs font-bold tracking-widest text-white rounded-xl shadow-lg flex items-center justify-center gap-2 select-none uppercase transition-all font-sans ${
          !isDirty ? 'bg-gray-400 cursor-not-allowed shadow-none' : 'bg-[#4272A5] hover:bg-[#2d5580] cursor-pointer'
        }`}
      >
        <Save className="w-4 h-4" />
        💾 Guardar y Aplicar
      </button>
    );
  };

  return (
    <div className="w-full h-full bg-[#f7f4f0] border-l-2 border-gray-200 flex flex-col overflow-hidden select-none">
      {/* Panel Header */}
      <div className="bg-[#4272A5] text-white px-5 py-4 font-bold text-sm tracking-wide shrink-0 shadow-sm flex items-center justify-between font-sans">
        <span>⚙ PANEL DE CONFIGURACIÓN</span>
        <div className="flex items-center gap-1">
          {isDirty ? (
            <span className="flex items-center gap-1 text-xs text-yellow-300 font-medium">
              <AlertCircle className="w-3.5 h-3.5" />
              Modificado
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-green-300 font-medium">
              <CheckCircle className="w-3.5 h-3.5" />
              Guardado
            </span>
          )}
        </div>
      </div>

      {/* Settings Sections */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-5 space-y-6">

        {/* 0. APPLICATION MAPPING */}
        <div className="border-b border-gray-200 pb-5">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase mb-3 font-sans">
            📱 Aplicación de Destino
          </h3>
          <label className="block text-[11px] font-semibold text-gray-600 mb-2 font-sans leading-relaxed">
            Asocia este diseño de login a una aplicación de Authentik
          </label>
          <select
            value={theme.authentik_app_slug || ''}
            onChange={(e) => onChangeApp(e.target.value || null)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:outline-none focus:border-[#4272A5] font-sans text-gray-700 shadow-sm"
          >
            <option value="">-- Sin vinculación (Diseño Global / Por Defecto) --</option>
            {authentikApps.map((app) => (
              <option key={app.slug} value={app.slug}>
                {app.name} ({app.slug})
              </option>
            ))}
          </select>
          <p className="text-[10px] text-gray-400 mt-2 font-sans leading-relaxed">
            Al seleccionar una aplicación, este diseño visual se inyectará de forma aislada e independiente solo cuando los usuarios ingresen a ella.
          </p>
        </div>

        {/* 1. LAYOUT POSITION */}
        <div className="border-b border-gray-200 pb-5">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase mb-3.5 font-sans">
            📐 Distribución del layout
          </h3>
          <label className="block text-xs font-semibold text-gray-600 mb-2 font-sans">
            Posición del formulario y logotipos
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['left', 'center', 'right'] as const).map((pos) => (
              <button
                key={pos}
                type="button"
                onClick={() => onUpdateField('layout_position', pos)}
                className={`py-2 px-1 border-2 rounded-xl text-[10px] font-bold text-gray-500 hover:border-[#4272A5] hover:text-[#4272A5] flex flex-col items-center gap-2 transition-all font-sans bg-white ${
                  theme.layout_position === pos ? 'border-[#4272A5] bg-[#4272A5]/5 text-[#4272A5]' : 'border-gray-200'
                }`}
              >
                <div
                  className={`w-11 h-7 border rounded flex items-center p-0.5 gap-0.5 ${
                    theme.layout_position === pos ? 'border-[#4272A5]' : 'border-gray-300'
                  }`}
                  style={{
                    flexDirection: pos === 'right' ? 'row-reverse' : 'row',
                    justifyContent: pos === 'center' ? 'center' : 'flex-start',
                  }}
                >
                  <div className="w-3.5 h-full bg-current rounded-sm shrink-0 opacity-90" />
                  <div className="flex-1 h-full border border-current rounded-sm opacity-50 shrink-0" />
                </div>
                {pos === 'left' ? 'Izquierda' : pos === 'right' ? 'Derecha' : 'Centro'}
              </button>
            ))}
          </div>
        </div>

        {/* 2. TEXTS & ALIGNMENTS */}
        <div className="border-b border-gray-200 pb-5 space-y-4">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase font-sans">
            📝 Textos del sistema
          </h3>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 space-y-3 shadow-sm">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5 font-sans">
                Nombre del sistema (Acepta HTML básico: &lt;br&gt;)
              </label>
              <input
                type="text"
                value={theme.system_name}
                onChange={(e) => onUpdateField('system_name', e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-[#fcfbf9] focus:outline-none focus:border-[#4272A5] font-sans"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-gray-400 mb-1 font-sans">Alineación</label>
              <div className="grid grid-cols-3 gap-1">
                {(['left', 'center', 'right'] as const).map((align) => (
                  <button
                    key={align}
                    type="button"
                    onClick={() => onUpdateField('name_align', align)}
                    className={`py-1 border rounded-lg text-[10px] font-bold text-gray-500 hover:border-[#4272A5] hover:text-[#4272A5] font-sans ${
                      theme.name_align === align ? 'border-[#4272A5] bg-[#4272A5]/5 text-[#4272A5]' : 'border-gray-200 bg-white'
                    }`}
                  >
                    {align === 'left' ? 'Izq' : align === 'right' ? 'Der' : 'Cen'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 space-y-3 shadow-sm">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5 font-sans">Subtítulo</label>
              <input
                type="text"
                value={theme.system_subtitle}
                onChange={(e) => onUpdateField('system_subtitle', e.target.value)}
                className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-[#fcfbf9] focus:outline-none focus:border-[#4272A5] font-sans"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-gray-400 mb-1 font-sans">Alineación</label>
              <div className="grid grid-cols-3 gap-1">
                {(['left', 'center', 'right'] as const).map((align) => (
                  <button
                    key={align}
                    type="button"
                    onClick={() => onUpdateField('subtitle_align', align)}
                    className={`py-1 border rounded-lg text-[10px] font-bold text-gray-500 hover:border-[#4272A5] hover:text-[#4272A5] font-sans ${
                      theme.subtitle_align === align ? 'border-[#4272A5] bg-[#4272A5]/5 text-[#4272A5]' : 'border-gray-200 bg-white'
                    }`}
                  >
                    {align === 'left' ? 'Izq' : align === 'right' ? 'Der' : 'Cen'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 3. LOGO CONTROL (TOP) */}
        <div className="border-b border-gray-200 pb-5">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase mb-3 font-sans">
            🖼 Logotipo superior
          </h3>
          {/* Mode toggle */}
          <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-lg mb-3 w-fit">
            {(['imagen', 'texto', 'ninguno'] as const).map((mode) => {
              const active = mode === 'imagen' ? !!theme.logo_top_base64 : mode === 'texto' ? (!theme.logo_top_base64 && !!theme.logo_top_text) : (!theme.logo_top_base64 && !theme.logo_top_text);
              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => {
                    if (mode === 'imagen') { /* handled by file input */ logoTopRef.current?.click(); }
                    else if (mode === 'texto') { onUpdateField('logo_top_base64', null); if (!theme.logo_top_text) onUpdateField('logo_top_text', ''); }
                    else { onUpdateField('logo_top_base64', null); onUpdateField('logo_top_text', null); }
                  }}
                  className={`px-3 py-1 rounded-md text-[10px] font-bold capitalize transition-all font-sans ${active ? 'bg-[#4272A5] text-white shadow-sm' : 'text-gray-500 hover:text-gray-800'}`}
                >
                  {mode === 'imagen' ? '🖼 Imagen' : mode === 'texto' ? '✏️ Texto' : '✕ Ninguno'}
                </button>
              );
            })}
          </div>
          <div className="flex flex-col gap-3">
            {/* Image mode */}
            {(theme.logo_top_base64 !== null || !theme.logo_top_text) && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => logoTopRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2 border border-[#4272A5] rounded-lg text-xs font-semibold text-[#4272A5] hover:bg-[#4272A5]/5 cursor-pointer font-sans bg-white"
                >
                  <Upload className="w-3.5 h-3.5" />
                  Subir Imagen
                </button>
                <input
                  ref={logoTopRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange('logo_top_base64', e)}
                  className="hidden"
                />
                {theme.logo_top_base64 && (
                  <button
                    type="button"
                    onClick={() => onUpdateField('logo_top_base64', null)}
                    className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 font-sans bg-white"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Quitar
                  </button>
                )}
              </div>
            )}
            {theme.logo_top_base64 ? (
              <div className="h-16 w-full border border-dashed border-gray-300 rounded-lg overflow-hidden bg-white p-1 flex items-center justify-center">
                <img src={theme.logo_top_base64} alt="Preview top" className="max-h-full object-contain" />
              </div>
            ) : theme.logo_top_text !== null && (
              /* Text mode */
              <div className="flex flex-col gap-1.5">
                <textarea
                  value={theme.logo_top_text || ''}
                  onChange={(e) => onUpdateField('logo_top_text', e.target.value || null)}
                  placeholder="Texto del logo superior (acepta <br>)"
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-sans resize-none focus:outline-none focus:border-[#4272A5]"
                />
                <p className="text-[9px] text-gray-400 font-sans">Acepta HTML básico: &lt;br&gt;, &lt;b&gt;, &lt;span&gt;</p>
              </div>
            )}
          </div>
        </div>

        {/* 4. LOGO CONTROL (BOTTOM) */}
        <div className="border-b border-gray-200 pb-5">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase mb-3 font-sans">
            🖼 Logotipo inferior
          </h3>
          {/* Mode toggle */}
          <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-lg mb-3 w-fit">
            {(['imagen', 'texto', 'ninguno'] as const).map((mode) => {
              const active = mode === 'imagen' ? !!theme.logo_bottom_base64 : mode === 'texto' ? (!theme.logo_bottom_base64 && !!theme.logo_bottom_text) : (!theme.logo_bottom_base64 && !theme.logo_bottom_text);
              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => {
                    if (mode === 'imagen') { logoBottomRef.current?.click(); }
                    else if (mode === 'texto') { onUpdateField('logo_bottom_base64', null); if (!theme.logo_bottom_text) onUpdateField('logo_bottom_text', ''); }
                    else { onUpdateField('logo_bottom_base64', null); onUpdateField('logo_bottom_text', null); }
                  }}
                  className={`px-3 py-1 rounded-md text-[10px] font-bold capitalize transition-all font-sans ${active ? 'bg-[#4272A5] text-white shadow-sm' : 'text-gray-500 hover:text-gray-800'}`}
                >
                  {mode === 'imagen' ? '🖼 Imagen' : mode === 'texto' ? '✏️ Texto' : '✕ Ninguno'}
                </button>
              );
            })}
          </div>
          <div className="flex flex-col gap-3">
            {(theme.logo_bottom_base64 !== null || !theme.logo_bottom_text) && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => logoBottomRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2 border border-[#4272A5] rounded-lg text-xs font-semibold text-[#4272A5] hover:bg-[#4272A5]/5 cursor-pointer font-sans bg-white"
                >
                  <Upload className="w-3.5 h-3.5" />
                  Subir Imagen
                </button>
                <input
                  ref={logoBottomRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange('logo_bottom_base64', e)}
                  className="hidden"
                />
                {theme.logo_bottom_base64 && (
                  <button
                    type="button"
                    onClick={() => onUpdateField('logo_bottom_base64', null)}
                    className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 font-sans bg-white"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Quitar
                  </button>
                )}
              </div>
            )}
            {theme.logo_bottom_base64 ? (
              <div className="h-16 w-full border border-dashed border-gray-300 rounded-lg overflow-hidden bg-white p-1 flex items-center justify-center">
                <img src={theme.logo_bottom_base64} alt="Preview bottom" className="max-h-full object-contain" />
              </div>
            ) : theme.logo_bottom_text !== null && (
              <div className="flex flex-col gap-1.5">
                <textarea
                  value={theme.logo_bottom_text || ''}
                  onChange={(e) => onUpdateField('logo_bottom_text', e.target.value || null)}
                  placeholder="Texto del logo inferior (acepta <br>)"
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-sans resize-none focus:outline-none focus:border-[#4272A5]"
                />
                <p className="text-[9px] text-gray-400 font-sans">Acepta HTML básico: &lt;br&gt;, &lt;b&gt;, &lt;span&gt;</p>
              </div>
            )}
          </div>
        </div>

        {/* 5. BACKGROUND CHANGER */}
        <div className="border-b border-gray-200 pb-5 space-y-4">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase font-sans">
            🌆 Fondo de pantalla
          </h3>

          <div className="flex items-center gap-2 bg-white p-1 border border-gray-200 rounded-lg shadow-sm shrink-0">
            {(['gradient', 'color', 'image'] as const).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => onUpdateField('bg_type', type)}
                className={`flex-1 py-1.5 rounded-md text-[10px] font-bold uppercase transition-all font-sans ${
                  theme.bg_type === type ? 'bg-[#4272A5] text-white' : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                {type === 'gradient' ? 'Gradiente' : type === 'color' ? 'Plano' : 'Imagen'}
              </button>
            ))}
          </div>

          {theme.bg_type === 'gradient' && (
            <div className="grid grid-cols-2 gap-3 bg-white p-3 border border-gray-200 rounded-xl">
              <div>
                <label className="block text-xxs font-semibold text-gray-400 mb-1 font-sans">Color Inicio</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={theme.bg_gradient_from}
                    onChange={(e) => onUpdateField('bg_gradient_from', e.target.value)}
                    className="w-10 h-8 border border-gray-300 rounded-lg cursor-pointer p-0.5"
                  />
                  <span className="text-[10px] text-gray-500 uppercase font-mono font-bold">{theme.bg_gradient_from}</span>
                </div>
              </div>
              <div>
                <label className="block text-xxs font-semibold text-gray-400 mb-1 font-sans">Color Fin</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={theme.bg_gradient_to}
                    onChange={(e) => onUpdateField('bg_gradient_to', e.target.value)}
                    className="w-10 h-8 border border-gray-300 rounded-lg cursor-pointer p-0.5"
                  />
                  <span className="text-[10px] text-gray-500 uppercase font-mono font-bold">{theme.bg_gradient_to}</span>
                </div>
              </div>
            </div>
          )}

          {theme.bg_type === 'color' && (
            <div className="bg-white p-3 border border-gray-200 rounded-xl">
              <label className="block text-xxs font-semibold text-gray-400 mb-1 font-sans">Color plano de fondo</label>
              <div className="flex items-center gap-2.5">
                <input
                  type="color"
                  value={theme.bg_flat_color || '#b0aba0'}
                  onChange={(e) => onUpdateField('bg_flat_color', e.target.value)}
                  className="w-10 h-8 border border-gray-300 rounded-lg cursor-pointer p-0.5"
                />
                <span className="text-xs text-gray-500 uppercase font-mono font-bold">{theme.bg_flat_color || '#b0aba0'}</span>
              </div>
            </div>
          )}

          {theme.bg_type === 'image' && (
            <div className="flex flex-col gap-3 bg-white p-3 border border-gray-200 rounded-xl">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => bgImgRef.current?.click()}
                  className="flex items-center gap-2 px-3 py-1.5 border border-[#4272A5] rounded-lg text-[10px] font-semibold text-[#4272A5] hover:bg-[#4272A5]/5 cursor-pointer font-sans bg-white"
                >
                  <Upload className="w-3 h-3" />
                  Elegir Imagen
                </button>
                <input
                  ref={bgImgRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange('bg_image_base64', e)}
                  className="hidden"
                />
              </div>
              {theme.bg_image_base64 ? (
                <div className="h-16 w-full border border-dashed border-gray-300 rounded-lg overflow-hidden bg-gray-50 p-1 flex items-center justify-center">
                  <img src={theme.bg_image_base64} alt="Fondo" className="max-h-full object-contain" />
                </div>
              ) : (
                <p className="text-xxs text-gray-400 font-sans">Sin imagen cargada. Suba una imagen de fondo.</p>
              )}
            </div>
          )}

          <div>
            <div className="flex justify-between items-center text-xs font-semibold text-gray-600 mb-1.5 font-sans">
              <span>Opacidad de fondo</span>
              <span>{Math.round(theme.bg_opacity * 100)}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              value={theme.bg_opacity * 100}
              onChange={(e) => onUpdateField('bg_opacity', parseFloat(e.target.value) / 100)}
              className="w-full accent-[#4272A5] cursor-pointer"
            />
          </div>
        </div>

        {/* 6. BUTTON COLOR PALETTE */}
        <div className="border-b border-gray-200 pb-5 space-y-4">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase font-sans">
            🎨 Color del botón "Iniciar sesión"
          </h3>

          <div className="flex flex-wrap gap-2">
            {PREDEFINED_COLORS.map((c) => (
              <button
                key={c.color}
                type="button"
                onClick={() => {
                  onUpdateField('primary_color', c.color);
                  onUpdateField('hover_color', c.hover);
                }}
                className={`w-9 h-9 rounded-full shadow-sm cursor-pointer border-2 transition-all flex items-center justify-center text-white font-bold text-xs ${
                  theme.primary_color === c.color ? 'border-gray-900 scale-110 shadow-md' : 'border-transparent'
                }`}
                style={{ backgroundColor: c.color }}
                title={c.name}
              >
                {theme.primary_color === c.color && '✓'}
              </button>
            ))}
          </div>

          <div className="bg-white p-3 border border-gray-200 rounded-xl flex items-center justify-between shadow-sm">
            <span className="text-xxs font-semibold text-gray-400 font-sans">Color Personalizado</span>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={theme.primary_color}
                onChange={(e) => {
                  onUpdateField('primary_color', e.target.value);
                  onUpdateField('hover_color', e.target.value + 'cc');
                }}
                className="w-9 h-7 border border-gray-300 rounded-lg cursor-pointer p-0.5"
              />
              <span className="text-xs text-gray-500 uppercase font-mono font-bold">{theme.primary_color}</span>
            </div>
          </div>
        </div>

        {/* 7. FORM & LOGOS CONTAINERS OPACITY / HEIGHT */}
        <div className="border-b border-gray-200 pb-5 space-y-4">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase font-sans">
            🪟 Contenedores
          </h3>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 space-y-4 shadow-sm">
            <div>
              <div className="flex justify-between items-center text-[10px] font-semibold text-gray-500 mb-1 font-sans">
                <span>Opacidad del formulario</span>
                <span>{Math.round(theme.form_opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={theme.form_opacity * 100}
                onChange={(e) => onUpdateField('form_opacity', parseFloat(e.target.value) / 100)}
                className="w-full accent-[#4272A5] cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between items-center text-[10px] font-semibold text-gray-500 mb-1 font-sans">
                <span>Altura del formulario</span>
                <span>{theme.form_height_pct ? `${theme.form_height_pct}%` : 'Auto'}</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={theme.form_height_pct || 0}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  onUpdateField('form_height_pct', val === 0 ? null : val);
                }}
                className="w-full accent-[#4272A5] cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between border-t border-dashed border-gray-200 pt-3.5">
              <span className="text-[10px] font-semibold text-gray-500 font-sans">Color de fondo</span>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={theme.card_bg_color || '#FFFFFF'}
                  onChange={(e) => onUpdateField('card_bg_color', e.target.value)}
                  className="w-8 h-6 border border-gray-300 rounded cursor-pointer p-0.5"
                />
                <span className="text-[9px] text-gray-500 uppercase font-mono font-bold">{theme.card_bg_color || '#FFFFFF'}</span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 space-y-4 shadow-sm">
            <div>
              <div className="flex justify-between items-center text-[10px] font-semibold text-gray-500 mb-1 font-sans">
                <span>Opacidad del panel de logos</span>
                <span>{Math.round(theme.logos_opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={theme.logos_opacity * 100}
                onChange={(e) => onUpdateField('logos_opacity', parseFloat(e.target.value) / 100)}
                className="w-full accent-[#4272A5] cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between items-center text-[10px] font-semibold text-gray-500 mb-1 font-sans">
                <span>Altura del panel de logos</span>
                <span>{theme.logos_height_pct ? `${theme.logos_height_pct}%` : 'Auto'}</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={theme.logos_height_pct || 0}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  onUpdateField('logos_height_pct', val === 0 ? null : val);
                }}
                className="w-full accent-[#4272A5] cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between border-t border-dashed border-gray-200 pt-3.5">
              <span className="text-[10px] font-semibold text-gray-500 font-sans">Color de fondo</span>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={theme.panel_bg_color || '#F6F9FD'}
                  onChange={(e) => onUpdateField('panel_bg_color', e.target.value)}
                  className="w-8 h-6 border border-gray-300 rounded cursor-pointer p-0.5"
                />
                <span className="text-[9px] text-gray-500 uppercase font-mono font-bold">{theme.panel_bg_color || '#F6F9FD'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 8. PRIVACY MODAL PDF */}
        <div>
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase mb-3 font-sans">
            📄 Aviso de Privacidad (PDF)
          </h3>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 space-y-3.5 shadow-sm text-left">
            <div>
              <label className="block text-xxs font-semibold text-gray-400 mb-1 font-sans">Enlace de Aviso PDF (URL externa)</label>
              <input
                type="text"
                placeholder="Ej. https://servicios.edomex.gob.mx/aviso.pdf"
                value={theme.privacy_pdf_url || ''}
                onChange={(e) => onUpdateField('privacy_pdf_url', e.target.value)}
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-[#fcfbf9] focus:outline-none focus:border-[#4272A5] font-sans"
              />
            </div>

            <div className="border-t border-dashed border-gray-200 pt-3">
              <label className="block text-xxs font-semibold text-gray-400 mb-1 font-sans">O suba un archivo PDF</label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => pdfRef.current?.click()}
                  className="flex items-center gap-2 px-3 py-1.5 border border-[#4272A5] rounded-lg text-[10px] font-semibold text-[#4272A5] hover:bg-[#4272A5]/5 cursor-pointer font-sans bg-white"
                >
                  <Upload className="w-3.5 h-3.5" />
                  Cargar PDF
                </button>
                <input
                  ref={pdfRef}
                  type="file"
                  accept="application/pdf"
                  onChange={handlePdfChange}
                  className="hidden"
                />
              </div>
              <p className="text-[10px] text-gray-400 mt-1 font-sans">
                {theme.privacy_pdf_url?.startsWith('data:') ? '✅ PDF subido correctamente a base de datos.' : 'No se ha subido ningún archivo local.'}
              </p>
            </div>

            <div>
              <label className="block text-xxs font-semibold text-gray-400 mb-1 font-sans">Alineación del enlace</label>
              <div className="grid grid-cols-3 gap-1">
                {(['left', 'center', 'right'] as const).map((align) => (
                  <button
                    key={align}
                    type="button"
                    onClick={() => onUpdateField('privacy_align', align)}
                    className={`py-1 border rounded-lg text-[10px] font-bold text-gray-500 hover:border-[#4272A5] hover:text-[#4272A5] font-sans ${
                      theme.privacy_align === align ? 'border-[#4272A5] bg-[#4272A5]/5 text-[#4272A5]' : 'border-gray-200 bg-white'
                    }`}
                  >
                    {align === 'left' ? 'Izq' : align === 'right' ? 'Der' : 'Cen'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 8. ACCESS & NOTIFICATIONS */}
        <div className="border-b border-gray-200 pb-5">
          <h3 className="text-xs font-bold text-[#4272A5] tracking-wider uppercase mb-3 font-sans">
            🔔 Accesos y Notificaciones
          </h3>
          <AccessAndNotificationsTab
            theme={theme}
            onUpdateField={onUpdateField}
            onUpdateEmailBody={onUpdateEmailBody}
          />
        </div>

      </div>

      {/* Save Button Drawer Footer */}
      <div className="p-4 bg-white border-t border-gray-200 shrink-0">
        {renderSaveButton()}
      </div>
    </div>
  );
};
