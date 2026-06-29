import { getSupabaseClient } from './supabase';

export async function signInWithPassword(email: string, password: string) {
  return getSupabaseClient().auth.signInWithPassword({ email, password });
}

export async function signOut() {
  await getSupabaseClient().auth.signOut();
}
