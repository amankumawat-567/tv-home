// Real Material Symbols (Apache 2.0) paths — fetched once from the
// @material-symbols/svg-400 package (the npm mirror of Google's
// material-design-icons repo) and pasted in here as plain path data, so the
// icon set is bundled with the app like everything else (no network call at
// runtime, consistent with the PRD's offline requirement). See
// docs/DESIGN.md's "Known gaps" — this replaces the hand-rolled stand-ins
// the UI shipped with initially.
//
// WifiIcon is the one exception, kept hand-drawn on purpose: it draws 0-4
// bars dynamically from signal strength, which no single static Material
// glyph can represent as clearly.
import type { JSX } from "preact";

type IconProps = { size?: number; className?: string };

function base(children: JSX.Element | JSX.Element[], { size = 24, className }: IconProps, viewBox = "0 -960 960 960") {
  return (
    <svg width={size} height={size} viewBox={viewBox} fill="none" className={className} aria-hidden="true">
      {children}
    </svg>
  );
}

function filled(d: string, props: IconProps) {
  return base(<path d={d} fill="currentColor" />, props);
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
    "0 0 24 24",
  );
}

export function BluetoothIcon({ state, className, size }: { state: "off" | "on" | "connected" } & IconProps) {
  const color = state === "off" ? "var(--text-muted)" : state === "connected" ? "var(--good)" : "currentColor";
  return base(
    <path
      d="M450-94v-314L256-214l-42-42 224-224-224-224 42-42 194 194v-314h30l214 214-172 172 172 172L480-94h-30Zm60-458 100-100-100-98v198Zm0 342 100-98-100-100v198Z"
      fill={color}
    />,
    { size, className },
  );
}

const VOLUME_UP =
  "M560-131v-62q97-28 158.5-107.5T780-481q0-101-61-181T560-769v-62q124 28 202 125.5T840-481q0 127-78 224.5T560-131ZM120-360v-240h160l200-200v640L280-360H120Zm420 48v-337q55 17 87.5 64T660-480q0 57-33 104t-87 64ZM420-648 307-540H180v120h127l113 109v-337Zm-94 168Z";
const VOLUME_OFF =
  "M813-56 681-188q-28 20-60.5 34.5T553-131v-62q23-7 44.5-15.5T638-231L473-397v237L273-360H113v-240h156L49-820l43-43 764 763-43 44Zm-36-232-43-43q20-34 29.5-71.92Q773-440.85 773-481q0-103.32-60-184.66T553-769v-62q124 28 202 125.5T833-481q0 51-14 100t-42 93ZM643-422l-90-90v-130q47 22 73.5 66t26.5 96q0 15-2.5 29.5T643-422ZM473-592 369-696l104-104v208Zm-60 286v-150l-84-84H173v120h126l114 114Zm-42-192Z";

export function VolumeIcon({ muted, className, size }: { level: number; muted: boolean } & IconProps) {
  return filled(muted ? VOLUME_OFF : VOLUME_UP, { size, className });
}

export function GearIcon(props: IconProps) {
  return filled(
    "m388-80-20-126q-19-7-40-19t-37-25l-118 54-93-164 108-79q-2-9-2.5-20.5T185-480q0-9 .5-20.5T188-521L80-600l93-164 118 54q16-13 37-25t40-18l20-127h184l20 126q19 7 40.5 18.5T669-710l118-54 93 164-108 77q2 10 2.5 21.5t.5 21.5q0 10-.5 21t-2.5 21l108 78-93 164-118-54q-16 13-36.5 25.5T592-206L572-80H388Zm48-60h88l14-112q33-8 62.5-25t53.5-41l106 46 40-72-94-69q4-17 6.5-33.5T715-480q0-17-2-33.5t-7-33.5l94-69-40-72-106 46q-23-26-52-43.5T538-708l-14-112h-88l-14 112q-34 7-63.5 24T306-642l-106-46-40 72 94 69q-4 17-6.5 33.5T245-480q0 17 2.5 33.5T254-413l-94 69 40 72 106-46q24 24 53.5 41t62.5 25l14 112Zm44-210q54 0 92-38t38-92q0-54-38-92t-92-38q-54 0-92 38t-38 92q0 54 38 92t92 38Zm0-130Z",
    props,
  );
}

export function BackspaceIcon(props: IconProps) {
  return filled(
    "m448-326 112-112 112 112 43-43-113-111 111-111-43-43-110 112-112-112-43 43 113 111-113 111 43 43Zm-98 166q-14.25 0-27-6.38-12.75-6.37-21-17.62L80-480l221-296q8.25-11.25 21-17.63 12.75-6.37 27-6.37h472q24.75 0 42.38 17.62Q881-764.75 881-740v520q0 24.75-17.62 42.37Q845.75-160 821-160H350ZM155-480l195 260h471v-520H350L155-480Zm431 0Z",
    props,
  );
}

