import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log unexpected UI error safely to console without exposing secrets
    console.error('VectorHire UI ErrorBoundary caught an error:', error?.message, errorInfo?.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (typeof this.props.onReset === 'function') {
      this.props.onReset();
    } else {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-[#FECDD3] shadow-elevated p-6 sm:p-8 text-center space-y-4 animate-in fade-in">
            <div className="w-12 h-12 rounded-2xl bg-[#FFF1F2] border border-[#FECDD3] flex items-center justify-center text-[#E11D48] mx-auto shadow-sm">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h2 className="font-sans text-lg font-bold text-[#0F172A]">
                Something went wrong
              </h2>
              <p className="text-xs text-[#475569] leading-relaxed">
                An unexpected application rendering error occurred. Your entered job data and candidate files remain preserved in your session where possible.
              </p>
            </div>

            <div className="pt-2">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-[#0369A1] to-[#0284C7] hover:brightness-105 transition-all shadow-sm active:scale-[0.98]"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Recover & Reload View</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
