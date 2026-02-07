import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "system";
  content: string;
  timestamp: Date;
}

interface Props {
  onSubmit: (query: string) => void;
  stage: string;
  error: string;
  disabled: boolean;
}

export function ChatSidebar({ onSubmit, stage, error, disabled }: Props) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Add system messages for stage updates
  useEffect(() => {
    if (stage) {
      const labels: Record<string, string> = {
        dispatching: "Querying research backends...",
        synthesizing: "Synthesizing findings...",
        generating: "Generating Typst report...",
        done: "Report complete.",
      };
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: labels[stage] || stage,
          timestamp: new Date(),
        },
      ]);
    }
  }, [stage]);

  useEffect(() => {
    if (error) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${error}`, timestamp: new Date() },
      ]);
    }
  }, [error]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || disabled) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: query, timestamp: new Date() },
    ]);
    setInput("");
    onSubmit(query);
  };

  return (
    <aside className="chat-sidebar">
      <div className="chat-header">
        <h3>Research Chat</h3>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-hint">
            Describe what you want to research...
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <span className="chat-msg-content">{msg.content}</span>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Enter a research query..."
          disabled={disabled}
          rows={3}
        />
        <button
          className="chat-submit"
          type="submit"
          disabled={disabled || !input.trim()}
        >
          {disabled ? "Researching..." : "Research"}
        </button>
      </form>
    </aside>
  );
}
