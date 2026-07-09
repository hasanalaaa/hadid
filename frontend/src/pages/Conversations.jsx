import { useCallback, useEffect, useState } from "react";
import { Star } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import PlatformIcon from "@/components/PlatformIcon";
import ConversationRow from "@/components/ConversationRow";
import { PLATFORM_NAMES } from "@/i18n";

const PAGE = 20;

export default function Conversations() {
  const { t } = useApp();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [source, setSource] = useState(null);
  const [favorites, setFavorites] = useState(false);
  const [tag, setTag] = useState("");
  const [titleQ, setTitleQ] = useState("");
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/tags").then(({ data }) => setTags(data)).catch(() => {});
  }, []);

  const fetchPage = useCallback(
    async (offset, replace) => {
      setLoading(true);
      try {
        const { data } = await api.get("/conversations", {
          params: {
            source: source || undefined,
            favorites: favorites || undefined,
            tag: tag || undefined,
            q: titleQ.trim() || undefined,
            limit: PAGE,
            offset,
          },
        });
        setTotal(data.total);
        setItems((prev) => (replace ? data.items : [...prev, ...data.items]));
      } catch {
        toast.error(t("common.error"));
      } finally {
        setLoading(false);
      }
    },
    [source, favorites, tag, titleQ, t]
  );

  useEffect(() => {
    const id = setTimeout(() => fetchPage(0, true), titleQ ? 300 : 0);
    return () => clearTimeout(id);
  }, [fetchPage, titleQ]);

  const toggleFavorite = async (conv) => {
    const { data } = await api.post(`/conversations/${conv.id}/favorite`);
    toast.success(data.favorite ? t("detail.favAdded") : t("detail.favRemoved"));
    if (favorites && !data.favorite) {
      setItems((prev) => prev.filter((c) => c.id !== conv.id));
      setTotal((n) => n - 1);
    } else {
      setItems((prev) => prev.map((c) => (c.id === conv.id ? { ...c, favorite: data.favorite } : c)));
    }
  };

  return (
    <div data-testid="conversations-page">
      <header className="mb-6">
        <h1 className="font-heading text-3xl font-bold tracking-tight">{t("conversations.title")}</h1>
        <p className="text-secondary mt-1">{t("conversations.subtitle")}</p>
      </header>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <button
          data-testid="filter-all"
          onClick={() => setSource(null)}
          className={`chip ${!source ? "chip-active" : ""}`}
        >
          {t("common.all")}
        </button>
        {Object.keys(PLATFORM_NAMES).map((s) => (
          <button
            key={s}
            data-testid={`filter-${s}`}
            onClick={() => setSource(source === s ? null : s)}
            className={`chip flex items-center gap-1.5 ${source === s ? "chip-active" : ""}`}
          >
            <PlatformIcon source={s} size={12} />
            {PLATFORM_NAMES[s]}
          </button>
        ))}
        <button
          data-testid="filter-favorites"
          onClick={() => setFavorites(!favorites)}
          className={`chip flex items-center gap-1.5 ${favorites ? "chip-active" : ""}`}
        >
          <Star size={12} fill={favorites ? "currentColor" : "none"} />
          {t("conversations.favoritesOnly")}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-6">
        <input
          data-testid="title-filter-input"
          value={titleQ}
          onChange={(e) => setTitleQ(e.target.value)}
          placeholder={t("conversations.searchTitles")}
          className="glass-input rounded-xl px-4 py-2 text-sm w-full sm:w-72 outline-none focus:ring-1 focus:ring-accent"
        />
        {tags.length > 0 && (
          <select
            data-testid="tag-filter-select"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            className="glass-input rounded-xl px-3 py-2 text-sm outline-none cursor-pointer"
          >
            <option value="">{t("conversations.allTags")}</option>
            {tags.map((tg) => (
              <option key={tg.name} value={tg.name}>
                {tg.name} ({tg.count})
              </option>
            ))}
          </select>
        )}
        <span className="text-xs text-secondary ms-auto" data-testid="conversations-total">
          {total} {t("nav.conversations")}
        </span>
      </div>

      {!loading && items.length === 0 && (
        <p className="text-center text-secondary py-16" data-testid="no-conversations">
          {t("conversations.noConversations")}
        </p>
      )}

      <div className="space-y-2.5">
        {items.map((conv) => (
          <ConversationRow key={conv.id} conv={conv} onToggleFavorite={toggleFavorite} />
        ))}
      </div>

      {items.length < total && (
        <div className="text-center mt-6">
          <button data-testid="load-more-btn" onClick={() => fetchPage(items.length, false)} className="btn-ghost">
            {loading ? t("common.loading") : t("common.loadMore")}
          </button>
        </div>
      )}
    </div>
  );
}
