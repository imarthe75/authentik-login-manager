import React, { useState } from 'react';
import { AuthentikExpansionConfig } from '../types/models';

/**
 * Propiedades del componente ExpansionSettingsManager.
 */
interface ExpansionSettingsManagerProps {
  /** Configuración inicial para poblar el estado del formulario. */
  initialConfig?: AuthentikExpansionConfig;
  /** Callback opcional invocado al guardar la configuración modificada. */
  onSaveConfig?: (config: AuthentikExpansionConfig) => void;
}

/**
 * Configuración predeterminada (fallback) utilizada cuando no se proporciona
 * un valor inicial para algún parámetro del diseño de Authentik.
 */
const DEFAULT_CONFIG: AuthentikExpansionConfig = {
  mfaLayout: {
    totpInstructionsHtml: 'Escanea el código QR con tu aplicación autenticadora para configurar tu cuenta.',
    qrBorderSize: 2,
    passkeyButtonColor: '#2b6cb0',
    backupCodesBgColor: '#f7fafc',
    allowDownloadTxt: true
  },
  consentStage: {
    showAppIcon: true,
    customScopeDescriptions: {
      'openid': 'Acceso a tu identidad básica de CASMARTS Core',
      'email': 'Acceso a tu dirección de correo electrónico',
      'profile': 'Acceso a tu perfil público (nombre, foto)'
    },
    termsAndPrivacyLinks: { terms: 'https://casmart.internal/terms', privacy: 'https://casmart.internal/privacy' }
  },
  errors: {
    err403Title: 'Acceso Denegado',
    err403Message: 'No tienes los permisos necesarios para acceder a este recurso.',
    err404Message: 'La página o el recurso que buscas no existe.',
    sessionExpiredMessage: 'Tu sesión ha expirado. Por favor, inicia sesión de nuevo.'
  },
  localization: {
    forceLocale: 'es',
    customTranslations: {
      'Log In': 'Iniciar Sesión',
      'Username': 'Usuario',
      'Password': 'Contraseña',
      'Forgot password?': '¿Olvidaste tu contraseña?',
      'Sign Up': 'Registrarse',
      'Flow does not apply to current user': 'El flujo no aplica al usuario actual.',
      'Continue': 'Continuar',
      'Please enter your password.': 'Por favor introduce tu contraseña.',
      'Log in to your account': 'Inicia sesión en tu cuenta',
      'Reset your password': 'Restablecer contraseña',
      'Your password has been reset successfully.': 'Tu contraseña ha sido restablecida con éxito.',
      'Access denied': 'Acceso denegado',
      'Something went wrong.': 'Algo salió mal.',
      'Email address': 'Dirección de correo',
      'Confirm Password': 'Confirmar contraseña',
      'Passwords do not match': 'Las contraseñas no coinciden',
      'Select an application': 'Selecciona una aplicación',
      'Log out': 'Cerrar sesión',
      'Are you sure you want to log out?': '¿Estás seguro de que deseas cerrar sesión?'
    },
    validationMessages: {
      requiredField: 'Este campo es obligatorio',
      invalidEmail: 'Introduce un correo válido',
      passwordMismatch: 'Las contraseñas no coinciden'
    }
  },
  userDashboard: {
    enableCustomDashboard: true,
    cardStyle: 'elevated',
    categoryOrder: ['Core Apps', 'AI Analytics', 'Security Tools'],
    showActiveSessions: true
  }
};

/**
 * Componente que gestiona la edición de configuraciones de expansión para Authentik
 * (MFA, Consentimientos, Errores personalizados, Traducciones y Dashboard de usuario).
 */
