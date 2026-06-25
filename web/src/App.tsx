import { useState } from "react";
import { ChatPage } from "./pages/ChatPage";
import { SearchPage } from "./pages/SearchPage";
import { AgentPage } from "./pages/AgentPage";
import { SettingsPage } from "./pages/SettingsPage";

type Tab = "chat" | "search" | "agent" | "settings";

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  return (
    <div className="flex flex-col h-dvh bg-[#0a0a0f] safe-top safe-bottom">
      {/* Content area */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "chat" && <ChatPage />}
        {activeTab === "search" && <SearchPage />}
        {activeTab === "agent" && <AgentPage />}
        {activeTab === "settings" && <SettingsPage />}
      </main>

      {/* iOS-style tab bar */}
      <nav className="flex-shrink-0 border-t border-white/10 bg-[#0a0a0f]/90 backdrop-blur-xl safe-bottom">
        <div className="flex items-center justify-around py-1">
          <TabButton
            icon={<ChatIcon />}
            label="Chat"
            active={activeTab === "chat"}
            onClick={() => setActiveTab("chat")}
          />
          <TabButton
            icon={<SearchIcon />}
            label="Research"
            active={activeTab === "search"}
            onClick={() => setActiveTab("search")}
          />
          <TabButton
            icon={<AgentIcon />}
            label="Agent"
            active={activeTab === "agent"}
            onClick={() => setActiveTab("agent")}
          />
          <TabButton
            icon={<GearIcon />}
            label="Settings"
            active={activeTab === "settings"}
            onClick={() => setActiveTab("settings")}
          />
        </div>
      </nav>
    </div>
  );
}

function TabButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-0.5 px-4 py-1.5 transition-colors no-select ${
        active ? "text-accent-400" : "text-surface-400"
      }`}
    >
      {icon}
      <span className="text-[10px] font-medium tracking-tight">{label}</span>
    </button>
  );
}

function ChatIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
      <path d="M11 7v8" />
      <path d="M7 11h8" />
    </svg>
  );
}

function AgentIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}
