import type { AppState } from "../types";
import { Row } from "../components/Row";
import { greeting, longDate } from "../components/Clock";

export function Home({ state }: { state: AppState }) {
  return (
    <div className="home-screen" style={state.wallpaper ? { backgroundImage: "url(/wallpaper)" } : undefined}>
      <div className="home-greeting">
        <div className="home-greeting-text">
          {greeting()}, {state.user}
        </div>
        <div className="home-date">{longDate()}</div>
      </div>
      <div className="home-rows">
        <Row title="Favourites" apps={state.apps} />
      </div>
    </div>
  );
}
