/** Animated thinking indicator — three bouncing dots */
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-1">
      <span className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" style={{ animationDelay: "0ms" }} />
      <span className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" style={{ animationDelay: "150ms" }} />
      <span className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" style={{ animationDelay: "300ms" }} />
    </div>
  );
}
