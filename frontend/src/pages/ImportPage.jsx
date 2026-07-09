import { useRef, useState } from "react";
import { UploadCloud, FileJson, CheckCircle2, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { useApp } from "@/context/AppContext";
import { api, fmtNum } from "@/lib/api";
import PlatformIcon from "@/components/PlatformIcon";
import { PLATFORM_NAMES } from "@/i18n";

export default function ImportPage() {
  const { t, lang } = useApp();
  const navigate = useNavigate();
  const [platform, setPlatform] = useState("auto");
  const [dragging, setDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const inputRef = useRef(null);

  const upload = async (file) => {
    if (!file) return;
    setImporting(true);
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("platform", platform);
    try {
      const { data } = await api.post("/import", form);
      setResult(data);
      toast.success(t("importPage.importSuccess"));
    } catch (err) {
      toast.error(err.response?.data?.detail || t("importPage.importError"));
    } finally {
      setImporting(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const loadDemo = async () => {
    setDemoLoading(true);
    try {
      const { data } = await api.post("/demo");
      setResult(data);
      toast.success(t("dashboard.demoLoaded"));
    } catch {
      toast.error(t("common.error"));
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div data-testid="import-page" className="max-w-3xl">
      <header className="mb-8">
        <h1 className="font-heading text-3xl font-bold tracking-tight">{t("importPage.title")}</h1>
        <p className="text-secondary mt-1">{t("importPage.subtitle")}</p>
      </header>

      <div className="flex items-center gap-2 mb-4">
        <label className="text-sm text-secondary">{t("importPage.platform")}:</label>
        <select
          data-testid="platform-select"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="glass-input rounded-xl px-3 py-2 text-sm outline-none cursor-pointer"
        >
          <option value="auto">{t("importPage.auto")}</option>
          {Object.keys(PLATFORM_NAMES).map((s) => (
            <option key={s} value={s}>{PLATFORM_NAMES[s]}</option>
          ))}
        </select>
      </div>

      <div
        data-testid="dropzone"
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files[0]); }}
        onClick={() => inputRef.current?.click()}
        className={`dropzone rounded-3xl p-12 md:p-16 text-center cursor-pointer ${dragging ? "dropzone-active" : ""}`}
      >
        <input
          ref={inputRef}
          data-testid="file-input"
          type="file"
          accept=".json,.zip"
          className="hidden"
          onChange={(e) => upload(e.target.files[0])}
        />
        {importing ? (
          <>
            <Loader2 size={44} className="mx-auto mb-4 text-accent animate-spin" />
            <p className="font-heading font-bold text-lg">{t("importPage.importing")}</p>
          </>
        ) : (
          <>
            <UploadCloud size={44} className="mx-auto mb-4 text-accent" />
            <p className="font-heading font-bold text-lg mb-1">{t("importPage.dropTitle")}</p>
            <p className="text-sm text-secondary mb-5">{t("importPage.dropDesc")}</p>
            <span className="btn-primary !text-xs pointer-events-none">
              <FileJson size={14} />
              {t("importPage.browse")}
            </span>
          </>
        )}
      </div>

      <p className="text-xs text-secondary mt-3 flex items-center gap-1.5">
        <Sparkles size={12} className="text-accent" />
        {t("importPage.autoTagNote")}
      </p>

      {result && (
        <div className="glass-card rounded-2xl p-6 mt-6 animate-pop" data-testid="import-result">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 size={18} className="text-green-400" />
            <h3 className="font-heading font-bold">{t("importPage.importSuccess")}</h3>
            {result.platform && result.platform !== "demo" && (
              <span className="chip flex items-center gap-1.5 ms-auto">
                <PlatformIcon source={result.platform} size={12} />
                {PLATFORM_NAMES[result.platform] || result.platform}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            {[
              ["added", result.added],
              ["updated", result.updated],
              ["skipped", result.skipped],
              ["newMessages", result.messages],
            ].map(([key, val]) => (
              <div key={key} className="glass-input rounded-xl py-3">
                <p className="font-heading text-2xl font-bold">{fmtNum(val, lang)}</p>
                <p className="text-[11px] text-secondary mt-0.5">{t(`importPage.${key}`)}</p>
              </div>
            ))}
          </div>
          <button data-testid="goto-conversations-btn" onClick={() => navigate("/conversations")} className="btn-primary !text-xs mt-5">
            {t("nav.conversations")}
          </button>
        </div>
      )}

      <div className="mt-10">
        <h2 className="font-heading font-bold mb-4">{t("importPage.howTitle")}</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {Object.keys(PLATFORM_NAMES).map((s) => (
            <div key={s} className="glass-card rounded-2xl p-4 flex gap-3" data-testid={`how-${s}`}>
              <span className="platform-badge shrink-0">
                <PlatformIcon source={s} size={16} />
              </span>
              <div>
                <p className="text-sm font-semibold">{PLATFORM_NAMES[s]}</p>
                <p className="text-xs text-secondary mt-1 leading-relaxed">{t(`importPage.how.${s}`)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card rounded-2xl p-5 mt-6 flex flex-wrap items-center gap-4">
        <Sparkles size={20} className="text-accent shrink-0" />
        <p className="text-sm text-secondary flex-1 min-w-48">{t("dashboard.emptyDesc")}</p>
        <button data-testid="demo-btn" onClick={loadDemo} disabled={demoLoading} className="btn-ghost text-xs">
          {demoLoading ? t("common.loading") : t("dashboard.ctaDemo")}
        </button>
      </div>
    </div>
  );
}
