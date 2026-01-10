import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';

import { resources } from './resources';

export const i18n = i18next.createInstance();

void i18n.use(initReactI18next).init({
  resources: resources as any,
  lng: 'pt-BR',
  fallbackLng: 'pt-BR',
  interpolation: { escapeValue: false },
});
