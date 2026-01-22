import type { ReactNode } from 'react';

import './ThemeGrid.css';

type Props = {
  children: ReactNode;
  variant?: 'grid' | 'carousel';
};

export function ThemeGrid({ children, variant = 'grid' }: Props) {
  return (
    <div className={`sr-theme-grid sr-theme-grid--${variant}`} role="list">
      {children}
    </div>
  );
}
