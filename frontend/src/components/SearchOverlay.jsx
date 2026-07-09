import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, X, CornerDownLeft } from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import PlatformIcon from "@/components/PlatformIcon";
import { PLATFORM_NAMES } from "@/i18n";

function Snippet({ text }) {
  const parts = text.split(/«|»/);
  return (
    <span>
      {parts.map((p, i) => (i % 2 === 1 ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>))}
    </span>
  );
}

export default function SearchOverlay() {
  const { t, searchOpen, setSearchOpen } = useApp();
  const [query, setQuery] = useState("");
  const [source, setSource] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (searchOpen) {
      setTimeout(() => inputRef.current?.focus(), 60);
    } else {
      setQuery("");
      setResults([]);
      setSource(null);
    }
  }, [searchOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    const id = setTimeout(async () => {
      try {
        const { data } = await api.get("/search", {
          params: { q: query, source: source || undefined, limit: 30 },
        });
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(id);
  }, [query, source]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") setSearchOpen(false);
    };
    if (searchOpen) window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [searchOpen, setSearchOpen]);

  if (!searchOpen) return null;

  const openResult = (r) => {
    setSearchOpen(false);
    navigate(`/conversations/${r.conversation_id}?q=${encodeURIComponent(query)}`);
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center pt-[12vh] px-4 search-backdrop"
      onClick={() => setSearchOpen(false)}
      data-testid="search-overlay"
    >
      <div
        className="w-full max-w-2xl glass-modal rounded-2xl overflow-hidden animate-pop"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-5 py-4 border-b border-line">
          <Search size={18} className="text-secondary shrink-0" />
          <input
            ref={inputRef}
            data-testid="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("common.searchPlaceholder")}
            className="flex-1 bg-transparent outline-none text-base placeholder:text-secondary"
          />
          <button data-testid="search-close-btn" onClick={() => setSearchOpen(false)} className="icon-btn !w-7 !h-7">
            <X size={14} />
          </button>
        </div>

        <div className="flex items-center gap-1.5 px-5 py-2.5 border-b border-line overflow-x-auto">
          <button
            data-testid="search-filter-all"
            onClick={() => setSource(null)}
            className={`chip ${!source ? "chip-active" : ""}`}
          >
            {t("common.all")}
          </button>
          {Object.keys(PLATFORM_NAMES).map((s) => (
            <button
              key={s}
              data-testid={`search-filter-${s}`}
              onClick={() => setSource(source === s ? null : s)}
              className={`chip flex items-center gap-1.5 ${source === s ? "chip-active" : ""}`}
            >
              <PlatformIcon source={s} size={12} />
              {PLATFORM_NAMES[s]}
            </button>
          ))}
        </div>

        <div className="max-h-[46vh] overflow-y-auto" data-testid="search-results">
          {!query.trim() && (
            <p className="px-5 py-8 text-sm text-secondary text-center">{t("search.hint")}</p>
          )}
          {query.trim() && !loading && results.length === 0 && (
            <p className="px-5 py-8 text-sm text-secondary text-center" data-testid="search-no-results">
              {t("common.noResults")}
            </p>
          )}
          {results.map((r) => (
            <button
              key={r.message_id}
              data-testid={`search-result-${r.message_id}`}
              onClick={() => openResult(r)}
              className="w-full text-start px-5 py-3.5 hover:bg-hover transition-colors duration-150 border-b border-line last:border-0 group"
            >
              <span className="flex items-center gap-2 mb-1">
                <PlatformIcon source={r.source} size={13} />
                <span className="text-sm font-semibold truncate">{r.title}</span>
                <CornerDownLeft size={12} className="text-secondary opacity-0 group-hover:opacity-100 ms-auto shrink-0" />
              </span>
              <span className="block text-xs text-secondary leading-relaxed line-clamp-2">
                <Snippet text={r.snippet} />
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
