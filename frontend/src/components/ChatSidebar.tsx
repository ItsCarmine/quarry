import { useState, useRef, useEffect } from "react";
import type { BackendInfo } from "../types";

interface Message {
  role: "user" | "system";
  content: string;
  timestamp: Date;
}

interface Props {
  onSubmit: (query: string) => void;
  stage: string;
  detail: string;
  error: string;
  backends: BackendInfo[];
  disabled: boolean;
}

const STATUS_ICON: Record<string, string> = {
  searching: "\u23F3",  // hourglass
  done: "\u2705",       // green check
  failed: "\u274C",     // red x
};

export function ChatSidebar({ onSubmit, stage, detail, error, backends, disabled }: Props) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const lastStageRef = useRef("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Add system messages for major stage transitions only
  useEffect(() => {
    if (!stage || stage === lastStageRef.current) return;
    lastStageRef.current = stage;

    if (stage === "synthesizing") {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "All backends complete. Opus 4.6 synthesizing...", timestamp: new Date() },
      ]);
    } else if (stage === "generating") {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "Generating Typst report...", timestamp: new Date() },
      ]);
    } else if (stage === "done") {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "Report complete.", timestamp: new Date() },
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
  }, [messages, backends]);

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
        {messages.length === 0 && backends.length === 0 && (
          <div className="chat-hint">
            Describe what you want to research...
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <span className="chat-msg-content">{msg.content}</span>
          </div>
        ))}

        {backends.length > 0 && stage !== "done" && (
          <div className="backend-progress">
            <div className="backend-progress-title">Research Backends</div>
            {backends.map((b) => (
              <div key={b.name} className={`backend-row backend-${b.status}`}>
                <span className="backend-icon">{STATUS_ICON[b.status] || "\u23F3"}</span>
                <span className="backend-name">{b.name}</span>
                <span className="backend-status">
                  {b.status === "searching" && "Searching..."}
                  {b.status === "done" && "Complete"}
                  {b.status === "failed" && "Failed"}
                </span>
              </div>
            ))}
            {stage === "synthesizing" && (
              <div className="backend-row backend-synth">
                <span className="backend-icon">{"\u{1F9E0}"}</span>
                <span className="backend-name">Opus 4.6 Mayor</span>
                <span className="backend-status">Synthesizing...</span>
              </div>
            )}
            {stage === "generating" && (
              <div className="backend-row backend-done">
                <span className="backend-icon">{"\u{1F4DD}"}</span>
                <span className="backend-name">Report</span>
                <span className="backend-status">Generating...</span>
              </div>
            )}
          </div>
        )}

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
