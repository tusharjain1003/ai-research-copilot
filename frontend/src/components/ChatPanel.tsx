import { useState, useEffect, useCallback, type FormEvent } from "react";
import { api } from "../api";
import type { ChatMessage } from "../types";

interface ChatPanelProps {
  sessionId: string;
}

function ChatPanel({ sessionId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMessages = useCallback(async () => {
    try {
      const res = await api.getChatMessages(sessionId);
      setMessages(res.messages);
    } catch {
      // silently ignore – chat is a secondary feature
    }
  }, [sessionId]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);
    setError(null);
    try {
      const assistantMsg = await api.sendMessage(sessionId, text);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", content: text, created_at: new Date().toISOString() },
        assistantMsg,
      ]);
    } catch {
      setError("Failed to send message. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-panel">
      <h3>Follow-up Chat</h3>
      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty">Ask a follow-up question about this research.</p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`chat-message chat-message-${m.role}`}>
            <strong>{m.role === "user" ? "You" : "Research Copilot"}:</strong>
            <p>{m.content}</p>
          </div>
        ))}
        {error && <p className="chat-error">{error}</p>}
      </div>
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a follow-up question..."
        />
        <button type="submit" className="btn btn-primary" disabled={sending}>
          {sending ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}

export default ChatPanel;
