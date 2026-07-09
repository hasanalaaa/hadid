import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Star, Download, Trash2, Copy, Check, Plus, X, User } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/context/AppContext";
import { api, API, fmtDate } from "@/lib/api";
import PlatformIcon from "@/components/PlatformIcon";
import { PLATFORM_NAMES } from "@/i18n";

function highlight(text, tokens) {
  if (!tokens.length) return [text];
  const pattern = tokens.map((tk) => tk.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const parts = text.split(new RegExp(`(${pattern})`, "gi"));
  return parts.map((p, i) => (i % 2 === 1 ? <mark key={i}>{p}</mark> : p));
}

function MessageBody({ content, tokens }) {
  const segments = content.split(/```/);
  return (
    <div className="msg-body">
      {segments.map((seg, i) =>
        i % 2 === 1 ? (
          <pre key={i} dir="ltr" className="code-block">
            <code>{seg.replace(/^[a-z]+\n/i, "")}</code>
          </pre>
        ) : (
          <p key={i} className="whitespace-pre-wrap leading-relaxed">{highlight(seg, tokens)}</p>
        )
      )}
    </div>
  );
}

export default function ConversationDetail() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { t, lang } = useApp();
  const navigate = useNavigate();
  const [conv, setConv] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(null);
  const [tagInput, setTagInput] = useState("");
  const [showTagInput, setShowTagInput] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const q = searchParams.get("q") || "";
  const tokens = q.trim() ? q.trim().split(/\s+/) : [];

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/conversations/${id}`);
      setConv(data);
    } catch {
      setNotFound(true);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  if (notFound) return <p className="pt-20 text-center text-secondary">{t("detail.notFound")}</p>;
  if (!conv) return <p className="pt-20 text-center text-secondary">{t("common.loading")}</p>;

  const BackIcon = lang === "ar" ? ArrowRight : ArrowLeft;

  const toggleFavorite = async () => {
    const { data } = await api.post(`/conversations/${id}/favorite`);
    setConv((c) => ({ ...c, favorite: data.favorite }));
    toast.success(data.favorite ? t("detail.favAdded") : t("detail.favRemoved"));
  };

  const deleteConv = async () => {
    await api.delete(`/conversations/${id}`);
    toast.success(t("detail.deleted"));
    navigate("/conversations");
  };

  const addTag = async () => {
    const name = tagInput.trim();
    if (!name) return;
    await api.post(`/conversations/${id}/tags`, { name });
    setConv((c) => ({ ...c, tags: [...new Set([...c.tags, name])] }));
    setTagInput("");
    setShowTagInput(false);
    toast.success(t("detail.tagAdded"));
  };

  const removeTag = async (name) => {
    await api.delete(`/conversations/${id}/tags/${encodeURIComponent(name)}`);
    setConv((c) => ({ ...c, tags: c.tags.filter((tg) => tg !== name) }));
    toast.success(t("detail.tagRemoved"));
  };

  const copyMessage = async (content, i) => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = content;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch { /* ignore */ }
      document.body.removeChild(ta);
    }
    setCopied(i);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div data-testid="conversation-detail-page" className="max-w-3xl">
      <button data-testid="back-btn" onClick={() => navigate(-1)} className="btn-ghost !py-1.5 !px-3 mb-5 text-xs">
        <BackIcon size={14} />
        {t("detail.back")}
      </button>

      <header className="glass-card rounded-2xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <span className="platform-badge !w-11 !h-11 shrink-0">
            <PlatformIcon source={conv.source} size={20} />
          </span>
          <div className="flex-1 min-w-0">
            <h1 className="font-heading text-xl font-bold leading-snug" data-testid="conversation-title">{conv.title}</h1>
            <p className="text-xs text-secondary mt-1.5">
              {PLATFORM_NAMES[conv.source] || conv.source}
              {conv.created_at && <> · {fmtDate(conv.created_at, lang)}</>}
              {" · "}{conv.messages.length} {t("common.messages")}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-5">
          <button
            data-testid="detail-favorite-btn"
            onClick={toggleFavorite}
            className={`btn-ghost !py-1.5 !px-3 text-xs ${conv.favorite ? "!text-amber-400 !border-amber-400/30" : ""}`}
          >
            <Star size={13} fill={conv.favorite ? "currentColor" : "none"} />
            {t("common.favorites")}
          </button>
          <a
            data-testid="export-md-btn"
            href={`${API}/export/conversation/${id}`}
            className="btn-ghost !py-1.5 !px-3 text-xs"
          >
            <Download size={13} />
            {t("detail.exportMd")}
          </a>
          <button
            data-testid="delete-btn"
            onClick={() => setConfirmDelete(true)}
            className="btn-ghost !py-1.5 !px-3 text-xs !text-red-400 !border-red-400/20 hover:!bg-red-500/10"
          >
            <Trash2 size={13} />
            {t("common.delete")}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-4">
          {conv.tags.map((tag) => (
            <span key={tag} className="tag-chip flex items-center gap-1.5" data-testid={`tag-${tag}`}>
              {tag}
              <button data-testid={`remove-tag-${tag}`} onClick={() => removeTag(tag)} className="hover:text-red-400 transition-colors">
                <X size={11} />
              </button>
            </span>
          ))}
          {showTagInput ? (
            <span className="flex items-center gap-1">
              <input
                data-testid="tag-input"
                autoFocus
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addTag()}
                placeholder={t("detail.tagPlaceholder")}
                className="glass-input rounded-lg px-2.5 py-1 text-xs w-32 outline-none"
              />
              <button data-testid="tag-submit-btn" onClick={addTag} className="icon-btn !w-6 !h-6">
                <Check size={12} />
              </button>
            </span>
          ) : (
            <button data-testid="add-tag-btn" onClick={() => setShowTagInput(true)} className="tag-chip hover:text-primary flex items-center gap-1 transition-colors">
              <Plus size={11} />
              {t("detail.addTag")}
            </button>
          )}
        </div>
      </header>

      <div className="space-y-4" data-testid="messages-list">
        {conv.messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`} data-testid={`message-${i}`}>
            <span className={`msg-avatar shrink-0 ${m.role === "user" ? "msg-avatar-user" : ""}`}>
              {m.role === "user" ? <User size={14} /> : <PlatformIcon source={conv.source} size={14} />}
            </span>
            <div className={`msg-bubble group ${m.role === "user" ? "msg-user" : "msg-assistant"}`}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[11px] font-bold text-secondary uppercase tracking-wider">
                  {m.role === "user" ? t("detail.you") : t("detail.assistant")}
                </span>
                {m.created_at && (
                  <span className="text-[10px] text-secondary/70">{fmtDate(m.created_at, lang)}</span>
                )}
                <button
                  data-testid={`copy-msg-${i}`}
                  onClick={() => copyMessage(m.content, i)}
                  className="ms-auto icon-btn !w-6 !h-6 opacity-0 group-hover:opacity-100"
                  title={t("common.copy")}
                >
                  {copied === i ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
                </button>
              </div>
              <MessageBody content={m.content} tokens={tokens} />
            </div>
          </div>
        ))}
      </div>

      {confirmDelete && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center px-4 search-backdrop" onClick={() => setConfirmDelete(false)}>
          <div className="glass-modal rounded-2xl p-6 max-w-sm w-full animate-pop" onClick={(e) => e.stopPropagation()} data-testid="delete-confirm-modal">
            <h3 className="font-heading font-bold text-lg mb-2">{t("detail.deleteTitle")}</h3>
            <p className="text-sm text-secondary mb-6">{t("detail.deleteDesc")}</p>
            <div className="flex justify-end gap-2">
              <button data-testid="delete-cancel-btn" onClick={() => setConfirmDelete(false)} className="btn-ghost text-xs">
                {t("common.cancel")}
              </button>
              <button data-testid="delete-confirm-btn" onClick={deleteConv} className="btn-danger text-xs">
                {t("common.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
