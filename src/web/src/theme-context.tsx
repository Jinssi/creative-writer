import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { DEFAULT_THEME_ID, getTheme, Theme } from "./themes";

interface ThemeContextValue {
  theme: Theme;
  themeId: string;
  setThemeId: (id: string) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY = "cw.themeId";

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [themeId, setThemeId] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME_ID
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, themeId);
  }, [themeId]);

  const value = useMemo(
    () => ({ theme: getTheme(themeId), themeId, setThemeId }),
    [themeId]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
};
