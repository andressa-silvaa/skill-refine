import type { ReactNode } from 'react';

export type ThemeBlock = {
  key: string;
  node: ReactNode;
  kind?: 'header' | 'section';
  breakable?: boolean;
};

export type ThemeLayoutData =
  | {
      type: 'single';
      blocks: ThemeBlock[];
      variant?: string;
    }
  | {
      type: 'two-column';
      main: ThemeBlock[];
      sidebar: ThemeBlock[];
      variant: 'split' | 'tech' | 'compact';
      headerPlacement?: 'full';
    };
