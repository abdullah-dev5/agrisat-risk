import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useProfile } from '../hooks/useProfile';
import { LoadingScreen } from '../components/ui/LoadingScreen';

export function TeamPage() {
  const { loading, isAdmin } = useProfile();
  const [members, setMembers] = useState<Awaited<ReturnType<typeof api.listTeam>>>([]);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAdmin) {
      api.listTeam().then(setMembers).catch((e) => setError(e.message));
    }
  }, [isAdmin]);

  if (loading) return <LoadingScreen label="Loading team…" />;

  if (!isAdmin) {
    return (
      <div className="panel" style={{ padding: '2rem' }}>
        <h1>Team</h1>
        <p className="page-intro">Only institution admins can invite colleagues.</p>
      </div>
    );
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      const res = await api.inviteUser({ email, full_name: fullName || undefined });
      setMessage(res.message);
      setEmail('');
      setFullName('');
      const rows = await api.listTeam();
      setMembers(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invite failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">Institution</span>
          <h1>Team members</h1>
          <p className="page-intro">
            Invite loan officers to your institution. They receive an email to set their password.
          </p>
        </div>
      </div>

      <div className="grid-2">
        <form className="card-elevated team-invite-form" onSubmit={handleInvite}>
          <span className="section-title">Invite colleague</span>
          <div className="form-group">
            <label htmlFor="invite-email">Work email</label>
            <input
              id="invite-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="officer@bank.com"
            />
          </div>
          <div className="form-group">
            <label htmlFor="invite-name">Full name</label>
            <input
              id="invite-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Optional"
            />
          </div>
          {error && <p className="error">{error}</p>}
          {message && <p className="success-text">{message}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Sending invite…' : 'Send invitation'}
          </button>
        </form>

        <div className="panel team-list">
          <span className="section-title">Current members ({members.length})</span>
          <ul className="team-member-list">
            {members.map((m) => (
              <li key={m.id}>
                <strong>{m.full_name || 'Unnamed user'}</strong>
                <span className="team-member-role">{m.role.replace('_', ' ')}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
