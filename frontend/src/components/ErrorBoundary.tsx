import type { ErrorInfo, ReactNode } from "react";
import { Component } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

/** حدود خطأ عام (P3-85) — تعرض للمكونات التي ترمي أثناء العرض بدلاً
   من إتلاف التطبيق بالكامل. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary أمسك استثناء:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="p-6 text-center">
            <h2 className="mb-2 text-lg font-bold text-red-700">
              حدث خطأ غير متوقع
            </h2>
            <p className="text-sm text-slate-600">{this.state.error.message}</p>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-3 rounded-lg bg-slate-200 px-3 py-1 text-sm hover:bg-slate-300"
            >
              إعادة المحاولة
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
