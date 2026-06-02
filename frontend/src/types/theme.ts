export type AlignValue = 'left' | 'center' | 'right';
export type BgType = 'gradient' | 'color' | 'image';
export type EmailTemplateType = 'integrated' | 'custom_per_event';
export type EmailEventType =
  | 'password_reset'
  | 'new_account'
  | 'account_lockout'
  | 'email_verification'
  | 'security_change';

export interface EmailBody {
  subject: string;
  body_html: string;
}

export type EmailBodies = Partial<Record<EmailEventType, EmailBody>>;

export interface SocialProviders {
  show_social_google: boolean;
  show_social_microsoft: boolean;
  show_social_gov_id: boolean;
}

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
  email_footer_text: string | null;
  email_template_type: EmailTemplateType;
  email_bodies?: EmailBodies;
  created_at?: string;
  updated_at?: string;
}

export const EMAIL_EVENT_LABELS: Record<EmailEventType, string> = {
  password_reset: 'Restablecer contraseña',
  new_account: 'Nueva cuenta',
  account_lockout: 'Bloqueo de cuenta',
  email_verification: 'Verificación de correo',
  security_change: 'Cambio de seguridad',
};

export const EMAIL_EVENT_TYPES: EmailEventType[] = [
  'password_reset',
  'new_account',
  'account_lockout',
  'email_verification',
  'security_change',
];

export const EMPTY_EMAIL_BODY: EmailBody = { subject: '', body_html: '' };
