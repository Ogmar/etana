// Plain-JS mirror of the CSS custom properties in index.css's :root.
// Three.js materials and Recharts inline props can't read CSS variables, so
// this file exists for JS-side consumers. Keep in sync with index.css by hand.
export const theme = {
  bg: "#05070a",
  panel: "#0b1017",
  panel2: "#0f1721",
  line: "#1b2632",
  cyan: "#00e5c7",
  blue: "#4da3ff",
  amber: "#ffb020",
  red: "#ff5266",
  merge: "#b18cff",
  text: "#d6e0ea",
  muted: "#8a97a6",
  dim: "#4a5765",
} as const;

export const fontMono = '"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace';
