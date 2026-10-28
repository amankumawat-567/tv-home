import { useEffect, useState } from "preact/hooks";

export function Clock({ className }: { className?: string }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 15_000);
    return () => clearInterval(id);
  }, []);
  const label = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return <span className={className}>{label}</span>;
}

export function greeting(now = new Date()): string {
  const h = now.getHours();
  if (h < 5) return "Good night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function longDate(now = new Date()): string {
  return now.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
}
