import { useEffect, useRef, useState } from "preact/hooks";

/** Fetches once on mount and then every `intervalMs`; call `refresh()` for an
 * immediate re-fetch (e.g. after an action). Settings pages that aren't backed
 * by a push event (unlike the WS-driven global status) use this instead. */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs = 4000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useRef(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }).current;

  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return { data, error, refresh };
}
