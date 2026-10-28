import type { AppTile } from "../types";
import { AppBanner } from "./AppBanner";

export function Row({ title, apps }: { title: string; apps: AppTile[] }) {
  if (apps.length === 0) return null;
  return (
    <section className="app-row">
      <h2 className="row-title">{title}</h2>
      <div className="grid-12">
        {apps.map((app) => (
          <AppBanner key={app.id} app={app} />
        ))}
      </div>
    </section>
  );
}
