"use client";

import { useEffect, useState } from "react";

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function write(key: string, v: string) {
  try { localStorage.setItem(key, v); } catch {}
}

export default function ThemeControls() {
  const [dark, setDark] = useState(false);
  const [high, setHigh] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    setDark(root.dataset.theme === "dark");
    setHigh(root.dataset.contrast === "high");
  }, []);

  function toggleDark() {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    write("tema", next ? "dark" : "light");
  }
  function toggleHigh() {
    const next = !high;
    setHigh(next);
    if (next) document.documentElement.dataset.contrast = "high";
    else delete document.documentElement.dataset.contrast;
    write("contraste", next ? "high" : "normal");
  }

  return (
    <div role="group" aria-label="Preferências de exibição" className="mx-auto flex w-full max-w-2xl justify-end gap-6 px-6 pt-5 sm:px-8">
      <Switch label="Modo escuro" on={dark} onClick={toggleDark} />
      <Switch label="Alto contraste" on={high} onClick={toggleHigh} />
    </div>
  );
}

function Switch({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button type="button" role="switch" aria-checked={on} onClick={onClick} className="flex min-h-11 items-center gap-2.5 text-sm">
      <span>{label}</span>
      <span
        aria-hidden
        className="relative h-5 w-9 shrink-0 rounded-full border-2 transition-colors"
        style={{ borderColor: on ? "var(--accent)" : "var(--muted)", background: on ? "var(--accent)" : "transparent" }}
      >
        <span
          className="absolute top-0.5 h-3 w-3 rounded-full transition-all"
          style={{ left: on ? "1.15rem" : "0.15rem", background: on ? "var(--on-accent)" : "var(--muted)" }}
        />
      </span>
    </button>
  );
}
