import { useRef, useState } from "react";
import { Download, FileJson, Upload, Tags, Trash2, Moon, Sun, Languages } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/context/AppContext";
import { api, API } from "@/lib/api";

export default function Settings() {
  const { t, lang, setLang, theme, setTheme } = useApp();
  const [confirmClear, setConfirmClear] = useState(false);
  const [busy, setBusy] = useState(null);
  const restoreRef = useRef(null);

  const runAutotag = async () => {
    setBusy("autotag");
    try {
      const { data } = await api.post("/autotag");
      toast.success(t("settings.autotagDone").replace("{n}", data.tagged));
    } catch {
      toast.error(t("common.error"));
    } finally {
      setBusy(null);
    }
  };

  const restore = async (file) => {
    if (!file) return;
    setBusy("restore");
    const form = new FormData();
    form.append("file", file);
    try {
      const { data } = await api.post("/import/archive", form);
      toast.success(`${t("settings.restored")} (+${data.added})`);
    } catch (err) {
      toast.error(err.response?.data?.detail || t("common.error"));
    } finally {
      setBusy(null);
      if (restoreRef.current) restoreRef.current.value = "";
    }
  };

  const clearArchive = async () => {
    await api.delete("/archive");
    setConfirmClear(false);
    toast.success(t("settings.cleared"));
  };

  return (
    <div data-testid="settings-page" className="max-w-3xl">
      <header className="mb-8">
        <h1 className="font-heading text-3xl font-bold tracking-tight">{t("settings.title")}</h1>
        <p className="text-secondary mt-1">{t("settings.subtitle")}</p>
      </header>

      <section className="glass-card rounded-2xl p-6 mb-4" data-testid="appearance-section">
        <h2 className="font-heading font-bold mb-4">{t("settings.appearance")}</h2>
        <div className="flex flex-wrap gap-6">
          <div>
            <p className="text-xs text-secondary mb-2">{t("settings.language")}</p>
            <div className="flex gap-2">
              <button
                data-testid="lang-ar-btn"
                onClick={() => setLang("ar")}
                className={`chip flex items-center gap-1.5 ${lang === "ar" ? "chip-active" : ""}`}
              >
                <Languages size={12} /> العربية
              </button>
              <button
                data-testid="lang-en-btn"
                onClick={() => setLang("en")}
                className={`chip flex items-center gap-1.5 ${lang === "en" ? "chip-active" : ""}`}
              >
                <Languages size={12} /> English
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs text-secondary mb-2">{t("settings.theme")}</p>
            <div className="flex gap-2">
              <button
                data-testid="theme-dark-btn"
                onClick={() => setTheme("dark")}
                className={`chip flex items-center gap-1.5 ${theme === "dark" ? "chip-active" : ""}`}
              >
                <Moon size={12} /> {t("settings.dark")}
              </button>
              <button
                data-testid="theme-light-btn"
                onClick={() => setTheme("light")}
                className={`chip flex items-center gap-1.5 ${theme === "light" ? "chip-active" : ""}`}
              >
                <Sun size={12} /> {t("settings.light")}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="glass-card rounded-2xl p-6 mb-4" data-testid="export-all-section">
        <h2 className="font-heading font-bold mb-1">{t("settings.exportAllTitle")}</h2>
        <p className="text-sm text-secondary mb-4">{t("settings.exportAllDesc")}</p>
        <a data-testid="export-all-btn" href={`${API}/export/all`} className="btn-primary !text-xs inline-flex">
          <Download size={14} />
          {t("settings.exportAllBtn")}
        </a>
      </section>

      <section className="glass-card rounded-2xl p-6 mb-4" data-testid="backup-section">
        <h2 className="font-heading font-bold mb-1">{t("settings.archiveTitle")}</h2>
        <p className="text-sm text-secondary mb-4">{t("settings.archiveDesc")}</p>
        <div className="flex flex-wrap gap-2">
          <a data-testid="export-json-btn" href={`${API}/export/archive`} className="btn-ghost !text-xs inline-flex">
            <FileJson size={14} />
            {t("settings.exportJsonBtn")}
          </a>
          <button
            data-testid="restore-json-btn"
            onClick={() => restoreRef.current?.click()}
            disabled={busy === "restore"}
            className="btn-ghost !text-xs"
          >
            <Upload size={14} />
            {busy === "restore" ? t("common.loading") : t("settings.importJsonBtn")}
          </button>
          <input
            ref={restoreRef}
            data-testid="restore-file-input"
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => restore(e.target.files[0])}
          />
        </div>
      </section>

      <section className="glass-card rounded-2xl p-6 mb-4" data-testid="autotag-section">
        <h2 className="font-heading font-bold mb-1">{t("settings.autotagTitle")}</h2>
        <p className="text-sm text-secondary mb-4">{t("settings.autotagDesc")}</p>
        <button data-testid="autotag-btn" onClick={runAutotag} disabled={busy === "autotag"} className="btn-ghost !text-xs">
          <Tags size={14} />
          {busy === "autotag" ? t("common.loading") : t("settings.autotagBtn")}
        </button>
      </section>

      <section className="glass-card rounded-2xl p-6 border-red-500/20" data-testid="danger-section">
        <h2 className="font-heading font-bold mb-1 text-red-400">{t("settings.dangerTitle")}</h2>
        <p className="text-sm text-secondary mb-4">{t("settings.dangerDesc")}</p>
        <button data-testid="clear-archive-btn" onClick={() => setConfirmClear(true)} className="btn-danger !text-xs">
          <Trash2 size={14} />
          {t("settings.clearBtn")}
        </button>
      </section>

      {confirmClear && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center px-4 search-backdrop" onClick={() => setConfirmClear(false)}>
          <div className="glass-modal rounded-2xl p-6 max-w-sm w-full animate-pop" onClick={(e) => e.stopPropagation()} data-testid="clear-confirm-modal">
            <h3 className="font-heading font-bold text-lg mb-2">{t("settings.clearTitle")}</h3>
            <p className="text-sm text-secondary mb-6">{t("settings.clearDesc")}</p>
            <div className="flex justify-end gap-2">
              <button data-testid="clear-cancel-btn" onClick={() => setConfirmClear(false)} className="btn-ghost text-xs">
                {t("common.cancel")}
              </button>
              <button data-testid="clear-confirm-btn" onClick={clearArchive} className="btn-danger text-xs">
                {t("settings.clearBtn")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
