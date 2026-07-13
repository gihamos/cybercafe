const THEME_KEY = "portail_theme";

export type Theme = "light" | "dark";

export function getStoredTheme(): Theme | null {
  const t = localStorage.getItem(THEME_KEY);
  return t === "dark" || t === "light" ? t : null;
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
}

export function initTheme() {
  const stored = getStoredTheme();
  const prefereSombre = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(stored ?? (prefereSombre ? "dark" : "light"));
}
