import React from 'react';

export default class FileErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error(`[Error in ${this.props.fileName}]`, error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="absolute inset-0 flex items-center justify-center bg-red-950/80 p-6 z-50 rounded-xl m-4 border border-red-500/50 backdrop-blur-md">
          <div className="text-white font-mono max-w-full overflow-auto">
            <h2 className="text-xl font-bold text-red-400 mb-2">💥 Crash Detected</h2>
            <p className="text-sm text-gray-300 mb-4">
              <span className="font-bold text-white">File:</span> {this.props.fileName}
            </p>
            <div className="bg-black/50 p-4 rounded-lg overflow-x-auto">
              <p className="text-red-300 font-semibold mb-2">{this.state.error?.toString()}</p>
              <pre className="text-xs text-gray-400 whitespace-pre-wrap leading-relaxed">
                {this.state.errorInfo?.componentStack}
              </pre>
            </div>
            <button 
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-red-500/20 hover:bg-red-500/40 text-red-100 rounded-md transition-colors border border-red-500/30"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
