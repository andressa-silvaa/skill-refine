import type { ButtonHTMLAttributes, ReactNode } from 'react';

import './IconButton.css';

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> & {
  children: ReactNode;
  isActive?: boolean;
};

export function IconButton(props: Props) {
  const { className = '', isActive = false, type = 'button', children, ...rest } = props;

  return (
    <button
      {...rest}
      type={type}
      className={`sr-icon-btn${isActive ? ' is-active' : ''}${className ? ` ${className}` : ''}`}
    >
      {children}
    </button>
  );
}


