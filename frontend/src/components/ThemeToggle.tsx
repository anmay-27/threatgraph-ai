import { Moon, Sun } from "lucide-react";
import { useState } from "react";

export function initialTheme(): "dark" | "light" {
  try { const saved = localStorage.getItem("threatgraph-theme"); if (saved === "dark" || saved === "light") return saved; } catch { /* Storage can be disabled. */ }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
document.documentElement.dataset.theme = initialTheme();

export default function ThemeToggle() {
  const [theme, setTheme] = useState(initialTheme);
  return <button className="theme-toggle" aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} onClick={() => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next); document.documentElement.dataset.theme = next;
    try { localStorage.setItem("threatgraph-theme", next); } catch { /* Theme still works for this session. */ }
    window.dispatchEvent(new Event("themechange"));
  }}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}<span>{theme === "dark" ? "Light" : "Dark"}</span></button>;
}
