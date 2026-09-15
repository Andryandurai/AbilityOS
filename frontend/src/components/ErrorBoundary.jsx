import { Component } from "react";

/**
 * Application-level error boundary (Phase 8 section 31). If a component
 * crashes, the person sees a plain recovery message instead of a blank
 * page — this never shows a stack trace to the normal user; that detail
 * only ever goes to the console for a developer to find.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("AbilityOS crashed:", error, info);
  }

  handleReturn = () => {
    this.setState({ hasError: false });
    window.location.href = "/";
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="app-shell">
        <div className="card" role="alert" style={{ margin: "var(--space-6) auto", maxWidth: 480 }}>
          <h2>Something went wrong.</h2>
          <p>AbilityOS hit an unexpected error. Your data is safe — nothing was lost.</p>
          <button type="button" className="btn btn--primary" onClick={this.handleReturn}>
            Return to AbilityOS
          </button>
        </div>
      </div>
    );
  }
}
