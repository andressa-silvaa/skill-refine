import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Button } from '@/shared/ui';

import '@/shared/ui/sr-controls/SrControls.css';
import './RouteLoadErrorBoundary.css';

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

export class RouteLoadErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Route load error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false });
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="sr-route-load-error" role="alert">
          <div className="sr-route-load-error__card">
            <div className="sr-route-load-error__icon" aria-hidden>
              <i className="fa-solid fa-circle-exclamation" />
            </div>
            <h1 className="sr-route-load-error__title">Erro ao carregar</h1>
            <p className="sr-route-load-error__message">
              Não foi possível carregar a página. Verifique sua conexão e tente novamente.
            </p>
            <Button variant="primary" onClick={this.handleRetry}>
              <i className="fa-solid fa-rotate-right" aria-hidden />
              Tentar novamente
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
