import { getAccessToken } from './supabase';

const API_URL = import.meta.env.VITE_API_URL ?? '';

async function apiFetch<T>(path: string, options: RequestInit = {}, timeoutMs = 60_000): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = err.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || 'Request failed'
            : 'Request failed';
      throw new Error(message);
    }
    return res.json();
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Request timed out — GEE imagery can take up to 2 minutes on first load.');
    }
    if (err instanceof TypeError) {
      throw new Error(
        'Could not reach the API — ensure the backend is running on port 8000 and refresh the page.',
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  getMe: () => apiFetch<import('../types').Profile>('/api/v1/auth/me'),
  listTeam: () => apiFetch<import('../types').TeamMember[]>('/api/v1/auth/team'),
  inviteUser: (body: { email: string; full_name?: string; role?: string }) =>
    apiFetch<{ message: string; user_id: string }>('/api/v1/auth/invite', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listFields: () => apiFetch<import('../types').Field[]>('/api/v1/fields'),
  getFieldDetail: (id: string) => apiFetch<import('../types').FieldDetail>(`/api/v1/fields/${id}/detail`),
  getFieldImagery: (id: string) =>
    apiFetch<import('../types').FieldImagery>(`/api/v1/fields/${id}/imagery`, {}, 120_000),
  createField: (body: unknown) =>
    apiFetch<import('../types').Field>('/api/v1/fields', { method: 'POST', body: JSON.stringify(body) }),
  reprocessField: (id: string) =>
    apiFetch<{ message: string }>(`/api/v1/fields/${id}/reprocess`, { method: 'POST' }),
  portfolioSummary: () => apiFetch<import('../types').PortfolioSummary>('/api/v1/reports/portfolio/summary'),
  registerInstitution: (body: unknown) =>
    apiFetch<{ id: string; name: string }>('/api/v1/auth/register-institution', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

export function reportUrl(path: string): string {
  return `${API_URL}${path}`;
}

export async function downloadReport(path: string, filename: string): Promise<void> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Download failed');
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
