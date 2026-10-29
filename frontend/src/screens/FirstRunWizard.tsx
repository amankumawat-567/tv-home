import { useEffect, useState } from "preact/hooks";
import { useFocusable } from "../focus/useFocusable";
import { popScope, pushScope } from "../focus/engine";
import { onNav } from "../focus/navEvents";
import { api } from "../api";
import { appState, refreshState } from "../state/data";
import { WifiPage } from "../settings/WifiPage";
import { CatalogTile } from "./AppStore";

const STEPS = ["welcome", "wifi", "remote", "apps", "done"] as const;
type Step = (typeof STEPS)[number];

function WizardButton({ label, onSelect, autoFocus, accent }: { label: string; onSelect: () => void; autoFocus?: boolean; accent?: boolean }) {
  const { ref, focused } = useFocusable({ scope: "firstRun", wrapGroup: "wizard-footer", onSelect, autoFocus });
  return (
    <button ref={ref as never} className={`dialog-button focusable${focused ? " is-focused" : ""}${accent ? " is-accent" : ""}`} onClick={onSelect}>
      {label}
    </button>
  );
}

export function FirstRunWizard() {
  const [step, setStep] = useState<Step>("welcome");
  const index = STEPS.indexOf(step);

  useEffect(() => {
    pushScope("firstRun");
    return () => popScope();
  }, []);

  const finish = async () => {
    await api.completeFirstRun().catch(() => undefined);
    await refreshState();
  };

  useEffect(
    () =>
      onNav("back", () => {
        if (index > 0) setStep(STEPS[index - 1]);
        return true; // first run owns Back entirely — never falls through to closing an overlay that isn't open
      }),
    [index],
  );

  // Home always returns to Home (even mid-setup) — treat it as "skip the rest".
  useEffect(
    () =>
      onNav("home", () => {
        void finish();
        return true;
      }),
    [],
  );

  const goTo = (s: Step) => setStep(s);

  return (
    <div className="first-run">
      <div className="first-run-progress">
        {STEPS.slice(0, -1).map((s, i) => (
          <span key={s} className={`first-run-dot${i <= index ? " is-active" : ""}`} />
        ))}
      </div>

      <div className="first-run-content">
        {step === "welcome" && (
          <div className="first-run-step first-run-center">
            <h1 className="settings-title">Welcome to TV Home</h1>
            <p className="dialog-message">Let's get a few things set up — this takes about a minute. You can always change any of it later from Settings.</p>
          </div>
        )}

        {step === "wifi" && (
          <div className="first-run-step">
            <WifiPage />
          </div>
        )}

        {step === "remote" && (
          <div className="first-run-step first-run-center">
            <h1 className="settings-title">Test your remote</h1>
            <OkButtonTile onSelect={() => goTo("apps")} />
            <p className="dialog-message">Using a Bluetooth remote? Pair it any time from Settings → Bluetooth.</p>
          </div>
        )}

        {step === "apps" && (
          <div className="first-run-step">
            <h1 className="settings-title">Pick a few apps</h1>
            <p className="dialog-message">Select any you'd like on Home — add more later from the App Store.</p>
            <div className="apps-grid">
              {(appState.value?.catalog ?? []).slice(0, 8).map((entry) => (
                <CatalogTile key={entry.id} entry={entry} />
              ))}
            </div>
          </div>
        )}

        {step === "done" && (
          <div className="first-run-step first-run-center">
            <h1 className="settings-title">All set!</h1>
            <p className="dialog-message">Everything here can be changed later from Settings.</p>
          </div>
        )}
      </div>

      <div className="first-run-footer">
        {step !== "welcome" && step !== "done" && (
          <WizardButton label="Back" onSelect={() => setStep(STEPS[Math.max(0, index - 1)])} />
        )}
        {step === "welcome" && <WizardButton label="Get started" accent autoFocus onSelect={() => goTo("wifi")} />}
        {step === "wifi" && <WizardButton label="Next" accent onSelect={() => goTo("remote")} />}
        {step === "apps" && <WizardButton label="Finish" accent onSelect={() => goTo("done")} />}
        {step === "done" && <WizardButton label="Go to Home" accent autoFocus onSelect={finish} />}
      </div>
    </div>
  );
}

function OkButtonTile({ onSelect }: { onSelect: () => void }) {
  const { ref, focused } = useFocusable({ scope: "firstRun", onSelect, autoFocus: true });
  return (
    <button ref={ref as never} className={`first-run-ok focusable${focused ? " is-focused" : ""}`} onClick={onSelect}>
      Press OK to continue
    </button>
  );
}
