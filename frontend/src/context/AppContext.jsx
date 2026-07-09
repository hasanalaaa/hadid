import { createContext, useContext, useEffect, useState } from "react";
import { translations } from "@/i18n";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("hadid-lang") || "ar");
  const [theme, setTheme] = useState(() => localStorage.getItem("hadid-theme") || "dark");
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem("hadid-lang", lang);
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    localStorage.setItem("hadid-theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const t = (path) => {
    const parts = path.split(".");
    let node = translations[lang];
    for (const p of parts) node = node?.[p];
    return node ?? path;
  };

  return (
    <AppContext.Provider value={{ lang, setLang, theme, setTheme, t, searchOpen, setSearchOpen }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
