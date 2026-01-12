import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

import './Button.css';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

type Props = PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>> & {
  variant?: Variant;
};

export function Button(props: Props) {
  const { className = '', variant = 'secondary', type = 'button', children, ...rest } = props;
  return (
    <button
      {...rest}
      type={type}
      className={`sr-btn sr-btn--${variant}${className ? ` ${className}` : ''}`}
    >
      {children}
    </button>
  );
}
