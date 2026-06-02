import { useState, useCallback } from 'react';
import { Theme, EmailBodies } from '../types/theme';
import { themesApi } from '../api/themesApi';

export type SavePhase = 'idle' | 'saving' | 'deploying' | 'done' | 'deploy_error';

const DEFAULT_THEME_STATE: Theme = {
  authentik_flow_slug: 'default-authentication-flow',
  display_name: 'CASMARTS Portal',
  system_name: 'CASMARTS<br>Core',
  system_subtitle: 'Gobierno del estado de México',
  layout_position: 'left',
  name_align: 'center',
  subtitle_align: 'center',
  privacy_align: 'center',
  primary_color: '#4272A5',
  hover_color: '#2d5580',
  card_bg_color: '#FFFFFF',
  panel_bg_color: '#F6F9FD',
  bg_type: 'gradient',
  bg_flat_color: null,
  bg_gradient_from: '#c8c4bc',
  bg_gradient_to: '#a09890',
  bg_image_base64: null,
  bg_opacity: 1.0,
  form_opacity: 0.55,
  form_height_pct: null,
  logos_opacity: 0.55,
  logos_height_pct: null,
  logo_top_base64: null,
  logo_bottom_base64: null,
  logo_top_text: null,
  logo_bottom_text: null,
  privacy_pdf_url: '/static/aviso_privacidad.pdf',
  is_active: true,
  allow_self_registration: false,
  require_email_verification: false,
  show_social_google: false,
  show_social_microsoft: false,
  show_social_gov_id: false,
  email_footer_text: null,
  email_template_type: 'integrated',
  email_bodies: {},
};

export const useTheme = () => {
  const [currentSlug, setCurrentSlug] = useState<string>('default-authentication-flow');
  const [theme, setTheme] = useState<Theme>({ ...DEFAULT_THEME_STATE });
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [savePhase, setSavePhase] = useState<SavePhase>('idle');
  const [deployError, setDeployError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isSaving = savePhase === 'saving' || savePhase === 'deploying';

  const loadTheme = useCallback(async (slug: string, appSlug?: string | null) => {
    try {
      setError(null);
      setCurrentSlug(slug);

      if (appSlug) {
        try {
          const data = await themesApi.getTheme(slug, appSlug);
          setTheme(data);
          setIsDirty(false);
          setSavePhase('idle');
          setDeployError(null);
          return;
        } catch {
          try {
            const globalData = await themesApi.getTheme(slug, null);
            const newAppTheme: Theme = {
              ...globalData,
              authentik_app_slug: appSlug,
              display_name: `${globalData.display_name} - ${appSlug}`,
            };
            delete (newAppTheme as any).id;
            setTheme(newAppTheme);
            setIsDirty(true);
            setSavePhase('idle');
            setDeployError(null);
            return;
          } catch { /* fall through */ }
        }
      } else {
        try {
          const data = await themesApi.getTheme(slug, null);
          setTheme(data);
          setIsDirty(false);
          setSavePhase('idle');
          setDeployError(null);
          return;
        } catch { /* fall through */ }
      }

      setTheme({
        ...DEFAULT_THEME_STATE,
        authentik_flow_slug: slug,
        authentik_app_slug: appSlug || null,
        display_name: slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      });
      setIsDirty(true);
      setSavePhase('idle');
      setDeployError(null);
    } catch {
      setTheme({
        ...DEFAULT_THEME_STATE,
        authentik_flow_slug: slug,
        authentik_app_slug: appSlug || null,
        display_name: slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      });
      setIsDirty(true);
      setSavePhase('idle');
      setDeployError(null);
    }
  }, []);

  const updateField = useCallback(<K extends keyof Theme>(key: K, value: Theme[K]) => {
    setTheme(prev => {
      const next = { ...prev, [key]: value };
      // Coerce: require_email_verification must be false when self-registration is off
      if (key === 'allow_self_registration' && !value) {
        next.require_email_verification = false;
      }
      return next;
    });
    setIsDirty(true);
    setSavePhase('idle');
    setDeployError(null);
  }, []);

  const updateEmailBody = useCallback((eventType: string, body: { subject: string; body_html: string }) => {
    setTheme(prev => ({
      ...prev,
      email_bodies: { ...(prev.email_bodies ?? {}), [eventType]: body },
    }));
    setIsDirty(true);
    setSavePhase('idle');
    setDeployError(null);
  }, []);

  const convertFileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
    });

  const uploadFileField = useCallback(
    async (key: 'logo_top_base64' | 'logo_bottom_base64' | 'bg_image_base64', file: File) => {
      try {
        const base64Str = await convertFileToBase64(file);
        updateField(key, base64Str);
      } catch {
        setError('Error converting file to Base64.');
      }
    },
    [updateField]
  );

  const saveTheme = useCallback(async () => {
    let currentPhase: SavePhase = 'idle';
    try {
      setError(null);
      setDeployError(null);
      currentPhase = 'saving';
      setSavePhase('saving');
      const saved = await themesApi.upsertTheme(theme);
      setTheme(saved);
      setIsDirty(false);
      currentPhase = 'deploying';
      setSavePhase('deploying');
      await themesApi.invalidatePublicCache(theme.authentik_flow_slug);
      await themesApi.deployTheme(theme.authentik_flow_slug);
      setSavePhase('done');
    } catch (err: any) {
      const msg = err?.message || 'Error al guardar o desplegar.';
      if (currentPhase === 'saving') {
        setError(msg);
        setSavePhase('idle');
      } else {
        setDeployError(msg);
        setSavePhase('deploy_error');
      }
    }
  }, [theme]);

  const retryDeploy = useCallback(async () => {
    try {
      setDeployError(null);
      setSavePhase('deploying');
      await themesApi.deployTheme(theme.authentik_flow_slug);
      setSavePhase('done');
    } catch (err: any) {
      setDeployError(err?.message || 'Error al desplegar la plantilla en Authentik.');
      setSavePhase('deploy_error');
    }
  }, [theme.authentik_flow_slug]);

  return {
    currentSlug,
    theme,
    isDirty,
    isSaving,
    savePhase,
    deployError,
    error,
    loadTheme,
    updateField,
    updateEmailBody,
    uploadFileField,
    saveTheme,
    retryDeploy,
    setTheme,
    setIsDirty,
  };
};
