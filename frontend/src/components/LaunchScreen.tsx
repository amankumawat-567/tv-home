import { launching } from "../state/ui";

export function LaunchScreen() {
  const state = launching.value;
  if (!state) return null;
  return (
    <div className="launch-screen">
      <div className="launch-logo">{state.name[0]}</div>
      <div className="launch-name">{state.name}</div>
      <div className="launch-spinner" aria-hidden="true" />
    </div>
  );
}
