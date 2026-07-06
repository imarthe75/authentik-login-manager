/**
 * Configuración de expansión avanzada para la personalización de flujos
 * de Authentik (MFA, Consentimientos, Errores, Localización y Dashboard).
 */
export interface AuthentikExpansionConfig {
  /** 1. Control y diseño de flujos avanzados de Autenticación de Múltiples Factores (MFA) */
  mfaLayout: {
    /** Texto instructivo para TOTP renderizado en formato HTML. */
    totpInstructionsHtml: string;
    /** Tamaño del borde del código QR. */
    qrBorderSize: number;
    /** Color del botón de inicio de sesión con llave de acceso física (Passkey). */
    passkeyButtonColor: string;
    /** Color de fondo para la sección de códigos de respaldo. */
    backupCodesBgColor: string;
    /** Permite al usuario descargar un archivo de texto plano con los códigos de respaldo. */
    allowDownloadTxt: boolean;
  };
  /** Configuración para la etapa de consentimiento de permisos de la aplicación. */
  consentStage: {
    /** Muestra u oculta el icono de la aplicación solicitante de acceso. */
    showAppIcon: boolean;
    /** Mapeo de descripción personalizada de scopes (ej: 'openid' -> 'Tu identidad base'). */
    customScopeDescriptions: Record<string, string>;
    /** Enlaces externos para términos del servicio y políticas de privacidad. */
    termsAndPrivacyLinks: { terms: string; privacy: string };
  };
  /** Mensajes y títulos de error personalizados presentados al usuario. */
  errors: {
    /** Título para el error 403 (Acceso Denegado). */
    err403Title: string;
    /** Mensaje explicativo para el error 403. */
    err403Message: string;
    /** Mensaje explicativo para páginas no encontradas (error 404). */
    err404Message: string;
    /** Mensaje mostrado cuando expira la sesión activa de navegación. */
    sessionExpiredMessage: string;
  };
  
  /** 2. Sistema de Localización y reemplazo dinámico de términos del DOM */
  localization: {
    /** Forzar un idioma específico ('es' o 'en'). */
    forceLocale: 'es' | 'en';
    /** Diccionario dinámico de sustitución en la traducción del DOM. */
    customTranslations: Record<string, string>;
    /** Mensajes de error en validaciones locales. */
    validationMessages: {
      requiredField: string;
      invalidEmail: string;
      passwordMismatch: string;
    };
  };
  
  /** 3. Interfaz del Catálogo y Launchpad de Aplicaciones de CASMARTS */
  userDashboard: {
    /** Habilitar o deshabilitar el dashboard personalizado. */
    enableCustomDashboard: boolean;
    /** Estilo de renderizado de las tarjetas de aplicaciones. */
    cardStyle: 'flat' | 'elevated' | 'minimal';
    /** Ordenación de categorías por etiquetas. */
    categoryOrder: string[];
    /** Determina si se deben mostrar las sesiones de usuario activas. */
    showActiveSessions: boolean;
  };
}

