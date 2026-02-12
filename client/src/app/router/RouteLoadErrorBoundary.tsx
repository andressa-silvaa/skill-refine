import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Button } from '@/shared/ui';

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
          <p className="sr-route-load-error__message">
            Não foi possível carregar a página. Tente novamente.
          </p>
          <Button variant="primary" onClick={this.handleRetry}>
            Tentar novamente
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
