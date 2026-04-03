import { useState, useRef, useEffect } from 'react';
import { Card } from '../shared/Card';
import { useChat } from '../../hooks/useAgents';
import type { ChatMessage } from '../../types/api';

const SUGGESTED_PROMPTS = [
  'What are the top risks?',
  'Simulate Suez Canal closure',
  'Why was order PO-2025-0042 rerouted?',
];

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3 animate-fade-in`}>
      <div
        className="max-w-[85%] rounded-lg px-3 py-2"
        style={{
          background: isUser ? 'var(--wr-cyan-dim)' : 'var(--wr-bg-elevated)',
          border: `1px solid ${isUser ? 'rgba(88, 166, 255, 0.3)' : 'var(--wr-border)'}`,
        }}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--wr-text-primary)' }}>
          {message.content}
        </p>
        <span
          className="block text-[10px] mt-1 font-mono-numbers"
          style={{ color: 'var(--wr-text-muted)', textAlign: isUser ? 'right' : 'left' }}
        >
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div
        className="rounded-lg px-4 py-3 flex items-center gap-2"
        style={{ background: 'var(--wr-bg-elevated)', border: '1px solid var(--wr-border)' }}
      >
        <span className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{
                background: 'var(--wr-cyan)',
                animation: `pulse-dot 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </span>
        <span className="text-xs" style={{ color: 'var(--wr-text-muted)' }}>
          Agent is thinking...
        </span>
      </div>
    </div>
  );
}

export function ChatPanel({ className }: { className?: string }) {
  const { messages, sendMessage, isLoading, error } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    sendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className={`flex flex-col ${className ?? ''}`} title="Command Chat" noPadding>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2 min-h-[200px] max-h-[400px]">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full gap-3 py-8">
            <span className="text-2xl" style={{ color: 'var(--wr-text-muted)' }}>
              &gt;_
            </span>
            <p className="text-xs text-center" style={{ color: 'var(--wr-text-muted)' }}>
              Ask about your supply chain, simulate scenarios, or investigate anomalies
            </p>

            {/* Suggested prompts */}
            <div className="flex flex-wrap gap-2 mt-2 justify-center">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  className="text-xs px-3 py-1.5 rounded-full transition-all duration-150"
                  style={{
                    background: 'var(--wr-bg-elevated)',
                    border: '1px solid var(--wr-border)',
                    color: 'var(--wr-text-secondary)',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => {
                    (e.target as HTMLElement).style.borderColor = 'var(--wr-cyan)';
                    (e.target as HTMLElement).style.color = 'var(--wr-cyan)';
                  }}
                  onMouseLeave={(e) => {
                    (e.target as HTMLElement).style.borderColor = 'var(--wr-border)';
                    (e.target as HTMLElement).style.color = 'var(--wr-text-secondary)';
                  }}
                  onClick={() => {
                    sendMessage(prompt);
                    inputRef.current?.focus();
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {isLoading && <ThinkingIndicator />}

        {error && (
          <div
            className="mb-3 px-3 py-2 rounded-lg text-xs"
            style={{ background: 'var(--wr-red-dim)', color: 'var(--wr-red)', border: '1px solid rgba(248, 81, 73, 0.3)' }}
          >
            Error: {(error as Error).message}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{ borderTop: '1px solid var(--wr-border)' }}
      >
        <input
          ref={inputRef}
          type="text"
          className="flex-1 px-3 py-2 rounded-md text-sm outline-none placeholder:text-[#484f58]"
          style={{
            background: 'var(--wr-bg-primary)',
            border: '1px solid var(--wr-border)',
            color: 'var(--wr-text-primary)',
          }}
          placeholder="Ask the supply chain AI..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={(e) => {
            (e.target as HTMLElement).style.borderColor = 'var(--wr-cyan)';
          }}
          onBlur={(e) => {
            (e.target as HTMLElement).style.borderColor = 'var(--wr-border)';
          }}
          disabled={isLoading}
        />
        <button
          className="px-4 py-2 rounded-md text-sm font-semibold transition-all duration-150 flex-shrink-0"
          style={{
            background: input.trim() && !isLoading ? 'var(--wr-cyan-dim)' : 'var(--wr-bg-primary)',
            color: input.trim() && !isLoading ? 'var(--wr-cyan)' : 'var(--wr-text-muted)',
            border: `1px solid ${input.trim() && !isLoading ? 'rgba(88, 166, 255, 0.3)' : 'var(--wr-border)'}`,
            cursor: input.trim() && !isLoading ? 'pointer' : 'default',
          }}
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
        >
          Send
        </button>
      </div>
    </Card>
  );
}