export const ExpansionSettingsManager: React.FC<ExpansionSettingsManagerProps> = ({
  initialConfig,
  onSaveConfig
}) => {
  // Estado local que almacena la configuración de expansión actual combinada con los defaults
  const [config, setConfig] = useState<AuthentikExpansionConfig>({
    ...DEFAULT_CONFIG,
    ...initialConfig
  });

  const [activeSection, setActiveSection] = useState<'mfa' | 'consent' | 'errors' | 'localization' | 'dashboard'>('localization');
  const [newKey, setNewKey] = useState('');
  const [newVal, setNewVal] = useState('');

  const updateMfaField = <K extends keyof AuthentikExpansionConfig['mfaLayout']>(key: K, value: AuthentikExpansionConfig['mfaLayout'][K]) => {
    setConfig(prev => ({
      ...prev,
      mfaLayout: { ...prev.mfaLayout, [key]: value }
    }));
  };

  const updateConsentField = <K extends keyof AuthentikExpansionConfig['consentStage']>(key: K, value: AuthentikExpansionConfig['consentStage'][K]) => {
    setConfig(prev => ({
      ...prev,
      consentStage: { ...prev.consentStage, [key]: value }
    }));
  };

  const updateErrorField = <K extends keyof AuthentikExpansionConfig['errors']>(key: K, value: AuthentikExpansionConfig['errors'][K]) => {
    setConfig(prev => ({
      ...prev,
      errors: { ...prev.errors, [key]: value }
    }));
  };

  const updateLocalizationField = <K extends keyof AuthentikExpansionConfig['localization']>(key: K, value: AuthentikExpansionConfig['localization'][K]) => {
    setConfig(prev => ({
      ...prev,
      localization: { ...prev.localization, [key]: value }
    }));
  };

  const updateValidationMsg = (key: keyof AuthentikExpansionConfig['localization']['validationMessages'], value: string) => {
    setConfig(prev => ({
      ...prev,
      localization: {
        ...prev.localization,
        validationMessages: { ...prev.localization.validationMessages, [key]: value }
      }
    }));
  };

  const updateDashboardField = <K extends keyof AuthentikExpansionConfig['userDashboard']>(key: K, value: AuthentikExpansionConfig['userDashboard'][K]) => {
    setConfig(prev => ({
      ...prev,
      userDashboard: { ...prev.userDashboard, [key]: value }
    }));
  };

  const handleTranslationChange = (key: string, value: string) => {
    setConfig(prev => ({
      ...prev,
      localization: {
        ...prev.localization,
        customTranslations: { ...prev.localization.customTranslations, [key]: value }
      }
    }));
  };

  const handleAddTranslation = () => {
    if (!newKey.trim()) return;
    handleTranslationChange(newKey.trim(), newVal.trim());
    setNewKey('');
    setNewVal('');
  };

  const handleRemoveTranslation = (key: string) => {
    setConfig(prev => {
      const updated = { ...prev.localization.customTranslations };
      delete updated[key];
      return {
        ...prev,
        localization: { ...prev.localization, customTranslations: updated }
      };
    });
  };

  const handleSave = () => {
    if (onSaveConfig) {
      onSaveConfig(config);
    } else {
      console.log('Saved Expansion Configuration:', config);
    }
  };

  return (
    <div className="w-full bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden text-left font-sans">
      {/* Navigation Sub-Tabs */}
      <div className="flex bg-gray-50 border-b border-gray-200 overflow-x-auto">
        {/*
          MFA, Errores y Dashboard se ocultan ya que no se pueden implementar de manera limpia
          sin alterar el core de Authentik de forma invasiva. Quedan habilitados únicamente
          Consentimiento y Traducciones.
        */}
        {(['consent', 'localization'] as const).map(tab => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveSection(tab)}
            className={`px-4 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all shrink-0 ${
              activeSection === tab
                ? 'border-[#4272A5] text-[#4272A5] bg-white'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            {tab === 'consent' && '🤝 Consentimiento'}
            {tab === 'localization' && '🗣 Traducciones'}
          </button>
        ))}
      </div>

      <div className="p-6 space-y-6">
        {/* SECTION: MFA / 2FA */}
        {activeSection === 'mfa' && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-gray-700">Configuración Visual de Multifactor (MFA)</h4>
            
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Instrucciones TOTP (HTML permitido)</label>
              <textarea
                value={config.mfaLayout.totpInstructionsHtml}
                onChange={e => updateMfaField('totpInstructionsHtml', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono bg-gray-50"
                rows={3}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Grosor de Borde QR (px)</label>
                <input
                  type="number"
                  value={config.mfaLayout.qrBorderSize}
                  onChange={e => updateMfaField('qrBorderSize', parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5 font-sans">Color del Botón Passkey</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="color"
                    value={config.mfaLayout.passkeyButtonColor}
                    onChange={e => updateMfaField('passkeyButtonColor', e.target.value)}
                    className="w-10 h-10 border border-gray-300 rounded cursor-pointer bg-transparent"
                  />
                  <input
                    type="text"
                    value={config.mfaLayout.passkeyButtonColor}
                    onChange={e => updateMfaField('passkeyButtonColor', e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50 font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5 font-sans">Fondo Códigos de Respaldo</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="color"
                    value={config.mfaLayout.backupCodesBgColor}
                    onChange={e => updateMfaField('backupCodesBgColor', e.target.value)}
                    className="w-10 h-10 border border-gray-300 rounded cursor-pointer bg-transparent"
                  />
                  <input
                    type="text"
                    value={config.mfaLayout.backupCodesBgColor}
                    onChange={e => updateMfaField('backupCodesBgColor', e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50 font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center pt-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.mfaLayout.allowDownloadTxt}
                    onChange={e => updateMfaField('allowDownloadTxt', e.target.checked)}
                    className="rounded border-gray-300 text-[#4272A5] focus:ring-[#4272A5]"
                  />
                  <span className="text-xs font-semibold text-gray-600">Permitir descargar códigos como archivo .TXT</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* SECTION: Consentimiento */}
        {activeSection === 'consent' && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-gray-700">Consentimiento Explícito OAuth2 / OIDC</h4>
            
            <label className="flex items-center gap-2 cursor-pointer mb-4">
              <input
                type="checkbox"
                checked={config.consentStage.showAppIcon}
                onChange={e => updateConsentField('showAppIcon', e.target.checked)}
                className="rounded border-gray-300 text-[#4272A5] focus:ring-[#4272A5]"
              />
              <span className="text-xs font-semibold text-gray-600">Mostrar icono de la aplicación solicitante</span>
            </label>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Enlace a Términos del Servicio</label>
                <input
                  type="text"
                  value={config.consentStage.termsAndPrivacyLinks.terms}
                  onChange={e => updateConsentField('termsAndPrivacyLinks', { ...config.consentStage.termsAndPrivacyLinks, terms: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                  placeholder="https://..."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Enlace a Políticas de Privacidad</label>
                <input
                  type="text"
                  value={config.consentStage.termsAndPrivacyLinks.privacy}
                  onChange={e => updateConsentField('termsAndPrivacyLinks', { ...config.consentStage.termsAndPrivacyLinks, privacy: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                  placeholder="https://..."
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Descripciones Personalizadas de Permisos (Scopes)</label>
              <div className="space-y-2">
                {Object.entries(config.consentStage.customScopeDescriptions).map(([scope, desc]) => (
                  <div key={scope} className="flex gap-2">
                    <span className="px-2.5 py-1.5 bg-gray-100 rounded-lg text-xs font-mono border border-gray-200 shrink-0 select-all">{scope}</span>
                    <input
                      type="text"
                      value={desc}
                      onChange={e => {
                        const updated = { ...config.consentStage.customScopeDescriptions, [scope]: e.target.value };
                        updateConsentField('customScopeDescriptions', updated);
                      }}
                      className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-gray-50"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* SECTION: Errores */}
        {activeSection === 'errors' && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-gray-700">Páginas de Error Customizadas</h4>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Título Error 403 (Acceso Denegado)</label>
                <input
                  type="text"
                  value={config.errors.err403Title}
                  onChange={e => updateErrorField('err403Title', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Mensaje Error 403</label>
                <input
                  type="text"
                  value={config.errors.err403Message}
                  onChange={e => updateErrorField('err403Message', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Mensaje Error 404 (Página no encontrada)</label>
                <input
                  type="text"
                  value={config.errors.err404Message}
                  onChange={e => updateErrorField('err404Message', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Mensaje Sesión Expirada</label>
                <input
                  type="text"
                  value={config.errors.sessionExpiredMessage}
                  onChange={e => updateErrorField('sessionExpiredMessage', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                />
              </div>
            </div>
          </div>
        )}

        {/* SECTION: Traducciones y Localización */}
        {activeSection === 'localization' && (
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-bold text-gray-700 mb-3">Módulo de Localización (Prevención de Inglés Residual)</h4>
              <div className="grid grid-cols-2 gap-4 items-center">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5">Idioma Forzado</label>
                  <select
                    value={config.localization.forceLocale}
                    onChange={e => updateLocalizationField('forceLocale', e.target.value as 'es' | 'en')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                  >
                    <option value="es">Español (es)</option>
                    <option value="en">English (en)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="border-t border-gray-100 pt-4">
              <h5 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Mensajes de Validación</h5>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10px] font-semibold text-gray-600 mb-1">Campo Requerido</label>
                  <input
                    type="text"
                    value={config.localization.validationMessages.requiredField}
                    onChange={e => updateValidationMsg('requiredField', e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-gray-50"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-gray-600 mb-1">Email Inválido</label>
                  <input
                    type="text"
                    value={config.localization.validationMessages.invalidEmail}
                    onChange={e => updateValidationMsg('invalidEmail', e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-gray-50"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-gray-600 mb-1">Contraseñas No Coinciden</label>
                  <input
                    type="text"
                    value={config.localization.validationMessages.passwordMismatch}
                    onChange={e => updateValidationMsg('passwordMismatch', e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs bg-gray-50"
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-gray-100 pt-4">
              <h5 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Sustitución de Cadenas del DOM</h5>
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  placeholder="Cadena en inglés (ej: Log In)"
                  value={newKey}
                  onChange={e => setNewKey(e.target.value)}
                  className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white"
                />
                <input
                  type="text"
                  placeholder="Sustitución en español (ej: Iniciar Sesión)"
                  value={newVal}
                  onChange={e => setNewVal(e.target.value)}
                  className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white"
                />
                <button
                  type="button"
                  onClick={handleAddTranslation}
                  className="px-4 py-1.5 bg-[#4272A5] text-white text-xs font-bold rounded-lg hover:bg-[#2d5580] transition-colors"
                >
                  Agregar
                </button>
              </div>

              <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-lg shadow-sm">
                <table className="min-w-full bg-white divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-[10px] font-bold text-gray-500 uppercase">Cadena Original (DOM)</th>
                      <th className="px-4 py-2 text-left text-[10px] font-bold text-gray-500 uppercase">Sustitución en Español</th>
                      <th className="px-4 py-2 w-16"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 text-xs">
                    {Object.entries(config.localization.customTranslations).map(([key, val]) => (
                      <tr key={key}>
                        <td className="px-4 py-2 font-mono font-medium text-gray-500 select-all">{key}</td>
                        <td className="px-4 py-2">
                          <input
                            type="text"
                            value={val}
                            onChange={e => handleTranslationChange(key, e.target.value)}
                            className="w-full px-2 py-1 border border-gray-200 rounded text-xs bg-gray-50 focus:bg-white"
                          />
                        </td>
                        <td className="px-4 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => handleRemoveTranslation(key)}
                            className="text-red-500 hover:text-red-700 font-bold transition-colors"
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* SECTION: User Dashboard */}
        {activeSection === 'dashboard' && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-gray-700">Catálogo de Aplicaciones (Launchpad) / Portal</h4>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.userDashboard.enableCustomDashboard}
                    onChange={e => updateDashboardField('enableCustomDashboard', e.target.checked)}
                    className="rounded border-gray-300 text-[#4272A5] focus:ring-[#4272A5]"
                  />
                  <span className="text-xs font-semibold text-gray-600">Habilitar Launchpad unificado en CASMARTS Core</span>
                </label>
              </div>

              <div className="flex items-center">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.userDashboard.showActiveSessions}
                    onChange={e => updateDashboardField('showActiveSessions', e.target.checked)}
                    className="rounded border-gray-300 text-[#4272A5] focus:ring-[#4272A5]"
                  />
                  <span className="text-xs font-semibold text-gray-600">Mostrar lista de sesiones de usuario activas</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Estilo de las Tarjetas (Cards) de Aplicación</label>
              <select
                value={config.userDashboard.cardStyle}
                onChange={e => updateDashboardField('cardStyle', e.target.value as 'flat' | 'elevated' | 'minimal')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
              >
                <option value="flat">Estilo Plano (Flat)</option>
                <option value="elevated">Estilo Elevado con Sombra (Elevated)</option>
                <option value="minimal">Estilo Minimalista (Bordes Sutiles)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Orden de Categorías en Launchpad</label>
              <input
                type="text"
                value={config.userDashboard.categoryOrder.join(', ')}
                onChange={e => updateDashboardField('categoryOrder', e.target.value.split(',').map(s => s.trim()))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50"
                placeholder="Core Apps, Analytics, Admin Tools..."
              />
              <p className="text-[10px] text-gray-400 mt-1">Ingresa las categorías separadas por comas.</p>
            </div>
          </div>
        )}
      </div>

      {/* Save panel footer button */}
      <div className="p-4 bg-gray-50 border-t border-gray-200 flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          className="px-5 py-2.5 bg-[#4272A5] hover:bg-[#2d5580] text-white text-xs font-bold uppercase tracking-wider rounded-lg shadow transition-colors cursor-pointer"
        >
          Aplicar Configuración Avanzada
        </button>
      </div>
    </div>
  );
};
