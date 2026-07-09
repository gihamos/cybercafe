const THEME_KEY = "cybercafe_theme";

export type Theme = "light" | "dark";

export function getStoredTheme(): Theme | null {
  const value = localStorage.getItem(THEME_KEY);
  return value === "light" || value === "dark" ? value : null;
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
}

export function initTheme() {
  const stored = getStoredTheme();
  if (stored) {
    document.documentElement.dataset.theme = stored;
  }
}
