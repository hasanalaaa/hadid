import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { MessagesSquare, MessageSquareText, Star, Tags, Upload, Sparkles, ArrowUpRight } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { toast } from "sonner";
import { useApp } from "@/context/AppContext";
import { api, fmtNum } from "@/lib/api";
import PlatformIcon, { PLATFORM_COLORS } from "@/components/PlatformIcon";
import ConversationRow from "@/components/ConversationRow";
import { PLATFORM_NAMES } from "@/i18n";

const STAT_ICONS = { conversations: MessagesSquare, messages: MessageSquareText, favorites: Star, tags: Tags };

export default function Dashboard() {
  const { t, lang } = useApp();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [words, setWords] = useState([]);
  const [recent, setRecent] = useState([]);
  const [demoLoading, setDemoLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, a, w, r] = await Promise.all([
        api.get("/stats"),
        api.get("/activity"),
        api.get("/wordcloud", { params: { limit: 24 } }),
        api.get("/conversations", { params: { limit: 5 } }),
      ]);
      setStats(s.data);
      setActivity(a.data);
      setWords(w.data);
      setRecent(r.data.items);
    } catch {
      toast.error(t("common.error"));
    }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const loadDemo = async () => {
    setDemoLoading(true);
    try {
      await api.post("/demo");
      toast.success(t("dashboard.demoLoaded"));
      await load();
    } catch {
      toast.error(t("common.error"));
    } finally {
      setDemoLoading(false);
    }
  };

  const toggleFavorite = async (conv) => {
    await api.post(`/conversations/${conv.id}/favorite`);
    setRecent((prev) => prev.map((c) => (c.id === conv.id ? { ...c, favorite: !c.favorite } : c)));
  };

  if (!stats) return <div className="pt-20 text-center text-secondary">{t("common.loading")}</div>;

  if (stats.conversations === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center" data-testid="dashboard-empty-state">
        <span className="logo-badge !w-16 !h-16 mb-6 animate-pop">
          <Sparkles size={28} />
        </span>
        <h1 className="font-heading text-3xl font-bold mb-3">{t("dashboard.emptyTitle")}</h1>
        <p className="text-secondary max-w-md mb-8">{t("dashboard.emptyDesc")}</p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button data-testid="empty-import-btn" onClick={() => navigate("/import")} className="btn-primary">
            <Upload size={16} />
            {t("dashboard.ctaImport")}
          </button>
          <button data-testid="empty-demo-btn" onClick={loadDemo} disabled={demoLoading} className="btn-ghost">
            <Sparkles size={16} />
            {demoLoading ? t("common.loading") : t("dashboard.ctaDemo")}
          </button>
        </div>
      </div>
    );
  }

  const statCards = [
    { key: "conversations", value: stats.conversations },
    { key: "messages", value: stats.messages },
    { key: "favorites", value: stats.favorites },
    { key: "tags", value: stats.tags },
  ];
  const maxSource = Math.max(1, ...Object.values(stats.by_source || {}));
  const maxWord = Math.max(1, ...words.map((w) => w.count));

  return (
    <div data-testid="dashboard-page">
      <header className="mb-8">
        <h1 className="font-heading text-3xl font-bold tracking-tight">{t("dashboard.title")}</h1>
        <p className="text-secondary mt-1">{t("dashboard.subtitle")}</p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statCards.map(({ key, value }, i) => {
          const Icon = STAT_ICONS[key];
          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="glass-card rounded-2xl p-5"
              data-testid={`stat-card-${key}`}
            >
              <span className="flex items-center gap-2 text-secondary text-xs font-medium uppercase tracking-wider">
                <Icon size={14} className="text-accent" />
                {t(`dashboard.stat${key[0].toUpperCase() + key.slice(1)}`)}
              </span>
              <p className="font-heading text-3xl font-bold mt-2">{fmtNum(value, lang)}</p>
            </motion.div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 glass-card rounded-2xl p-5" data-testid="activity-chart">
          <h2 className="font-heading font-bold mb-4">{t("dashboard.activityTitle")}</h2>
          <div className="h-56" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activity} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="accentFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: "var(--tooltip-bg)", border: "1px solid var(--line)",
                    borderRadius: 12, backdropFilter: "blur(12px)", color: "var(--text-primary)", fontSize: 12,
                  }}
                />
                <Area type="monotone" dataKey="n" stroke="var(--accent)" strokeWidth={2} fill="url(#accentFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5" data-testid="sources-panel">
          <h2 className="font-heading font-bold mb-4">{t("dashboard.sourcesTitle")}</h2>
          <div className="space-y-4">
            {Object.entries(stats.by_source).sort((a, b) => b[1] - a[1]).map(([source, n]) => (
              <div key={source}>
                <div className="flex items-center gap-2 mb-1.5">
                  <PlatformIcon source={source} size={14} />
                  <span className="text-sm font-medium">{PLATFORM_NAMES[source] || source}</span>
                  <span className="ms-auto text-xs text-secondary">{fmtNum(n, lang)}</span>
                </div>
                <div className="h-1.5 rounded-full bg-hover overflow-hidden">
                  <div
                    className="h-full rounded-full transition-transform duration-500"
                    style={{ width: `${(n / maxSource) * 100}%`, background: PLATFORM_COLORS[source] || "var(--accent)" }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2" data-testid="recent-conversations">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-heading font-bold">{t("dashboard.recentTitle")}</h2>
            <Link to="/conversations" data-testid="view-all-link" className="text-xs text-accent flex items-center gap-1 hover:underline">
              {t("dashboard.viewAll")}
              <ArrowUpRight size={12} />
            </Link>
          </div>
          <div className="space-y-2.5">
            {recent.map((conv) => (
              <ConversationRow key={conv.id} conv={conv} onToggleFavorite={toggleFavorite} />
            ))}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-5 h-fit" data-testid="wordcloud-panel">
          <h2 className="font-heading font-bold mb-4">{t("dashboard.wordsTitle")}</h2>
          <div className="flex flex-wrap gap-2 items-center">
            {words.map((w) => (
              <span
                key={w.word}
                className="word-chip"
                style={{
                  fontSize: `${11 + (w.count / maxWord) * 10}px`,
                  opacity: 0.55 + (w.count / maxWord) * 0.45,
                }}
              >
                {w.word}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
