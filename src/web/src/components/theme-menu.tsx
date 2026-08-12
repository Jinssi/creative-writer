import { useEffect, useRef, useState } from "react";
import { ChevronDownIcon, CheckIcon } from "@heroicons/react/24/outline";
import { THEMES } from "../themes";
import { useTheme } from "../theme-context";

// Theme picker that lives in the desktop menu bar. Switching a theme changes the
// example prompts and the writing domain guidance sent to the agents.
export const ThemeMenu = () => {
  const { theme, setThemeId } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full bg-white/70 hover:bg-white px-3 py-1.5 text-sm font-medium text-purple-900 shadow-sm ring-1 ring-purple-200 transition"
      >
        <span className="text-base leading-none">{theme.emoji}</span>
        <span className="hidden sm:inline">{theme.name}</span>
        <ChevronDownIcon className="w-4 h-4 text-purple-500" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-white/95 backdrop-blur shadow-xl ring-1 ring-purple-100 p-2 z-50">
          <p className="px-3 pt-2 pb-1 text-xs font-semibold uppercase tracking-wide text-purple-400">
            Creative theme
          </p>
          {THEMES.map((t) => {
            const active = t.id === theme.id;
            return (
              <button
                key={t.id}
                onClick={() => {
                  setThemeId(t.id);
                  setOpen(false);
                }}
                className={`w-full flex items-start gap-3 rounded-xl px-3 py-2 text-left transition ${
                  active ? "bg-purple-50" : "hover:bg-purple-50/60"
                }`}
              >
                <span className="text-xl leading-none mt-0.5">{t.emoji}</span>
                <span className="flex-1">
                  <span className="block text-sm font-medium text-gray-900">{t.name}</span>
                  <span className="block text-xs text-gray-500">{t.tagline}</span>
                </span>
                {active && <CheckIcon className="w-4 h-4 text-purple-600 mt-1" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ThemeMenu;
