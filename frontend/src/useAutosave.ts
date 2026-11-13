import { useCallback, useEffect, useRef, useState } from 'react';
import { api, message } from './api';

/** Serialize saves and preserve edits made while an earlier request is in flight. */
export function useAutosave<T extends { revision: number }>(initial: T, endpoint: string, onSaved?: (value: T) => void, serialize?: (value: T) => unknown) {
  const latest = useRef(initial);
  const baseline = useRef(JSON.stringify(initial));
  const inFlight = useRef<Promise<boolean> | null>(null);
  const callback = useRef(onSaved);
  callback.current = onSaved;
  const serializer = useRef(serialize);
  serializer.current = serialize;
  const [draft, setDraft] = useState(initial);
  const [state, setState] = useState('Saved');
  const [error, setError] = useState('');
  const blocked = useRef(false);

  const change = useCallback((update: (value: T) => T) => {
    latest.current = update(latest.current);
    setDraft(latest.current);
    setState('Unsaved');
  }, []);

  const save = useCallback(async (): Promise<boolean> => {
    if (inFlight.current) return inFlight.current;
    if (blocked.current) return false;
    const run = async () => {
      try {
        while (JSON.stringify(latest.current) !== baseline.current) {
          setState('Saving…');
          const snapshot = latest.current;
          const result = await api<T>(endpoint, 'PUT', serializer.current ? serializer.current(snapshot) : snapshot);
          baseline.current = JSON.stringify(result);
          latest.current = latest.current === snapshot ? result : { ...latest.current, revision: result.revision };
          setDraft(latest.current);
          callback.current?.(result);
        }
        setState('Saved'); setError('');
        return true;
      } catch (failure) {
        // Retrying an obsolete revision would hide a conflict. Preserve the user's text.
        if (failure instanceof Error && 'status' in failure && failure.status === 409) blocked.current = true;
        setState('Not saved'); setError(message(failure));
        return false;
      }
    };
    inFlight.current = run();
    try { return await inFlight.current; } finally { inFlight.current = null; }
  }, [endpoint]);

  useEffect(() => {
    if (JSON.stringify(draft) === baseline.current) return;
    const timer = setTimeout(() => { void save(); }, 700);
    return () => clearTimeout(timer);
  }, [draft, save]);

  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => {
      if (JSON.stringify(latest.current) !== baseline.current) { event.preventDefault(); }
    };
    window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, []);

  return { draft, change, save, state, error, conflicted: blocked.current };
}
