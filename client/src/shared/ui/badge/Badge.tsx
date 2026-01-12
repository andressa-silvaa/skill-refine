import type { HTMLAttributes, PropsWithChildren } from 'react';

import './Badge.css';

type Tone = 'neutral' | 'success' | 'warning';

type Props = PropsWithChildren<HTMLAttributes<HTMLSpanElement>> & {
  tone?: Tone;
};

export function Badge(props: Props) {
  const { className = '', tone = 'neutral', children, ...rest } = props;
  return (
    <span {...rest} className={`sr-badge sr-badge--${tone}${className ? ` ${className}` : ''}`}>
      {children}
    </span>
  );
}
