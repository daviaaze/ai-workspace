import { useState, useEffect } from "react";
import { healthCheck } from "../lib/api";

interface HealthData {
  status: string;
  version: string;
  providers: Record<string, boolean>;
}

export function SettingsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    healthCheck()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10">
        <h1 className="text-sm font-semibold">Settings</h1>
        <p className="text-[10px] text-surface-400">System status & configuration</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Server Status */}
        <Section title="Server">
          {loading ? (
            <div className="flex items-center gap-2 py-2">
              <div className="w-2 h-2 rounded-full bg-accent-400 animate-pulse" />
              <span className="text-sm text-surface-400">Connecting...</span>
            </div>
          ) : health ? (
            <div className="space-y-2">
              <StatusRow label="Status" value={health.status} good={health.status === "ok"} />
              <StatusRow label="Version" value={health.version} />
            </div>
          ) : (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
              <p className="text-red-400 text-sm">Could not connect to server</p>
              <p className="text-[11px] text-red-400/60 mt-1">
                Make sure the API server is running on port 8000
              </p>
            </div>
          )}
        </Section>

        {/* Providers */}
        {health && health.providers && (
          <Section title="Providers">
            <div className="space-y-1.5">
              {Object.entries(health.providers).map(([name, available]) => (
                <StatusRow
                  key={name}
                  label={name}
                  value={available ? "Available" : "Unavailable"}
                  good={available}
                />
              ))}
            </div>
          </Section>
        )}

        {/* App Info */}
        <Section title="About">
          <div className="space-y-2 text-sm text-surface-300">
            <p>
              <strong className="text-white">AI Workspace</strong> is a self-hosted
              AI agent for deep research, coding, and knowledge management.
            </p>
            <ul className="space-y-1 text-[13px]">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Multi-provider LLM routing (Ollama, DeepSeek, Gemini)
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Deep recursive research with critique
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Sandboxed agent with 17 tools
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Budget enforcement & permission gates
              </li>
            </ul>
          </div>
        </Section>

        {/* PWA hint */}
        <Section title="Install on iOS">
          <div className="text-sm text-surface-300">
            <p className="mb-2">
              This app can be installed on your home screen like a native app.
            </p>
            <ol className="list-decimal list-inside space-y-1 text-[13px] text-surface-400">
              <li>Tap the <strong className="text-white">Share</strong> button</li>
              <li>Scroll down and tap <strong className="text-white">Add to Home Screen</strong></li>
              <li>Tap <strong className="text-white">Add</strong> in the top right</li>
            </ol>
          </div>
        </Section>

        {/* Version */}
        <div className="text-center py-4">
          <p className="text-[11px] text-surface-500">AI Workspace v0.1.0</p>
          <p className="text-[10px] text-surface-600 mt-0.5">MIT License</p>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white/5 rounded-xl px-4 py-3">
      <h2 className="text-[11px] font-semibold text-surface-400 uppercase tracking-wider mb-2">
        {title}
      </h2>
      {children}
    </div>
  );
}

function StatusRow({
  label,
  value,
  good,
}: {
  label: string;
  value: string;
  good?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-surface-300">{label}</span>
      <div className="flex items-center gap-1.5">
        {good !== undefined && (
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              good ? "bg-green-400" : "bg-red-400"
            }`}
          />
        )}
        <span className={`text-sm ${good ? "text-green-400" : "text-red-400"}`}>
          {value}
        </span>
      </div>
    </div>
  );
}
