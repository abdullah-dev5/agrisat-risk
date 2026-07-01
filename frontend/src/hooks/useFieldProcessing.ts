import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { FieldProcessingStatus } from '../types';

const POLL_MS = 3000;
const MAX_POLLS = 120; // 6 minutes

export function useFieldProcessing(
  fieldId: string | undefined,
  initialStatus?: string | null,
  onReady?: () => void,
) {
  const [status, setStatus] = useState<FieldProcessingStatus | null>(null);
  const [polling, setPolling] = useState(
    initialStatus === 'processing' || !initialStatus,
  );
  const polls = useRef(0);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  const refresh = useCallback(async () => {
    if (!fieldId) return null;
    const s = await api.getFieldProcessing(fieldId);
    setStatus(s);
    return s;
  }, [fieldId]);

  useEffect(() => {
    if (!fieldId || !polling) return;

    let cancelled = false;
    const tick = async () => {
      try {
        const s = await api.getFieldProcessing(fieldId);
        if (cancelled) return;
        setStatus(s);
        polls.current += 1;
        if (s.status === 'ready' || s.status === 'idle') {
          setPolling(false);
          onReadyRef.current?.();
        } else if (s.status === 'failed') {
          setPolling(false);
        } else if (polls.current >= MAX_POLLS) {
          setPolling(false);
        }
      } catch {
        if (!cancelled) setPolling(false);
      }
    };

    tick();
    const id = window.setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [fieldId, polling]);

  return { status, polling, refresh, startPolling: () => setPolling(true) };
}
