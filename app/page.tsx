"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check, Loader2, Youtube, Github, ExternalLink } from "lucide-react";

type StageStatus = "idle" | "queued" | "running" | "complete" | "failed";

interface Stage {
  id: string;
  name: string;
  description: string;
  status: StageStatus;
  progress?: number;
}

const INITIAL_STAGES: Stage[] = [
  { id: "ingest", name: "1. Ingest", description: "Downloading video + metadata", status: "idle" },
  { id: "hybrid", name: "2. Hybrid Transcribe", description: "Whisper + vision analysis", status: "idle" },
  { id: "analyze", name: "3. Analyze + Extract", description: "Multimodal LLM extraction", status: "idle" },
  { id: "synthesize", name: "4. Synthesize", description: "Code + UI generation", status: "idle" },
  { id: "validate", name: "5. Validate + Test", description: "Typecheck + e2e", status: "idle" },
  { id: "deploy", name: "6. Build & Deploy", description: "Vercel + GitHub", status: "idle" },
];

export default function Home() {
  const [url, setUrl] = useState("");
  const [stages, setStages] = useState<Stage[]>(INITIAL_STAGES);
  const [isRunning, setIsRunning] = useState(false);
  const [liveUrl, setLiveUrl] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);

  const isValidYoutube = (u: string) =>
    /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/.test(u.trim());

  const startForge = async () => {
    if (!isValidYoutube(url) || isRunning) return;
    setIsRunning(true);
    setLiveUrl(null);
    setShowToast(false);

    // Simulate the pipeline (real backend coming next)
    const order = ["ingest", "hybrid", "analyze", "synthesize", "validate", "deploy"];
    for (let i = 0; i < order.length; i++) {
      const id = order[i];
      setStages((prev) =>
        prev.map((s) =>
          s.id === id
            ? { ...s, status: "running", progress: 0 }
            : s.status === "running"
            ? { ...s, status: "complete", progress: 100 }
            : s
        )
      );

      // Fake progress
      for (let p = 0; p <= 100; p += 20) {
        await new Promise((r) => setTimeout(r, 180));
        setStages((prev) =>
          prev.map((s) => (s.id === id ? { ...s, progress: p } : s))
        );
      }

      setStages((prev) =>
        prev.map((s) =>
          s.id === id ? { ...s, status: "complete", progress: 100 } : s
        )
      );
    }

    setLiveUrl("https://forge.app/demo-" + Math.random().toString(36).slice(2, 8));
    setShowToast(true);
    setIsRunning(false);
  };

  return (
    <div className="min-h-screen bg-grid flex flex-col">
      {/* Top bar */}
      <header className="border-b border-border bg-black/40 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center">
              <span className="text-primary font-bold text-sm">F</span>
            </div>
            <span className="font-semibold tracking-tight text-lg">FORGE</span>
            <span className="text-xs text-muted ml-2 hidden sm:inline">YouTube → Live App</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted">
            <a href="https://github.com/groupthinking/forge" target="_blank" rel="noreferrer" className="hover:text-white transition">
              <Github className="w-4 h-4" />
            </a>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            What should we build?
          </h1>
          <p className="text-muted text-lg max-w-xl mx-auto">
            Paste any YouTube tutorial or demo. Forge reverse-engineers it and ships a live app.
          </p>
        </div>

        {/* Input */}
        <div className="flex flex-col sm:flex-row gap-3 max-w-2xl mx-auto mb-16">
          <div className="relative flex-1">
            <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste YouTube URL of any tutorial or demo..."
              className="w-full h-14 pl-12 pr-4 rounded-xl bg-card border border-border focus:border-primary focus:ring-2 focus:ring-primary/30 outline-none transition text-white placeholder:text-muted"
              disabled={isRunning}
              onKeyDown={(e) => e.key === "Enter" && startForge()}
            />
          </div>
          <button
            onClick={startForge}
            disabled={!isValidYoutube(url) || isRunning}
            className="h-14 px-8 rounded-xl bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium flex items-center justify-center gap-2 transition shadow-lg shadow-primary/20"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Forging...
              </>
            ) : (
              <>
                Forge <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>

        {/* Progress cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {stages.map((stage) => (
            <motion.div
              key={stage.id}
              layout
              className={`rounded-xl border p-5 transition-all ${
                stage.status === "running"
                  ? "border-primary/50 bg-primary/5 shadow-lg shadow-primary/10"
                  : stage.status === "complete"
                  ? "border-success/30 bg-success/5"
                  : "border-border bg-card"
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-medium">{stage.name}</h3>
                {stage.status === "complete" && (
                  <div className="w-6 h-6 rounded-full bg-success/20 flex items-center justify-center">
                    <Check className="w-3.5 h-3.5 text-success" />
                  </div>
                )}
                {stage.status === "running" && (
                  <Loader2 className="w-5 h-5 text-primary animate-spin" />
                )}
              </div>
              <p className="text-sm text-muted mb-3">{stage.description}</p>
              {stage.status === "running" && (
                <div className="h-1.5 rounded-full bg-border overflow-hidden">
                  <motion.div
                    className="h-full bg-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${stage.progress || 0}%` }}
                    transition={{ duration: 0.2 }}
                  />
                </div>
              )}
              {stage.status === "complete" && (
                <p className="text-xs text-success">✓ complete</p>
              )}
              {stage.status === "idle" && (
                <p className="text-xs text-muted">waiting</p>
              )}
            </motion.div>
          ))}
        </div>

        {/* Live preview / result */}
        <AnimatePresence>
          {liveUrl && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl border border-success/30 bg-success/5 p-8 text-center"
            >
              <div className="inline-flex items-center gap-2 text-success mb-4">
                <Check className="w-6 h-6" />
                <span className="font-semibold text-lg">Deployed!</span>
              </div>
              <p className="text-muted mb-6">Your app is live and the source is in GitHub.</p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <a
                  href={liveUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-success text-black font-medium hover:bg-success/90 transition"
                >
                  Open Live App <ExternalLink className="w-4 h-4" />
                </a>
                <a
                  href="https://github.com/groupthinking/forge"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-border hover:bg-card transition"
                >
                  <Github className="w-4 h-4" /> View Source
                </a>
              </div>
              <p className="mt-4 text-sm text-muted font-mono">{liveUrl}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Toast */}
        <AnimatePresence>
          {showToast && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="fixed bottom-8 left-1/2 -translate-x-1/2 px-6 py-3 rounded-full bg-success text-black font-medium shadow-2xl flex items-center gap-2 z-50"
            >
              <Check className="w-5 h-5" />
              Deployed! Live at forge.app/xyz
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="border-t border-border py-6 text-center text-sm text-muted">
        <p>
          FORGE · Built with Next.js 15 ·{" "}
          <a href="https://github.com/groupthinking/forge-spec" className="underline hover:text-white">
            Full Spec
          </a>
        </p>
      </footer>
    </div>
  );
}
