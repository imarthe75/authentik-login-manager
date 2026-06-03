import React, { useEffect, useState } from 'react';
import { useTheme } from './hooks/useTheme';
import { ThemeSelector } from './components/ThemeSelector';
import { LoginPreview } from './components/LoginPreview';
import { ConfigPanel } from './components/ConfigPanel';
import { themesApi } from './api/themesApi';
import { Theme } from './types/theme';

export const App: React.FC = () => {
  const {
    currentSlug,
    theme,
    isDirty,
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
    setIsDirty
  } = useTheme();

  const [themesList, setThemesList] = useState<Theme[]>([]);
  const [authentikApps, setAuthentikApps] = useState<{ slug: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchApps = async () => {
    try {
      const apps = await themesApi.getAuthentikApplications();
      setAuthentikApps(apps);
    } catch (err) {
      console.error("Error fetching Authentik applications list: ", err);
    }
  };

  const fetchThemes = async () => {
    try {
      setLoading(true);
      const data = await themesApi.getThemes();
      setThemesList(data);
      
      // If list is not empty and theme is default, load the first one
      if (data.length > 0) {
        const found = data.find(t => t.authentik_flow_slug === currentSlug);
        if (found) {
          setTheme(found);
          setIsDirty(false);
        } else {
          // Load first in list
          loadTheme(data[0].authentik_flow_slug);
        }
      } else {
        // Safe fallback if DB is completely empty (initialize with seed)
        const seedTheme: Theme = {
          authentik_flow_slug: 'default-authentication-flow',
          authentik_app_slug: null,
          display_name: 'CASMARTS Core Portal',
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
        setThemesList([seedTheme]);
        setTheme(seedTheme);
        setIsDirty(false);
      }
    } catch (err) {
      console.error("Error loading theme configurations list: ", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThemes();
    fetchApps();
  }, []);

  const handleSelectSlug = (slug: string) => {
    if (isDirty) {
      const confirmLeave = window.confirm("Tienes cambios sin guardar en este portal. ¿Deseas descartarlos y cambiar de portal?");
      if (!confirmLeave) return;
    }
    loadTheme(slug);
  };
  
  const handleChangeApp = (appSlug: string | null) => {
    if (isDirty) {
      const confirmLeave = window.confirm("Tienes cambios sin guardar. ¿Deseas descartarlos y cambiar de aplicación?");
      if (!confirmLeave) return;
    }
    loadTheme(theme.authentik_flow_slug, appSlug);
  };

  const handleCreateTheme = (displayName: string, flowSlug: string) => {
    const newTheme: Theme = {
      authentik_flow_slug: flowSlug,
      authentik_app_slug: null,
      display_name: displayName,
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
    
    // Add to dropdown list and set as current
    setThemesList(prev => [newTheme, ...prev]);
    setTheme(newTheme);
    setIsDirty(true);
  };

  const handleSave = async () => {
    await saveTheme();
    // Re-fetch list to capture updated changes or creation
    fetchThemes();
  };

  return (
    <div className="w-screen h-screen flex flex-col font-sans overflow-hidden bg-gray-100">
      {/* Top Navigation Header Bar */}
      <header className="h-16 shrink-0 bg-white border-b border-gray-200 px-6 flex items-center justify-between shadow-sm z-30">
        <div className="flex items-center gap-3">
          <div className="bg-[#4272A5] text-white p-2 rounded-lg font-black text-sm tracking-wider">
            CA
          </div>
          <div>
            <h1 className="font-extrabold text-base text-gray-800 leading-none">Authentik Login Manager</h1>
            <span className="text-[10px] text-gray-400 font-semibold tracking-widest uppercase">CASMARTS SAAS INTERNAL</span>
          </div>
        </div>

        {/* Dropdown theme selection */}
        {!loading && (
          <ThemeSelector
            themes={themesList}
            currentSlug={theme.authentik_flow_slug}
            onSelectSlug={handleSelectSlug}
            onCreateTheme={handleCreateTheme}
          />
        )}
      </header>

      {/* Main Two-Column Panel Container */}
      <main className="flex-1 flex items-stretch overflow-hidden relative">
        {/* Error notification drawer banner */}
        {error && (
          <div className="absolute top-4 left-6 z-40 max-w-sm bg-red-600 text-white rounded-xl shadow-2xl p-4 flex items-start gap-2.5 animate-slideIn">
            <span className="text-xl">⚠️</span>
            <div className="flex-1">
              <h4 className="font-bold text-xs">Error de Servidor</h4>
              <p className="text-[11px] opacity-90 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Left Column Preview (~60%) */}
        <section className="flex-1 h-full relative bg-gray-800">
          <LoginPreview theme={theme} />
        </section>

        {/* Right Column Customizer Drawer Panel (~40%) */}
        <section className="w-[380px] shrink-0 h-full">
          <ConfigPanel
            theme={theme}
            isDirty={isDirty}
            savePhase={savePhase}
            deployError={deployError}
            onUpdateField={updateField}
            onUploadFile={uploadFileField}
            onSave={handleSave}
            onRetryDeploy={retryDeploy}
            authentikApps={authentikApps}
            onChangeApp={handleChangeApp}
            onUpdateEmailBody={updateEmailBody}
          />
        </section>
      </main>
    </div>
  );
};

export default App;
