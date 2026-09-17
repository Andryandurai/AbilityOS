import { useState } from "react";
import "./AuthPages.css";

/**
 * Phase 1 (Real User Authentication). On success, hands off to login
 * (section 15's preferred flow: Register -> Login) rather than logging the
 * person in directly with a second, separate mechanism — one real path
 * into an authenticated session, not two.
 */
export default function RegisterPage({ onRegister, onSwitchToLogin }) {
  const [form, setForm] = useState({
    username: "",
    email: "",
    displayName: "",
    password: "",
    passwordConfirm: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  const setField = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (form.password !== form.passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await onRegister({
        username: form.username,
        email: form.email,
        display_name: form.displayName,
        password: form.password,
        password_confirm: form.passwordConfirm,
      });
      setDone(true);
    } catch (err) {
      const detail = err.body;
      if (detail && typeof detail === "object") {
        const firstMessage = Object.values(detail).flat()[0];
        setError(typeof firstMessage === "string" ? firstMessage : err.message);
      } else {
        setError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="auth-page">
        <div className="card auth-page__card">
          <h1>Account created</h1>
          <p>Your AbilityOS account is ready. Log in to continue.</p>
          <button type="button" className="btn btn--primary auth-page__submit" onClick={onSwitchToLogin}>
            Go to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="card auth-page__card">
        <h1>Create your account</h1>
        <p>This creates a real AbilityOS account — separate from the demo personas.</p>

        {error && (
          <div className="auth-page__error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="auth-page__field">
            <label htmlFor="register-display-name">Display name</label>
            <input
              id="register-display-name"
              name="displayName"
              type="text"
              autoComplete="name"
              value={form.displayName}
              onChange={setField("displayName")}
            />
          </div>

          <div className="auth-page__field">
            <label htmlFor="register-username">Username</label>
            <input
              id="register-username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={form.username}
              onChange={setField("username")}
            />
          </div>

          <div className="auth-page__field">
            <label htmlFor="register-email">Email</label>
            <input
              id="register-email"
              name="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={setField("email")}
            />
          </div>

          <div className="auth-page__field">
            <label htmlFor="register-password">Password</label>
            <input
              id="register-password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              value={form.password}
              onChange={setField("password")}
            />
          </div>

          <div className="auth-page__field">
            <label htmlFor="register-password-confirm">Confirm password</label>
            <input
              id="register-password-confirm"
              name="passwordConfirm"
              type="password"
              autoComplete="new-password"
              required
              value={form.passwordConfirm}
              onChange={setField("passwordConfirm")}
            />
          </div>

          <button type="submit" className="btn btn--primary auth-page__submit" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-page__switch">
          Already have an account?{" "}
          <button type="button" onClick={onSwitchToLogin}>
            Log in
          </button>
        </p>
      </div>
    </div>
  );
}
