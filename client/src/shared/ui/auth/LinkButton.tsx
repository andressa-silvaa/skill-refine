import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

import './AuthStyles.css';

type Props = PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>;

export function LinkButton(props: Props) {
  const { className = '', children, ...rest } = props;
  return (
    <button className={`auth-link-btn${className ? ` ${className}` : ''}`} {...rest}>
      {children}
    </button>
  );
}


