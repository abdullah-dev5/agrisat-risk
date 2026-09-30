import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { FieldProcessingStatus } from '../types';

const POLL_MS = 3000;
const MAX_POLLS = 120; // 6 minutes

export function useFieldProcessing(
  fieldId: string | undefined,
  initialStatus?: string | null,
  // Fires whenever polling stops for ANY reason (ready, failed, max-polls
  // timeout, or a poll request itself erroring) -- not just success. The
  // caller's `detail.processing_status` is otherwise a stale snapshot from
  // whenever it was first fetched, so without this, isAnalyzing-style
  // checks in the caller can stay stuck on "processing" forever even after
  // the job genuinely finished (or failed) on the server, if a single poll
  // request happens to hit a transient network error. Found live: a real
  // field finished successfully in ~80s, but one transient "server
  // disconnected" poll error froze the UI on "processing" for the rest of
  // a 4-minute wait, since nothing ever re-fetched the field's real status.
  onSettled?: () => void,
) {
  const [status, setStatus] = useState<FieldProcessingStatus | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [polling, setPolling] = useState(
    initialStatus === 'processing' || !initialStatus,
  );
  const polls = useRef(0);
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;

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
        setPollError(null);
        polls.current += 1;
        if (s.status === 'ready' || s.status === 'idle') {
          setPolling(false);
          onSettledRef.current?.();
        } else if (s.status === 'failed') {
          setPolling(false);
          onSettledRef.current?.();
        } else if (polls.current >= MAX_POLLS) {
          setPolling(false);
          onSettledRef.current?.();
        }
      } catch (err) {
        if (!cancelled) {
          setPolling(false);
          setPollError(
            err instanceof Error
              ? err.message
              : 'Lost connection while checking analysis status.',
          );
          // A single failed poll request is often transient (a network
          // blip, not the job itself failing) -- refresh the field detail
          // once so the UI reflects whatever the server's real state
          // actually is, instead of freezing on a stale "processing" view.
          onSettledRef.current?.();
        }
      }
    };

    tick();
    const id = window.setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [fieldId, polling]);

  return {
    status,
    polling,
    pollError,
    refresh,
    startPolling: () => {
      setPollError(null);
      setPolling(true);
    },
    // For the caller to call once it has independently confirmed a
    // definitive (non-"processing") status after a poll error settled --
    // otherwise a transient error's message would keep showing even once
    // the real outcome (success or failure) is known and displayed.
    clearPollError: () => setPollError(null),
  };
}
