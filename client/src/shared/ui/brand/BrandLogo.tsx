import type { HTMLAttributes } from 'react';

import './BrandLogo.css';

type Props = HTMLAttributes<HTMLDivElement> & {
  label?: string;
  showLabel?: boolean;
};

export function BrandLogo(props: Props) {
  const { className = '', label = 'Skill Refine', showLabel = true, ...rest } = props;

  return (
    <div {...rest} className={`sr-brand${className ? ` ${className}` : ''}`}>
      {showLabel ? <span className="sr-brand__label">{label}</span> : null}
    </div>
  );
}
