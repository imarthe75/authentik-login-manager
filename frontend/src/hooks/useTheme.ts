import { useState, useCallback } from 'react';
import { Theme } from '../types/theme';
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
  primary_color: '#8B3A2A',
  hover_color: '#a04535',
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
  privacy_pdf_url: '/static/aviso_privacidad.pdf',
  is_active: true
};

export const useTheme = () => {
  const [currentSlug, setCurrentSlug] = useState<string>('default-authentication-flow');
  const [theme, setTheme] = useState<Theme>({ ...DEFAULT_THEME_STATE });
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [savePhase, setSavePhase] = useState<SavePhase>('idle');
  const [deployError, setDeployError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isSaving = savePhase === 'saving' || savePhase === 'deploying';

  const loadTheme = useCallback(async (slug: string) => {
    try {
      setError(null);
      setCurrentSlug(slug);
      const data = await themesApi.getTheme(slug);
      setTheme(data);
      setIsDirty(false);
      setSavePhase('idle');
      setDeployError(null);
    } catch (err: any) {
      console.warn("Theme record not in DB. Initializing locally.", err);
      setTheme({
        ...DEFAULT_THEME_STATE,
        authentik_flow_slug: slug,
        display_name: slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      });
      setIsDirty(true);
      setSavePhase('idle');
      setDeployError(null);
    }
  }, []);

  const updateField = useCallback(<K extends keyof Theme>(key: K, value: Theme[K]) => {
    setTheme((prev) => ({ ...prev, [key]: value }));
    setIsDirty(true);
    setSavePhase('idle');
    setDeployError(null);
  }, []);

  const convertFileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (err) => reject(err);
    });
  };

  const uploadFileField = useCallback(async (key: 'logo_top_base64' | 'logo_bottom_base64' | 'bg_image_base64', file: File) => {
    try {
      const base64Str = await convertFileToBase64(file);
      updateField(key, base64Str);
    } catch (err) {
      console.error("Base64 file translation failure: ", err);
      setError("Error converting file to Base64.");
    }
  }, [updateField]);

  const saveTheme = useCallback(async () => {
    let currentPhase: SavePhase = 'idle';
    try {
      setError(null);
      setDeployError(null);

      // Phase 1: persist to database
      currentPhase = 'saving';
      setSavePhase('saving');
      const saved = await themesApi.upsertTheme(theme);
      setTheme(saved);
      setIsDirty(false);

      // Phase 2: invalidate Valkey cache + deploy static template
      currentPhase = 'deploying';
      setSavePhase('deploying');
      await themesApi.invalidatePublicCache(theme.authentik_flow_slug);
      await themesApi.deployTheme(theme.authentik_flow_slug);

      setSavePhase('done');
    } catch (err: any) {
      const msg = err?.message || 'Error al guardar o desplegar.';
      if (currentPhase === 'saving') {
        // Hard failure: nothing was saved
        setError(msg);
        setSavePhase('idle');
      } else {
        // Theme was saved but deploy failed — non-blocking warning
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
    uploadFileField,
    saveTheme,
    retryDeploy,
    setTheme,
    setIsDirty
  };
};
