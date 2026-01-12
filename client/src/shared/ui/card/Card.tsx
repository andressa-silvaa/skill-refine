import type { HTMLAttributes, PropsWithChildren } from 'react';

import './Card.css';

type Props = PropsWithChildren<HTMLAttributes<HTMLDivElement>>;

export function Card(props: Props) {
  const { className = '', children, ...rest } = props;
  return (
    <div {...rest} className={`sr-card${className ? ` ${className}` : ''}`}>
      {children}
    </div>
  );
}
