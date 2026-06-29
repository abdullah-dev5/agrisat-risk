import { useEffect, useState } from 'react';
import { signOut as authSignOut } from '../lib/auth';
import { getSupabaseClient } from '../lib/supabase';

interface AuthUser {
  id: string;
  email: string;
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sb = getSupabaseClient();

    sb.auth.getSession().then(({ data }) => {
      const s = data.session;
      setUser(s?.user ? { id: s.user.id, email: s.user.email ?? '' } : null);
      setLoading(false);
    });

    const { data: sub } = sb.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ? { id: session.user.id, email: session.user.email ?? '' } : null);
      setLoading(false);
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  return {
    user,
    loading,
    signOut: () => authSignOut(),
  };
}
