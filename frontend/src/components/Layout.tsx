import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { PILOT_CROP, PILOT_DISTRICT } from '../lib/constants';

export function AppLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div className="main">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;

  const links = [
    { to: '/', label: 'Dashboard' },
    { to: '/fields', label: 'Fields' },
    { to: '/fields/new', label: 'Register Field' },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>AgriSat Risk</h1>
        <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '1rem' }}>
          {PILOT_CROP} · {PILOT_DISTRICT}
        </p>
        <nav>
          {links.map((l) => (
            <Link key={l.to} to={l.to} className={location.pathname === l.to ? 'active' : ''}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div style={{ marginTop: 'auto', fontSize: '0.8rem', color: 'var(--muted)' }}>
          {user.email}
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
