import './PageLoader.css';

export function PageLoader() {
  return (
    <div
      className="sr-page-loader"
      role="status"
      aria-busy="true"
      aria-live="polite"
      aria-label="Carregando página"
    >
      <div className="sr-page-loader__spinner" aria-hidden />
    </div>
  );
}
