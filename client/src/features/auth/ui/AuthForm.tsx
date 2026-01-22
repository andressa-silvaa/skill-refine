import type { FormHTMLAttributes, PropsWithChildren } from 'react';

import './AuthStyles.css';

type Props = PropsWithChildren<FormHTMLAttributes<HTMLFormElement>>;

export function AuthForm(props: Props) {
  const { className = '', children, ...rest } = props;
  return (
    <form className={`auth-form${className ? ` ${className}` : ''}`} {...rest}>
      {children}
    </form>
  );
}
