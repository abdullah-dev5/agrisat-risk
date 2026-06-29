import { getAccessToken } from './supabase';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
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
}

export const api = {
  getMe: () => apiFetch<import('../types').Profile>('/api/v1/auth/me'),
  listFields: () => apiFetch<import('../types').Field[]>('/api/v1/fields'),
  getFieldDetail: (id: string) => apiFetch<import('../types').FieldDetail>(`/api/v1/fields/${id}/detail`),
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
