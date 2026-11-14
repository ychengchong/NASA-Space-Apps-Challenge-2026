import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./fonts.css";
import "./styles.css";

const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("index.html has no element with the id 'root'.");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
