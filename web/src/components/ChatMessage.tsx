import { useState } from "react";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 animate-fade-in`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-accent-600 text-white rounded-br-md"
            : "bg-white/5 text-white/90 rounded-bl-md"
        }`}
      >
        {isUser ? (
          <p className="text-[15px] leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose prose-invert text-[15px] leading-relaxed">
            <MarkdownContent content={message.content} />
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 bg-accent-400 ml-0.5 cursor-blink" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Simple Markdown renderer for chat messages */
function MarkdownContent({ content }: { content: string }) {
  // Simple markdown parsing — inline code, code blocks, bold, lists
  const parts: React.ReactNode[] = [];
  let remaining = content;
  let key = 0;

  while (remaining.length > 0) {
    // Code blocks ```lang ... ```
    const codeBlockMatch = remaining.match(/```(\w*)\n?([\s\S]*?)```/);
    if (codeBlockMatch && codeBlockMatch.index !== undefined) {
      // Text before code block
      if (codeBlockMatch.index > 0) {
        parts.push(
          <span key={key++}>
            {renderInlineMarkdown(remaining.slice(0, codeBlockMatch.index))}
          </span>
        );
      }
      parts.push(
        <pre key={key++} className="my-2 text-xs">
          <code>{codeBlockMatch[2]}</code>
        </pre>
      );
      remaining = remaining.slice(codeBlockMatch.index + codeBlockMatch[0].length);
      continue;
    }

    // Inline markdown
    parts.push(
      <span key={key++}>{renderInlineMarkdown(remaining)}</span>
    );
    break;
  }

  return <>{parts}</>;
}

function renderInlineMarkdown(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold **text**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch && boldMatch.index !== undefined) {
      if (boldMatch.index > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, boldMatch.index)}</span>);
      }
      parts.push(<strong key={key++}>{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      continue;
    }

    // Inline code `text`
    const codeMatch = remaining.match(/`(.+?)`/);
    if (codeMatch && codeMatch.index !== undefined) {
      if (codeMatch.index > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, codeMatch.index)}</span>);
      }
      parts.push(
        <code key={key++} className="bg-white/10 px-1.5 py-0.5 rounded text-sm">
          {codeMatch[1]}
        </code>
      );
      remaining = remaining.slice(codeMatch.index + codeMatch[0].length);
      continue;
    }

    // Links [text](url)
    const linkMatch = remaining.match(/\[(.+?)\]\((.+?)\)/);
    if (linkMatch && linkMatch.index !== undefined) {
      if (linkMatch.index > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, linkMatch.index)}</span>);
      }
      parts.push(
        <a key={key++} href={linkMatch[2]} target="_blank" rel="noopener noreferrer" className="text-accent-400 underline">
          {linkMatch[1]}
        </a>
      );
      remaining = remaining.slice(linkMatch.index + linkMatch[0].length);
      continue;
    }

    // Newlines
    const nlMatch = remaining.match(/\n\n/);
    if (nlMatch && nlMatch.index !== undefined) {
      if (nlMatch.index > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, nlMatch.index)}</span>);
      }
      parts.push(<br key={key++} />);
      parts.push(<br key={key++} />);
      remaining = remaining.slice(nlMatch.index + nlMatch[0].length);
      continue;
    }

    // Single newline
    const singleNl = remaining.match(/\n/);
    if (singleNl && singleNl.index !== undefined) {
      if (singleNl.index > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, singleNl.index)}</span>);
      }
      parts.push(<br key={key++} />);
      remaining = remaining.slice(singleNl.index + 1);
      continue;
    }

    parts.push(<span key={key++}>{remaining}</span>);
    break;
  }

  return parts;
}
