import { useState } from "react";
import "./AuthPages.css";

/**
 * Phase 1 (Real User Authentication) — "Path A" entry point (section 19):
 * Landing -> Login/Register -> authenticated application. Deliberately
 * simple: on success this stops at "you are logged in" (see App.jsx) —
 * it does not start the questionnaire or a kiosk session, both of which
 * are out of scope for this phase.
 */
export default function LoginPage({ onLogin, onSwitchToRegister, onBack }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(err.status === 401 ? "Incorrect username or password." : err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-page__card">
        <h1>Log in</h1>
        <p>Sign in to your AbilityOS account.</p>

        {error && (
          <div className="auth-page__error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="auth-page__field">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="auth-page__field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn--primary auth-page__submit" disabled={submitting}>
            {submitting ? "Logging in…" : "Log in"}
          </button>
        </form>

        <p className="auth-page__switch">
          Don't have an account?{" "}
          <button type="button" onClick={onSwitchToRegister}>
            Create one
          </button>
        </p>

        {onBack && (
          <p className="auth-page__switch">
            <button type="button" onClick={onBack}>
              ← Back
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
