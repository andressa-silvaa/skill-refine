import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

import './AuthStyles.css';

type Props = PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>;

export function PrimaryButton(props: Props) {
  const { className = '', children, ...rest } = props;
  return (
    <button className={`auth-btn${className ? ` ${className}` : ''}`} {...rest}>
      {children}
    </button>
  );
}
