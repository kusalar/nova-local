import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[NOVA ErrorBoundary Caught]:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-nova-dark p-6 select-none scanlines text-slate-100">
          <div className="hud-panel max-w-lg w-full p-6 border-red-500/40 shadow-[0_0_30px_rgba(239,68,68,0.25)] space-y-4">
            <div className="flex items-center gap-3 border-b border-nova-border/80 pb-3">
              <div className="w-10 h-10 rounded-lg bg-red-500/20 border border-red-500/50 flex items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-red-400 animate-pulse" />
              </div>
              <div>
                <h2 className="font-display font-bold text-sm text-white tracking-wider uppercase">
                  NOVA Desktop Runtime Guard
                </h2>
                <p className="text-xs text-slate-400 font-mono">
                  UI recovery handler intercepted an unhandled error
                </p>
              </div>
            </div>

            <div className="p-3 bg-red-950/20 border border-red-500/30 rounded text-xs text-red-200 font-mono space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-red-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                {this.state.error?.name || 'Runtime Error'}:
              </div>
              <p className="break-all">{this.state.error?.message || 'Unknown runtime error'}</p>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={this.handleReload}
                className="flex items-center gap-2 px-4 py-2 rounded bg-nova-cyan hover:bg-nova-cyan/90 text-black font-display font-bold text-xs uppercase tracking-wider transition-all shadow-nova-cyan"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reload Application
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