const EYE_OPEN =
  "M600.5-379.5Q650-429 650-500t-49.5-120.5Q551-670 480-670t-120.5 49.5Q310-571 310-500t49.5 120.5Q409-330 480-330t120.5-49.5Zm-200-41Q368-453 368-500t32.5-79.5Q433-612 480-612t79.5 32.5Q592-547 592-500t-32.5 79.5Q527-388 480-388t-79.5-32.5ZM216-283Q98-366 40-500q58-134 176-217t264-83q146 0 264 83t176 217q-58 134-176 217t-264 83q-146 0-264-83Zm264-217Zm222.5 174.5Q804-391 857-500q-53-109-154.5-174.5T480-740q-121 0-222.5 65.5T102-500q54 109 155.5 174.5T480-260q121 0 222.5-65.5Z";
const EYE_CLOSED =
  "m629-419-44-44q26-71-27-118t-115-24l-44-44q17-11 38-16t43-5q71 0 120.5 49.5T650-500q0 22-5.5 43.5T629-419Zm129 129-40-40q49-36 85.5-80.5T857-500q-50-111-150-175.5T490-740q-42 0-86 8t-69 19l-46-47q35-16 89.5-28T485-800q143 0 261.5 81.5T920-500q-26 64-67 117t-95 93Zm58 226L648-229q-35 14-79 21.5t-89 7.5q-146 0-265-81.5T40-500q20-52 55.5-101.5T182-696L56-822l42-43 757 757-39 44ZM223-654q-37 27-71.5 71T102-500q51 111 153.5 175.5T488-260q33 0 65-4t48-12l-64-64q-11 5-27 7.5t-30 2.5q-70 0-120-49t-50-121q0-15 2.5-30t7.5-27l-97-97Zm305 142Zm-116 58Z";

export function EyeIcon({ open, ...props }: { open: boolean } & IconProps) {
  return filled(open ? EYE_OPEN : EYE_CLOSED, props);
}

export function LockIcon(props: IconProps) {
  return filled(
    "M220-80q-24.75 0-42.37-17.63Q160-115.25 160-140v-434q0-24.75 17.63-42.38Q195.25-634 220-634h70v-96q0-78.85 55.61-134.42Q401.21-920 480.11-920q78.89 0 134.39 55.58Q670-808.85 670-730v96h70q24.75 0 42.38 17.62Q800-598.75 800-574v434q0 24.75-17.62 42.37Q764.75-80 740-80H220Zm0-60h520v-434H220v434Zm314.5-162.03Q557-324.06 557-355q0-30-22.67-54.5t-54.5-24.5q-31.83 0-54.33 24.5t-22.5 55q0 30.5 22.67 52.5t54.5 22q31.83 0 54.33-22.03ZM350-634h260v-96q0-54.17-37.88-92.08-37.88-37.92-92-37.92T388-822.08q-38 37.91-38 92.08v96ZM220-140v-434 434Z",
    props,
  );
}

export function DisplayIcon(props: IconProps) {
  return filled(
    "M334-120v-60h86v-100H140q-24 0-42-18t-18-42v-440q0-24 18-42t42-18h680q24 0 42 18t18 42v440q0 24-18 42t-42 18H540v100h86v60H334ZM140-340h680v-440H140v440Zm0 0v-440 440Z",
    props,
  );
}

export function PowerIcon(props: IconProps) {
  return filled(
    "M480-80q-82 0-155-31.5t-127.5-86Q143-252 111.5-325T80-480q0-84 32-156.5T198-763l42 42q-47 46-73.5 108T140-480q0 141 99.5 240.5T480-140q142 0 241-99.5T820-480q0-71-26-133t-73-108l42-42q54 54 85.5 126.5T880-480q0 82-31.5 155T763-197.5q-54 54.5-127 86T480-80Zm-30-360v-440h60v440h-60Z",
    props,
  );
}

export function CheckIcon(props: IconProps) {
  return filled("M378-246 154-470l43-43 181 181 384-384 43 43-427 427Z", props);
}

export function PhoneIcon(props: IconProps) {
  return filled(
    "M260-40q-24.75 0-42.37-17.63Q200-75.25 200-100v-760q0-24 18-42t42-18h438q24.75 0 42.38 17.62Q758-884.75 758-860v150q18 3 30 16.95 12 13.96 12 31.63V-587q0 19-12 33t-30 17v437q0 24.75-17.62 42.37Q722.75-40 698-40H260Zm0-60h438v-760H260v760Zm0 0v-760 760Zm219-620q12 0 21-9t9-21q0-12-9-21t-21-9q-12 0-21 9t-9 21q0 12 9 21t21 9Z",
    props,
  );
}
