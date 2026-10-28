import { render } from "preact";
import "./styles/global.css";
import { App } from "./app.tsx";

render(<App />, document.getElementById("app")!);
