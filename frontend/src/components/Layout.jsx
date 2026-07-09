import { NavLink, useNavigate } from "react-router-dom";
import { Anvil, LayoutDashboard, MessagesSquare, Upload, Settings, Search, Moon, Sun, Languages } from "lucide-react";
import { useApp } from "@/context/AppContext";
import { useEffect } from "react";
import SearchOverlay from "@/components/SearchOverlay";

const NAV = [
  { to: "/", key: "dashboard", icon: LayoutDashboard, end: true },
  { to: "/conversations", key: "conversations", icon: MessagesSquare },
  { to: "/import", key: "import", icon: Upload },
  { to: "/settings", key: "settings", icon: Settings },
];

export default function Layout({ children }) {
  const { t, lang, setLang, theme, setTheme, setSearchOpen } = useApp();
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setSearchOpen]);

  return (
    <div className="min-h-screen flex bg-app text-primary">
      <div className="noise-overlay" aria-hidden="true" />

      {/* Sidebar (desktop) */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 fixed inset-y-0 start-0 z-40 glass-sidebar">
        <button
          data-testid="sidebar-logo"
          onClick={() => navigate("/")}
          className="flex items-center gap-3 px-5 pt-6 pb-5 text-start"
        >
          <span className="logo-badge">
            <Anvil size={20} />
          </span>
          <span>
            <span className="block font-heading font-bold text-lg leading-none">{t("appName")}</span>
            <span className="block text-[11px] text-secondary mt-1">{lang === "ar" ? "Hadid" : "حديد"}</span>
          </span>
        </button>

        <button
          data-testid="sidebar-search-btn"
          onClick={() => setSearchOpen(true)}
          className="mx-4 mb-4 flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-secondary glass-input hover:text-primary transition-colors duration-200"
        >
          <Search size={15} />
          <span className="flex-1 text-start">{t("common.search")}</span>
          <kbd className="kbd">⌘K</kbd>
        </button>

        <nav className="flex-1 px-3 space-y-1">
          {NAV.map(({ to, key, icon: Icon, end }) => (
            <NavLink
              key={key}
              to={to}
              end={end}
              data-testid={`nav-${key}`}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-200 ${
                  isActive ? "nav-active" : "text-secondary hover:text-primary hover:bg-hover"
                }`
              }
            >
              <Icon size={17} />
              {t(`nav.${key}`)}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 pb-5 flex items-center gap-2">
          <button
            data-testid="theme-toggle"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="icon-btn"
            title={t("settings.theme")}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button
            data-testid="lang-toggle"
            onClick={() => setLang(lang === "ar" ? "en" : "ar")}
            className="icon-btn gap-1.5 w-auto px-3"
            title={t("settings.language")}
          >
            <Languages size={16} />
            <span className="text-xs font-semibold">{lang === "ar" ? "EN" : "عربي"}</span>
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="md:hidden fixed top-0 inset-x-0 z-40 glass-sidebar flex items-center gap-2 px-4 py-3">
        <span className="logo-badge !w-8 !h-8">
          <Anvil size={16} />
        </span>
        <span className="font-heading font-bold">{t("appName")}</span>
        <div className="flex-1" />
        <button data-testid="mobile-search-btn" onClick={() => setSearchOpen(true)} className="icon-btn">
          <Search size={16} />
        </button>
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="icon-btn">
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button onClick={() => setLang(lang === "ar" ? "en" : "ar")} className="icon-btn">
          <Languages size={16} />
        </button>
      </header>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 glass-sidebar flex justify-around py-2">
        {NAV.map(({ to, key, icon: Icon, end }) => (
          <NavLink
            key={key}
            to={to}
            end={end}
            data-testid={`mobile-nav-${key}`}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] ${
                isActive ? "text-accent" : "text-secondary"
              }`
            }
          >
            <Icon size={18} />
            {t(`nav.${key}`)}
          </NavLink>
        ))}
      </nav>

      <main className="flex-1 md:ms-60 px-4 md:px-10 pt-20 md:pt-10 pb-24 md:pb-12 max-w-[1400px] relative z-10">
        {children}
      </main>

      <SearchOverlay />
    </div>
  );
}
