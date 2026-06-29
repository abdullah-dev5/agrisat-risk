import { useCallback, useEffect, useRef, useState } from 'react';
import type { Map } from 'leaflet';

export interface MapTileLoadingState {
  loading: boolean;
  percent: number;
}

export function useMapTileLoading(map: Map): MapTileLoadingState {
  const [loading, setLoading] = useState(false);
  const [percent, setPercent] = useState(0);
  const stats = useRef({ pending: 0, done: 0 });
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHideTimer = useCallback(() => {
    if (hideTimer.current) {
      clearTimeout(hideTimer.current);
      hideTimer.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearHideTimer();
    stats.current = { pending: 0, done: 0 };
    setLoading(false);
    setPercent(0);
  }, [clearHideTimer]);

  const syncProgress = useCallback(() => {
    const { pending, done } = stats.current;
    if (pending === 0) return;

    const pct = Math.min(100, Math.round((done / pending) * 100));
    setPercent(pct);
    setLoading(true);

    if (done >= pending) {
      setPercent(100);
      clearHideTimer();
      hideTimer.current = setTimeout(() => {
        setLoading(false);
        stats.current = { pending: 0, done: 0 };
      }, 700);
    }
  }, [clearHideTimer]);

  useEffect(() => {
    const onStart = () => {
      stats.current.pending += 1;
      syncProgress();
    };

    const onFinish = () => {
      stats.current.done += 1;
      syncProgress();
    };

    map.on('movestart', reset);
    map.on('zoomstart', reset);
    map.on('tileloadstart', onStart);
    map.on('tileload', onFinish);
    map.on('tileerror', onFinish);

    return () => {
      clearHideTimer();
      map.off('movestart', reset);
      map.off('zoomstart', reset);
      map.off('tileloadstart', onStart);
      map.off('tileload', onFinish);
      map.off('tileerror', onFinish);
    };
  }, [map, reset, syncProgress, clearHideTimer]);

  return { loading, percent };
}
