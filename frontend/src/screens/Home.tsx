import type { AppState } from "../types";
import { Row } from "../components/Row";
import { greeting, longDate } from "../components/Clock";

export function Home({ state }: { state: AppState }) {
  return (
    <div
      className="home-screen"
      // /wallpaper always answers at the same URL even after the selection
      // changes -- ?v=<wallpaperVersion> forces a real re-fetch instead of
      // risking a stale cached image (this was reported as wallpapers not
      // actually being switchable).
      style={state.wallpaper ? { backgroundImage: `url(/wallpaper?v=${state.wallpaperVersion})` } : undefined}
    >
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
