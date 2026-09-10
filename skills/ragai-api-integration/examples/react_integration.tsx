import React, { useState, useEffect, useRef } from 'react';

export interface RagAiCitation {
  document_name: string;
  page_number: number;
  similarity_score: number;
  chunk_id: string;
  snippet?: string;
}

export interface RagAiMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citations?: RagAiCitation[];
  confidence?: number;
  timestamp: string;
}

export interface RagAiChatOptions {
  apiBase?: string;
  apiKey: string;
  role?: 'student' | 'employee' | 'faculty' | 'admin' | 'general';
  department?: string;
  course?: string;
}

export function useRagAiChat(options: RagAiChatOptions) {
  const [messages, setMessages] = useState<RagAiMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am your verified institutional AI assistant. How may I assist you?',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const apiBase = options.apiBase || 'http://localhost:8000';

  const sendMessage = async (query: string) => {
    if (!query.trim() || loading) return;

    const userMsg: RagAiMessage = {
      id: 'msg_' + Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString()
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${apiBase}/api/v1/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': options.apiKey
        },
        body: JSON.stringify({
          query,
          department: options.department || null,
          course: options.course || null,
          role: options.role || 'general',
          session_id: sessionId
        })
      });

      if (!res.ok) {
        throw new Error(`RagAi Server Error: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      setSessionId(data.session_id || sessionId);

      const aiMsg: RagAiMessage = {
        id: 'msg_ai_' + Date.now(),
        sender: 'assistant',
        text: data.answer,
        citations: data.citations,
        confidence: data.confidence_score,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err: any) {
      setError(err.message || 'Failed to communicate with RagAi');
    } finally {
      setLoading(false);
    }
  };

  const submitFeedback = async (messageId: string, feedback: 'up' | 'down', reason?: string) => {
    try {
      await fetch(`${apiBase}/api/v1/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': options.apiKey
        },
        body: JSON.stringify({
          query_id: messageId,
          feedback,
          reason
        })
      });
    } catch (e) {
      console.error('Failed to submit feedback:', e);
    }
  };

  return {
    messages,
    loading,
    error,
    isOpen,
    openModal: () => setIsOpen(true),
    closeModal: () => setIsOpen(false),
    sendMessage,
    submitFeedback
  };
}

export function RagAiChatModal({ chat, title = "RagAi Assistant" }: { chat: ReturnType<typeof useRagAiChat>, title?: string }) {
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages, chat.loading]);

  if (!chat.isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      right: 24,
      width: 420,
      height: 600,
      background: '#fff',
      borderRadius: 16,
      boxShadow: '0 20px 50px rgba(0,0,0,0.2)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 999999,
      overflow: 'hidden',
      border: '1px solid #cbd5e1'
    }}>
      <div style={{
        background: '#0f172a',
        color: '#fff',
        padding: '14px 18px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <strong style={{ fontSize: 15 }}>{title}</strong>
        <button onClick={chat.closeModal} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: 20, cursor: 'pointer' }}>&times;</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16, background: '#f8fafc', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {chat.messages.map(m => (
          <div key={m.id} style={{
            alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
            background: m.sender === 'user' ? '#2563eb' : '#ffffff',
            color: m.sender === 'user' ? '#ffffff' : '#1e293b',
            padding: '10px 14px',
            borderRadius: 12,
            maxWidth: '85%',
            border: m.sender === 'assistant' ? '1px solid #e2e8f0' : 'none',
            fontSize: 13.5
          }}>
            <div>{m.text}</div>
            {m.citations && m.citations.length > 0 && (
              <div style={{ marginTop: 8, fontSize: 11, color: '#64748b', borderTop: '1px solid #f1f5f9', paddingTop: 4 }}>
                <strong>Sources:</strong>
                {m.citations.map(c => (
                  <span key={c.chunk_id} style={{ display: 'inline-block', background: '#e2e8f0', padding: '2px 6px', borderRadius: 4, margin: '2px 4px 2px 0' }}>
                    📄 {c.document_name} (p.{c.page_number})
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {chat.loading && <div style={{ color: '#64748b', fontSize: 13 }}>Thinking...</div>}
        {chat.error && <div style={{ color: '#dc2626', fontSize: 13 }}>{chat.error}</div>}
        <div ref={endRef} />
      </div>

      <div style={{ padding: 12, borderTop: '1px solid #e2e8f0', display: 'flex', gap: 8, background: '#fff' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') {
              chat.sendMessage(input);
              setInput('');
            }
          }}
          placeholder="Type your question..."
          style={{ flex: 1, padding: '10px 12px', border: '1px solid #cbd5e1', borderRadius: 8, outline: 'none' }}
        />
        <button
          onClick={() => {
            chat.sendMessage(input);
            setInput('');
          }}
          style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '0 16px', cursor: 'pointer', fontWeight: 500 }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
