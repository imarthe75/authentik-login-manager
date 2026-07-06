export interface AuthentikExpansionConfig {
  // 1. Control de Flujos Avanzados de Autenticación
  mfaLayout: {
    totpInstructionsHtml: string;
    qrBorderSize: number;
    passkeyButtonColor: string;
    backupCodesBgColor: string;
    allowDownloadTxt: boolean;
  };
  consentStage: {
    showAppIcon: boolean;
    customScopeDescriptions: Record<string, string>; // Mapeo de scopes (ej: 'openid' -> 'Tu identidad base')
    termsAndPrivacyLinks: { terms: string; privacy: string };
  };
  errors: {
    err403Title: string;
    err403Message: string;
    err404Message: string;
    sessionExpiredMessage: string;
  };
  
  // 2. Sistema Anti-Inglés (Localización Forzada)
  localization: {
    forceLocale: 'es' | 'en';
    customTranslations: Record<string, string>; // Diccionario dinámico de sustitución del DOM
    validationMessages: {
      requiredField: string;
      invalidEmail: string;
      passwordMismatch: string;
    };
  };
  
  // 3. Interfaz del Catálogo / Launchpad de CASMARTS
  userDashboard: {
    enableCustomDashboard: boolean;
    cardStyle: 'flat' | 'elevated' | 'minimal';
    categoryOrder: string[];
    showActiveSessions: boolean;
  };
}
