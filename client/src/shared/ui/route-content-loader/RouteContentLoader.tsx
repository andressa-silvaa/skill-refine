import './RouteContentLoader.css';

/** Shown inside AppShell while a lazy route chunk loads — inherits theme, no full-viewport flash. */
export function RouteContentLoader() {
  return (
    <div
      className="sr-route-content-loader"
      role="status"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="sr-route-content-loader__spinner" aria-hidden />
    </div>
  );
}
