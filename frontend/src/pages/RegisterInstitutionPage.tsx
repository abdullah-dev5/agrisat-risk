import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { signInWithPassword } from '../lib/auth';
import { LogoMark } from '../components/ui/LogoMark';
import { PILOT_CROP, PILOT_DISTRICT, PILOT_REGION } from '../lib/constants';

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
      const { error: authError } = await signInWithPassword(form.admin_email, form.admin_password);
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
      <div className="auth-brand-panel">
        <div className="auth-brand-content">
          <LogoMark size={48} />
          <h1>Partner with precision.</h1>
          <p>
            Register your institution to monitor farmer portfolios with satellite vegetation indices
            and historical baseline anomaly detection across {PILOT_REGION}.
          </p>
        </div>
        <div className="auth-brand-footer">{PILOT_CROP} · {PILOT_DISTRICT}</div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card">
          <h2>Register institution</h2>
          <p className="subtitle">Set up your organization and administrator account</p>
          <form onSubmit={handleSubmit}>
            {[
              ['name', 'Organization name *'],
              ['contact_email', 'Contact email *'],
              ['contact_phone', 'Contact phone'],
              ['admin_full_name', 'Administrator name'],
              ['admin_email', 'Administrator email *'],
              ['admin_password', 'Password * (min 8 characters)'],
            ].map(([key, label]) => (
              <div className="form-group" key={key}>
                <label htmlFor={`register-institution-${key}`}>{label}</label>
                <input
                  id={`register-institution-${key}`}
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
              {loading ? 'Creating account…' : 'Create institution'}
            </button>
          </form>
          <p className="auth-footer-link">
            Already registered? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
