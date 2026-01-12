import type { HTMLAttributes, PropsWithChildren } from 'react';

import './Chip.css';

type Props = PropsWithChildren<HTMLAttributes<HTMLSpanElement>>;

export function Chip(props: Props) {
  const { className = '', children, ...rest } = props;
  return (
    <span {...rest} className={`sr-chip${className ? ` ${className}` : ''}`}>
      {children}
    </span>
  );
}
