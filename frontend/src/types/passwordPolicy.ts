export interface PasswordPolicy {
  id: string;
  length_min: number;
  amount_uppercase: number;
  amount_lowercase: number;
  amount_digits: number;
  amount_symbols: number;
  symbol_charset: string;
  check_zxcvbn: boolean;
  zxcvbn_score_threshold: number;
  check_have_i_been_pwned: boolean;
  hibp_allowed_count: number;
  error_message: string;
  help_text: string;
  expiry_enabled: boolean;
  expiry_days: number;
  link_expiry_minutes: number;
  lockout_failed_attempts: number;
  last_synced_at: string | null;
  updated_at: string;
  synced_to_authentik: boolean | null;
  sync_error: string | null;
}

export type PasswordPolicyUpdate = Partial<
  Omit<PasswordPolicy, 'id' | 'last_synced_at' | 'updated_at' | 'synced_to_authentik' | 'sync_error'>
>;
