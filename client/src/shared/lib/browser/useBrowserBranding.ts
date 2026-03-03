import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

import { useSession } from '@/entities/session';
import { i18n } from '@/shared/lib/i18n';
import { APPEARANCE_CHANGE_EVENT } from '@/shared/lib/theme/appearance';

import { applyContextFavicon } from './favicon';
import { isProtectedPath, resolvePageTitle } from './pageTitle';

function useI18nLanguage() {
  const [language, setLanguage] = useState(() => i18n.resolvedLanguage || i18n.language || 'pt-BR');

  useEffect(() => {
    const onLanguageChanged = (nextLanguage: string) => {
      setLanguage(nextLanguage);
    };
    i18n.on('languageChanged', onLanguageChanged);
    return () => {
      i18n.off('languageChanged', onLanguageChanged);
    };
  }, []);

  return language;
}

export function useBrowserBranding() {
  const location = useLocation();
  const { preferences } = useSession();
  const currentLanguage = useI18nLanguage();
  const [previewAccentColor, setPreviewAccentColor] = useState<string | null>(null);

  useEffect(() => {
    const onAppearanceChanged = (event: Event) => {
      const customEvent = event as CustomEvent<{ accentColor?: string | null }>;
      if (typeof customEvent.detail?.accentColor === 'string') {
        setPreviewAccentColor(customEvent.detail.accentColor);
      }
    };

    window.addEventListener(APPEARANCE_CHANGE_EVENT, onAppearanceChanged);
    return () => {
      window.removeEventListener(APPEARANCE_CHANGE_EVENT, onAppearanceChanged);
    };
  }, []);

  useEffect(() => {
    const pathname = location.pathname;
    const isProtected = isProtectedPath(pathname);
    applyContextFavicon({ isProtected, accentColor: previewAccentColor ?? preferences?.accent_color });
    document.title = resolvePageTitle(pathname, (key) => i18n.t(key, { lng: currentLanguage }));
  }, [currentLanguage, location.pathname, preferences?.accent_color, previewAccentColor]);
}
