import './RecoveryLayout.css';

export default function RecoveryLayout({
  title,
  subtitle,
  children,
  footer,
  onBack,
  className = '',
}) {
  const bgSrc = `${process.env.PUBLIC_URL}/background-reset.png`;

  return (
    <div
      className="recovery-shell"
      style={{
        '--recovery-bg-image': `url(${bgSrc})`,
      }}
    >

      <div className="recovery-card">
        {onBack && (
          <button type="button" className="recovery-back" onClick={onBack}>
            ‹ Voltar
          </button>
        )}

        <header className="recovery-header">
          <h1 className="recovery-title">{title}</h1>
          {subtitle && <p className="recovery-subtitle">{subtitle}</p>}
        </header>

        <div className={`recovery-body${className ? ` ${className}` : ''}`}>
          {children}
        </div>

        {footer && <footer className="recovery-footer">{footer}</footer>}
      </div>
    </div>
  );
}
