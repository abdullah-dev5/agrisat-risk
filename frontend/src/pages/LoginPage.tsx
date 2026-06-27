import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
    if (authError) {
      setError(authError.message);
      return;
    }
    navigate('/');
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2 style={{ marginBottom: '0.5rem' }}>AgriSat Risk</h2>
        <p style={{ color: 'var(--muted)', marginBottom: '1.5rem' }}>Sign in to your institution account</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" style={{ width: '100%', marginTop: '0.5rem' }}>Sign In</button>
        </form>
        <p style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
          New institution? <Link to="/register">Register here</Link>
        </p>
      </div>
    </div>
  );
}
