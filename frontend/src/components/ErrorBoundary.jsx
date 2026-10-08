import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen w-screen items-center justify-center bg-bg text-textMain font-mono text-sm">
          <div className="bg-panel border border-accentFail p-6 max-w-3xl w-full shadow-2xl">
            <h1 className="text-xl font-bold text-accentFail mb-4">FATAL ERROR</h1>
            <p className="mb-4">The application crashed while rendering. See details below:</p>
            <div className="bg-[#0A0A0A] border border-border p-4 overflow-auto max-h-96">
              <div className="text-accentFail font-bold mb-2">{this.state.error && this.state.error.toString()}</div>
              <pre className="text-textMuted text-xs whitespace-pre-wrap">
                {this.state.errorInfo && this.state.errorInfo.componentStack}
              </pre>
            </div>
            <button 
              className="mt-4 bg-border hover:bg-textMuted px-4 py-2 font-bold"
              onClick={() => window.location.reload()}
            >
              RELOAD PAGE
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
