import type { ReactNode } from 'react';

export type NavItem = {
  key: string;
  icon: ReactNode;
  to?: string;
};

export const mainNav: NavItem[] = [
  { key: 'dashboard', icon: <i className="fa-solid fa-house" aria-hidden /> },
  { key: 'curriculos', icon: <i className="fa-regular fa-file-lines" aria-hidden />, to: '/protected/resumes' },
  { key: 'analiseComIA', icon: <i className="fa-solid fa-wand-magic-sparkles" aria-hidden />, to: '/protected/ai-analysis' },
  { key: 'historico', icon: <i className="fa-solid fa-clock-rotate-left" aria-hidden /> },
];

export const bottomNav: NavItem[] = [
  { key: 'perfil', icon: <i className="fa-regular fa-user" aria-hidden />, to: '/protected/profile' },
  { key: 'config', icon: <i className="fa-solid fa-gear" aria-hidden />, to: '/protected/settings' },
  { key: 'sair', icon: <i className="fa-solid fa-arrow-right-from-bracket" aria-hidden /> },
];

