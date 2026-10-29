// Small hand-rolled glyphs standing in for the PRD's choice of bundled Material
// Symbols SVGs (Apache 2.0) — same shapes/meaning, no external asset pipeline
// needed to get the UI running. Swap for the real Material Symbols files later
// by dropping them in and keeping these component names.
import type { JSX } from "preact";

type IconProps = { size?: number; className?: string };

function base(children: JSX.Element | JSX.Element[], { size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      {children}
    </svg>
  );
}

export function WifiIcon({ level, className, size }: { level: number | "off" } & IconProps) {
  const bars = [0, 1, 2, 3].map((i) => {
    const h = 4 + i * 4;
    const on = level !== "off" && level >= i + 1;
    return (
      <rect
        key={i}
        x={3 + i * 5}
        y={20 - h}
        width={3.5}
        height={h}
        rx={1}
        fill={on ? "currentColor" : "var(--text-muted)"}
        opacity={level === "off" ? 0.35 : 1}
      />
    );
  });
  return base(
    level === "off" ? [...bars, <line key="x" x1={2} y1={2} x2={22} y2={22} stroke="currentColor" strokeWidth={1.6} />] : bars,
    { size, className },
  );
}

export function BluetoothIcon({ state, className, size }: { state: "off" | "on" | "connected" } & IconProps) {
  const color = state === "off" ? "var(--text-muted)" : state === "connected" ? "var(--good)" : "currentColor";
  return base(
    <path
      d="M7 7l10 10-5 5V2l5 5L7 17"
      stroke={color}
      strokeWidth={1.8}
      strokeLinejoin="round"
      strokeLinecap="round"
      fill="none"
    />,
    { size, className },
  );
}

export function VolumeIcon({ level, muted, className, size }: { level: number; muted: boolean } & IconProps) {
  const loud = !muted && level > 50;
  return base(
    [
      <path key="cone" d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />,
      !muted && (
        <path
          key="wave"
          d={loud ? "M16 8a6 6 0 010 8M18.5 5.5a10 10 0 010 13" : "M16 9.5a3 3 0 010 5"}
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          fill="none"
        />
      ),
      muted && <line key="x" x1={15} y1={8} x2={21} y2={16} stroke="var(--bad)" strokeWidth={1.8} strokeLinecap="round" />,
      muted && <line key="x2" x1={21} y1={8} x2={15} y2={16} stroke="var(--bad)" strokeWidth={1.8} strokeLinecap="round" />,
    ].filter(Boolean) as JSX.Element[],
    { size, className },
  );
}

export function GearIcon(props: IconProps) {
  return base(
    <>
      <circle cx={12} cy={12} r={3.2} stroke="currentColor" strokeWidth={1.6} />
      <path
        d="M12 3v2.2M12 18.8V21M21 12h-2.2M5.2 12H3M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6M18.4 18.4l-1.6-1.6M7.2 7.2L5.6 5.6"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
    </>,
    props,
  );
}

export function BackspaceIcon(props: IconProps) {
  return base(
    <>
      <path d="M8 6h12v12H8l-5-6 5-6z" stroke="currentColor" strokeWidth={1.6} strokeLinejoin="round" fill="none" />
      <line x1={11} y1={9} x2={17} y2={15} stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" />
      <line x1={17} y1={9} x2={11} y2={15} stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" />
    </>,
    props,
  );
}

export function EyeIcon({ open, ...props }: { open: boolean } & IconProps) {
  return base(
    open ? (
      <>
        <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z" stroke="currentColor" strokeWidth={1.6} fill="none" />
        <circle cx={12} cy={12} r={2.6} stroke="currentColor" strokeWidth={1.6} />
      </>
    ) : (
      <path d="M3 3l18 18M10.6 10.6a2.6 2.6 0 003.8 3.8M6.5 6.9C4 8.5 2 12 2 12s4 7 10 7c1.6 0 3-.4 4.3-1.1M17.6 17.6C20 16 22 12 22 12s-1.7-3-4.8-5" stroke="currentColor" strokeWidth={1.6} fill="none" strokeLinecap="round" />
    ),
    props,
  );
}

export function LockIcon(props: IconProps) {
  return base(
    <>
      <rect x={5} y={10} width={14} height={10} rx={1.5} stroke="currentColor" strokeWidth={1.6} fill="none" />
      <path d="M8 10V7a4 4 0 018 0v3" stroke="currentColor" strokeWidth={1.6} fill="none" />
    </>,
    props,
  );
}

export function DisplayIcon(props: IconProps) {
  return base(
    <>
      <rect x={2} y={4} width={20} height={13} rx={1.5} stroke="currentColor" strokeWidth={1.6} fill="none" />
      <line x1={8} y1={21} x2={16} y2={21} stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" />
      <line x1={12} y1={17} x2={12} y2={21} stroke="currentColor" strokeWidth={1.6} />
    </>,
    props,
  );
}

export function PowerIcon(props: IconProps) {
  return base(
    <>
      <path d="M12 3v8" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
      <path d="M7 6a8 8 0 1010 0" stroke="currentColor" strokeWidth={1.8} fill="none" strokeLinecap="round" />
    </>,
    props,
  );
}

export function CheckIcon(props: IconProps) {
  return base(<path d="M4 12l5 5 11-11" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" fill="none" />, props);
}

export function PhoneIcon(props: IconProps) {
  return base(
    <>
      <rect x={7} y={2} width={10} height={20} rx={2} stroke="currentColor" strokeWidth={1.6} fill="none" />
      <line x1={10} y1={18} x2={14} y2={18} stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" />
    </>,
    props,
  );
}
