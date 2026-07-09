import { useNavigate } from "react-router-dom";
import { Star, MessagesSquare } from "lucide-react";
import PlatformIcon from "@/components/PlatformIcon";
import { PLATFORM_NAMES } from "@/i18n";
import { useApp } from "@/context/AppContext";
import { fmtDate } from "@/lib/api";

export default function ConversationRow({ conv, onToggleFavorite }) {
  const { t, lang } = useApp();
  const navigate = useNavigate();

  return (
    <div
      data-testid={`conversation-row-${conv.id}`}
      onClick={() => navigate(`/conversations/${conv.id}`)}
      className="glass-card rounded-2xl px-5 py-4 flex items-center gap-4 cursor-pointer card-hover"
    >
      <span className="platform-badge shrink-0">
        <PlatformIcon source={conv.source} size={17} />
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm truncate">{conv.title || t("common.untitled")}</p>
        <div className="flex items-center flex-wrap gap-x-3 gap-y-1 mt-1 text-xs text-secondary">
          <span>{PLATFORM_NAMES[conv.source] || conv.source}</span>
          {conv.created_at && <span>{fmtDate(conv.created_at, lang)}</span>}
          <span className="flex items-center gap-1">
            <MessagesSquare size={11} />
            {conv.message_count} {t("common.messages")}
          </span>
          {conv.tags?.slice(0, 3).map((tag) => (
            <span key={tag} className="tag-chip">{tag}</span>
          ))}
        </div>
      </div>
      <button
        data-testid={`favorite-btn-${conv.id}`}
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite?.(conv);
        }}
        className={`icon-btn shrink-0 ${conv.favorite ? "!text-amber-400" : ""}`}
      >
        <Star size={16} fill={conv.favorite ? "currentColor" : "none"} />
      </button>
    </div>
  );
}
