import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Only catch React rendering errors, not API/network errors
    if (error.message.includes('fetch') || 
        error.message.includes('network') || 
        error.message.includes('API') ||
        error.message.includes('HTTP')) {
      return { hasError: false };
    }
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Only log React rendering errors
    if (!error.message.includes('fetch') && 
        !error.message.includes('network') && 
        !error.message.includes('API') &&
        !error.message.includes('HTTP')) {
      console.error('ErrorBoundary caught a React error:', error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '50vh',
          color: '#00bcd4',
          textAlign: 'center',
          padding: '2rem'
        }}>
          <h2>Something went wrong</h2>
          <p>An unexpected error occurred. Please refresh the page and try again.</p>
          <button 
            onClick={() => {
              this.setState({ hasError: false, error: undefined });
              window.location.reload();
            }}
            style={{
              background: '#00bcd4',
              color: '#121212',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '8px',
              cursor: 'pointer',
              marginTop: '1rem'
            }}
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 