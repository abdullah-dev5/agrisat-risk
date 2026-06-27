import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LogoMark } from './ui/LogoMark';
import { LoadingScreen } from './ui/LoadingScreen';
import { PILOT_CROP, PILOT_DISTRICT } from '../lib/constants';

export function AppLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;

  const links = [
    { to: '/', label: 'Overview', match: (p: string) => p === '/' },
    { to: '/fields', label: 'Portfolio', match: (p: string) => p === '/fields' || (p.startsWith('/fields/') && p !== '/fields/new') },
    { to: '/fields/new', label: 'Register', match: (p: string) => p === '/fields/new' },
  ];

  return (
    <div className="app-shell">
      <header className="site-header">
        <Link to="/" className="brand">
          <LogoMark size={36} />
          <div className="brand-text">
            <span className="brand-name">AgriSat Risk</span>
            <span className="brand-meta">{PILOT_CROP} · {PILOT_DISTRICT}</span>
          </div>
        </Link>

        <nav className="site-nav" aria-label="Main">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={l.match(location.pathname) ? 'active' : ''}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="header-actions">
          <span className="user-chip" title={user.email ?? ''}>{user.email}</span>
          <Link to="/fields/new" className="btn btn-wheat">+ Register field</Link>
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
