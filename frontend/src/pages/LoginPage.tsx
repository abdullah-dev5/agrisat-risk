import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signInWithPassword } from '../lib/auth';
import { LogoMark } from '../components/ui/LogoMark';
import { PILOT_CROP, PILOT_DISTRICT, PILOT_REGION } from '../lib/constants';

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    const { error: authError } = await signInWithPassword(email, password);
    setLoading(false);
    if (authError) {
      setError(authError.message);
      return;
    }
    navigate('/');
  }

  return (
    <div className="auth-page">
      <div className="auth-brand-panel">
        <div className="auth-brand-content">
          <LogoMark size={48} />
          <h1>Crop risk intelligence, from orbit.</h1>
          <p>
            Monitor registered field boundaries with fused satellite vegetation signals —
            built for lenders and insurers serving {PILOT_REGION}.
          </p>
        </div>
        <div className="auth-brand-footer">
          {PILOT_CROP} pilot · {PILOT_DISTRICT} · decision-support platform
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card">
          <h2>Sign in</h2>
          <p className="subtitle">Access your institution&apos;s risk dashboard</p>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="login-email">Email</label>
              <input id="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            </div>
            <div className="form-group">
              <label htmlFor="login-password">Password</label>
              <input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
            </div>
            {error && <p className="error">{error}</p>}
            <button type="submit" disabled={loading} style={{ width: '100%', marginTop: '0.5rem' }}>
              {loading ? 'Signing in…' : 'Continue'}
            </button>
          </form>
          <p className="auth-footer-link">
            New institution? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
