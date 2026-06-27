import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { supabase } from '../lib/supabase';

export function RegisterInstitutionPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    contact_email: '',
    contact_phone: '',
    admin_full_name: '',
    admin_email: '',
    admin_password: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function update(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.registerInstitution(form);
      const { error: authError } = await supabase.auth.signInWithPassword({
        email: form.admin_email,
        password: form.admin_password,
      });
      if (authError) throw authError;
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2 style={{ marginBottom: '0.5rem' }}>Register Institution</h2>
        <p style={{ color: 'var(--muted)', marginBottom: '1.5rem' }}>Create your partner institution account (FR-1.1)</p>
        <form onSubmit={handleSubmit}>
          {[
            ['name', 'Organization name *'],
            ['contact_email', 'Contact email *'],
            ['contact_phone', 'Contact phone'],
            ['admin_full_name', 'Administrator name'],
            ['admin_email', 'Administrator email *'],
            ['admin_password', 'Administrator password * (min 8 chars)'],
          ].map(([key, label]) => (
            <div className="form-group" key={key}>
              <label>{label}</label>
              <input
                type={key.includes('password') ? 'password' : key.includes('email') ? 'email' : 'text'}
                value={form[key as keyof typeof form]}
                onChange={(e) => update(key, e.target.value)}
                required={label.includes('*')}
                minLength={key === 'admin_password' ? 8 : undefined}
              />
            </div>
          ))}
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading} style={{ width: '100%' }}>
            {loading ? 'Creating...' : 'Create Institution'}
          </button>
        </form>
        <p style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
