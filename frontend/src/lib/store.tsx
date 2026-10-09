import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "dark" | "light";

interface Store {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const StoreContext = createContext<Store | null>(null);

function initialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const saved = window.localStorage.getItem("is-theme");
  return saved === "light" || saved === "dark" ? saved : "dark";
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(initialTheme);

  const setTheme = useCallback((value: Theme) => {
    setThemeState(value);
    window.localStorage.setItem("is-theme", value);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  return <StoreContext.Provider value={{ theme, setTheme }}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const store = useContext(StoreContext);
  if (!store) throw new Error("useStore must be used inside StoreProvider");
  return store;
}
