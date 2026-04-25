import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DEFAULT_FORM = {
  pseudo: '',
  email: '',
  password: '',
};

function LoginPage() {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState(DEFAULT_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { login, signup, loginDemo } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const redirectTo = useMemo(() => location.state?.from || '/dashboard', [location.state]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');

    try {
      if (mode === 'login') {
        await login(form);
      } else {
        await signup(form);
      }

      navigate(redirectTo, { replace: true });
    } catch (requestError) {
      setError(requestError.message || 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  function onDemoMode() {
    loginDemo();
    navigate('/dashboard', { replace: true });
  }

  const showPseudo = mode === 'signup';

  return (
    <main className="auth-wrap">
      <section className="auth-card">
      <h1 className="auth-title">{mode === 'login' ? 'GeoSeer Login' : 'Create account'}</h1>
      <p className="auth-subtitle">
        Enter your credentials to access the image-to-location workspace.
      </p>

      <form className="auth-form" onSubmit={onSubmit}>
        {showPseudo ? (
          <label htmlFor="pseudo">
            Pseudo
            <input
              autoComplete="nickname"
              id="pseudo"
              onChange={(event) => updateField('pseudo', event.target.value)}
              required={showPseudo}
              value={form.pseudo}
            />
          </label>
        ) : null}

        <label htmlFor="email">
          Email
          <input
            autoComplete="email"
            id="email"
            onChange={(event) => updateField('email', event.target.value)}
            required
            type="email"
            value={form.email}
          />
        </label>

        <label htmlFor="password">
          Password
          <input
            autoComplete="current-password"
            id="password"
            minLength={6}
            onChange={(event) => updateField('password', event.target.value)}
            required
            type="password"
            value={form.password}
          />
        </label>

        {error ? <p className="auth-error">{error}</p> : null}

        <button className="auth-primary" disabled={busy} type="submit">
          {busy ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
        </button>
      </form>

      <button
        className="auth-secondary"
        onClick={() => setMode((prev) => (prev === 'login' ? 'signup' : 'login'))}
        type="button"
      >
        {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Login'}
      </button>

      <button className="auth-secondary" onClick={onDemoMode} type="button">
        Continue in demo mode
      </button>
      </section>
    </main>
  );
}

export default LoginPage;
