import { useState } from 'react';
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useProfile } from '../hooks/useProfile';
import { LogoMark } from './ui/LogoMark';
import { LoadingScreen } from './ui/LoadingScreen';
import { PILOT_CROP, PILOT_DISTRICT } from '../lib/constants';

export function AppLayout() {
  const { user, loading, signOut } = useAuth();
  const { profile, isAdmin } = useProfile();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleSignOut() {
    await signOut();
    navigate('/login');
  }

  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;

  const links = [
    { to: '/', label: 'Overview', match: (p: string) => p === '/' },
    { to: '/fields', label: 'Portfolio', match: (p: string) => p === '/fields' || (p.startsWith('/fields/') && p !== '/fields/new') },
    { to: '/fields/new', label: 'Register', match: (p: string) => p === '/fields/new' },
    { to: '/guide', label: 'Guide', match: (p: string) => p === '/guide' },
    ...(isAdmin ? [{ to: '/team', label: 'Team', match: (p: string) => p === '/team' }] : []),
  ];

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Skip to main content</a>

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
          <span className="user-chip" title={user.email ?? ''}>
            {profile?.full_name || user.email}
            {profile?.role && <span className="user-role">{profile.role.replace('_', ' ')}</span>}
          </span>
          <button type="button" className="btn secondary btn-compact" onClick={handleSignOut}>
            Sign out
          </button>
          <Link to="/fields/new" className="btn btn-wheat header-register">+ Register field</Link>
          <button
            type="button"
            className="mobile-menu-btn"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            onClick={() => setMenuOpen((v) => !v)}
          >
            Menu
          </button>
        </div>
      </header>

      {menuOpen && (
        <nav id="mobile-nav" className="mobile-nav" aria-label="Mobile">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={l.match(location.pathname) ? 'active' : ''}
              onClick={() => setMenuOpen(false)}
            >
              {l.label}
            </Link>
          ))}
          <button type="button" className="mobile-nav-signout" onClick={handleSignOut}>
            Sign out
          </button>
        </nav>
      )}

      <main id="main-content" className="main">
        <Outlet />
      </main>
    </div>
  );
}
