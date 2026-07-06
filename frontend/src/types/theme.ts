/** Alineación de texto y diseño (izquierda, centro, derecha). */
export type AlignValue = 'left' | 'center' | 'right';

/** Tipo de fondo de pantalla a renderizar. */
export type BgType = 'gradient' | 'color' | 'image';

/** Tipo de envío de correo (integrado o plantilla personalizada por evento). */
export type EmailTemplateType = 'integrated' | 'custom_per_event';

/** Lista de todos los tipos de eventos de correo soportados en la plataforma. */
export type EmailEventType =
  | 'password_reset'
  | 'new_account'
  | 'account_lockout'
  | 'email_verification'
  | 'security_change'
  | 'account_locked_admin'
  | 'account_unlocked_admin'
  | 'login_success'
  | 'suspicious_request'
  | 'invitation_used'
  | 'app_authorized'
  | 'impersonation_started'
  | 'account_deleted';

/** Estructura que define el cuerpo HTML y el asunto de una plantilla de correo. */
export interface EmailBody {
  subject: string;
  body_html: string;
}

/** Diccionario opcional que mapea eventos de correo con sus plantillas asociadas. */
export type EmailBodies = Partial<Record<EmailEventType, EmailBody>>;

/** Configuración de visibilidad para los proveedores de autenticación social. */
export interface SocialProviders {
  show_social_google: boolean;
  show_social_microsoft: boolean;
  show_social_gov_id: boolean;
}

/**
 * Interfaz principal que representa la estructura completa del Tema de un Tenant.
 */
export interface Theme {
  id?: string;
  authentik_flow_slug: string;
  authentik_app_slug?: string | null;
  display_name: string;
  system_name: string;
  system_subtitle: string;
  layout_position: AlignValue;
  name_align: AlignValue;
  subtitle_align: AlignValue;
  privacy_align: AlignValue;
  primary_color: string;
  hover_color: string;
  card_bg_color: string;
  panel_bg_color: string;
  bg_type: BgType;
  bg_flat_color: string | null;
  bg_gradient_from: string;
  bg_gradient_to: string;
  bg_image_base64: string | null;
  bg_opacity: number;
  form_opacity: number;
  form_height_pct: number | null;
  logos_opacity: number;
  logos_height_pct: number | null;
  logo_top_base64: string | null;
  logo_bottom_base64: string | null;
  logo_top_text: string | null;
  logo_bottom_text: string | null;
  privacy_pdf_url: string | null;
  is_active: boolean;
  // Access & notifications (new)
  allow_self_registration: boolean;
  require_email_verification: boolean;
  show_social_google: boolean;
  show_social_microsoft: boolean;
  show_social_gov_id: boolean;
  show_forgot_password: boolean;
  show_logos_panel: boolean;
  show_password_toggle: boolean;
  show_system_name: boolean;
  show_system_subtitle: boolean;
  show_field_labels: boolean;
  show_app_message: boolean;
  email_footer_text: string | null;
  email_template_type: EmailTemplateType;
  email_bodies?: EmailBodies;
  custom_messages?: Record<string, string> | null;
  expansion_config?: import('./models').AuthentikExpansionConfig | null;
  created_at?: string;
  updated_at?: string;
}

export const EMAIL_EVENT_LABELS: Record<EmailEventType, string> = {
  password_reset: 'Restablecer contraseña',
  new_account: 'Nueva cuenta',
  account_lockout: 'Bloqueo de cuenta',
  email_verification: 'Verificación de correo',
  security_change: 'Cambio de seguridad',
  account_locked_admin: 'Bloqueo por administrador',
  account_unlocked_admin: 'Desbloqueo por administrador',
  login_success: 'Inicio de sesión exitoso',
  suspicious_request: 'Actividad sospechosa',
  invitation_used: 'Invitación aceptada',
  app_authorized: 'Aplicación autorizada',
  impersonation_started: 'Acceso administrativo (impersonación)',
  account_deleted: 'Cuenta eliminada',
};

export const EMAIL_EVENT_TYPES: EmailEventType[] = [
  'password_reset',
  'new_account',
  'account_lockout',
  'email_verification',
  'security_change',
  'account_locked_admin',
  'account_unlocked_admin',
  'login_success',
  'suspicious_request',
  'invitation_used',
  'app_authorized',
  'impersonation_started',
  'account_deleted',
];

export const EMPTY_EMAIL_BODY: EmailBody = { subject: '', body_html: '' };
