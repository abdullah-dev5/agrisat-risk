import { getAccessToken } from './supabase';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export const API_TIMEOUT = {
  default: 30_000,
  imagery: 180_000,
  report: 120_000,
  processing: 15_000,
} as const;

async function apiFetch<T>(path: string, options: RequestInit = {}, timeoutMs: number = API_TIMEOUT.default): Promise<T> {
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
    if (res.status === 204) return undefined as T;
    return res.json();
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error(
        'Request timed out. Satellite analysis runs in the background — check field status or try again.',
      );
    }
    if (err instanceof TypeError) {
      throw new Error(
        'Could not reach the API — ensure the backend is running and refresh the page.',
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
  getFieldProcessing: (id: string) =>
    apiFetch<import('../types').FieldProcessingStatus>(
      `/api/v1/fields/${id}/processing`,
      {},
      API_TIMEOUT.processing,
    ),
  getFieldImagery: (id: string) =>
    apiFetch<import('../types').FieldImagery>(`/api/v1/fields/${id}/imagery`, {}, API_TIMEOUT.imagery),
  createField: (body: unknown) =>
    apiFetch<import('../types').Field>('/api/v1/fields', { method: 'POST', body: JSON.stringify(body) }),
  reprocessField: (id: string) =>
    apiFetch<{ message: string; status: string }>(
      `/api/v1/fields/${id}/reprocess`,
      { method: 'POST' },
      API_TIMEOUT.processing,
    ),
  portfolioSummary: () => apiFetch<import('../types').PortfolioSummary>('/api/v1/reports/portfolio/summary'),
  registerInstitution: (body: unknown, registrationSecret?: string) =>
    apiFetch<{ id: string; name: string }>('/api/v1/auth/register-institution', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: registrationSecret ? { 'X-Registration-Secret': registrationSecret } : {},
    }),
};

export function reportUrl(path: string): string {
  return `${API_URL}${path}`;
}

export async function downloadReport(path: string, filename: string): Promise<void> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT.report);

  try {
    const res = await fetch(`${API_URL}${path}`, { headers, signal: controller.signal });
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
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Report download timed out — try again.');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function waitForFieldProcessing(
  fieldId: string,
  onProgress?: (status: import('../types').FieldProcessingStatus) => void,
): Promise<import('../types').FieldProcessingStatus> {
  const maxAttempts = 120;
  for (let i = 0; i < maxAttempts; i += 1) {
    const s = await api.getFieldProcessing(fieldId);
    onProgress?.(s);
    if (s.status === 'ready' || s.status === 'idle') return s;
    if (s.status === 'failed') throw new Error(s.error || 'Satellite analysis failed');
    await new Promise((r) => setTimeout(r, 3000));
  }
  throw new Error('Analysis is taking longer than expected. Open the field page to check status.');
}
