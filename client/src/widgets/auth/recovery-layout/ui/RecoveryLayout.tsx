import type { CSSProperties, PropsWithChildren, ReactNode } from 'react';

import './RecoveryLayout.css';

type Props = PropsWithChildren<{
  title: string;
  subtitle?: string;
  footer?: ReactNode;
  onBack?: () => void;
  className?: string;
}>;

export function RecoveryLayout(props: Props) {
  const { title, subtitle, children, footer, onBack, className = '' } = props;

  const bgSrc = `${process.env.PUBLIC_URL}/background-reset.png`;
  const style = { '--recovery-bg-image': `url(${bgSrc})` } as CSSProperties;

  return (
    <div className="recovery-shell" style={style}>
      <div className="recovery-card">
        {onBack && (
          <button type="button" className="recovery-back" onClick={onBack}>
            ‹ Voltar
          </button>
        )}

        <header className="recovery-header">
          <h1 className="recovery-title">{title}</h1>
          {subtitle ? <p className="recovery-subtitle">{subtitle}</p> : null}
        </header>

        <div className={`recovery-body${className ? ` ${className}` : ''}`}>{children}</div>

        {footer ? <footer className="recovery-footer">{footer}</footer> : null}
      </div>
    </div>
  );
}


