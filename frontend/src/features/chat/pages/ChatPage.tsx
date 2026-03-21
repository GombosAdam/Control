import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Trash2, ChevronDown, ChevronRight, Bot, User } from 'lucide-react';
import { chatApi, type ChatResponse } from '../../../services/api/chat';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sql?: string | null;
  row_count?: number | null;
  error?: string | null;
  response_time_ms?: number | null;
  retry_count?: number;
  timestamp: Date;
}

const SUGGESTIONS = [
  'Hány számla van a rendszerben?',
  'Melyik osztály lépte túl a budget-ot?',
  'Mi a top 5 szállító összeg szerint?',
  'Mennyi a jóváhagyásra váró számlák összértéke?',
];

export function ChatPage() {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedSql, setExpandedSql] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const toggleSql = (id: string) => {
    setExpandedSql(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response: ChatResponse = await chatApi.ask(question.trim());
      const aiMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.answer,
        sql: response.sql,
        row_count: response.row_count,
        error: response.error,
        response_time_ms: response.response_time_ms,
        retry_count: response.retry_count,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Hiba történt a kérdés feldolgozása közben. Kérlek próbáld újra.',
        error: err?.message || 'Ismeretlen hiba',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const clearChat = () => {
    setMessages([]);
    setExpandedSql(new Set());
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 40px)', background: '#f8f9fa' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px', borderBottom: '1px solid #e5e7eb',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: '#fff',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '10px', background: '#8B5CF6',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
          }}>
            <Bot size={22} />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#111' }}>
              {t('modules.chat')}
            </h1>
            <span style={{ fontSize: '12px', color: '#888' }}>
              Kérdezz bármit a pénzügyi adatokról
            </span>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 14px', borderRadius: '8px', border: '1px solid #e5e7eb',
              background: '#fff', cursor: 'pointer', color: '#666', fontSize: '13px',
            }}
          >
            <Trash2 size={14} /> Törlés
          </button>
        )}
      </div>

      {/* Messages area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
        {messages.length === 0 && !loading ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', gap: '24px',
          }}>
            <div style={{
              width: '72px', height: '72px', borderRadius: '20px', background: '#8B5CF6',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
            }}>
              <Bot size={36} />
            </div>
            <div style={{ textAlign: 'center' }}>
              <h2 style={{ margin: '0 0 8px', fontSize: '20px', fontWeight: 600, color: '#333' }}>
                Pénzügyi Asszisztens
              </h2>
              <p style={{ margin: 0, color: '#888', fontSize: '14px' }}>
                Tedd fel kérdéseidet a rendszer pénzügyi adatairól
              </p>
            </div>
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: '10px',
              justifyContent: 'center', maxWidth: '600px',
            }}>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  style={{
                    padding: '10px 16px', borderRadius: '20px',
                    border: '1px solid #e0e0e0', background: '#fff',
                    cursor: 'pointer', fontSize: '13px', color: '#555',
                    transition: 'all 150ms',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#8B5CF6';
                    e.currentTarget.style.color = '#8B5CF6';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#e0e0e0';
                    e.currentTarget.style.color = '#555';
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div style={{
                  display: 'flex', gap: '10px', maxWidth: '85%',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                }}>
                  {/* Avatar */}
                  <div style={{
                    width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
                    background: msg.role === 'user' ? '#3B82F6' : '#8B5CF6',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff',
                  }}>
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>

                  {/* Bubble */}
                  <div>
                    <div style={{
                      padding: '12px 16px', borderRadius: '12px',
                      background: msg.role === 'user' ? '#3B82F6' : '#fff',
                      color: msg.role === 'user' ? '#fff' : '#333',
                      border: msg.role === 'user' ? 'none' : '1px solid #e5e7eb',
                      fontSize: '14px', lineHeight: 1.6,
                      whiteSpace: 'pre-wrap',
                    }}>
                      {msg.content}
                    </div>

                    {/* SQL collapsible */}
                    {msg.sql && (
                      <div style={{ marginTop: '8px' }}>
                        <button
                          onClick={() => toggleSql(msg.id)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '4px',
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#888', fontSize: '12px', padding: '4px 0',
                          }}
                        >
                          {expandedSql.has(msg.id) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          SQL lekérdezés
                          {msg.row_count !== null && msg.row_count !== undefined && (
                            <span style={{
                              marginLeft: '6px', padding: '1px 6px', borderRadius: '10px',
                              background: '#f0f0f0', fontSize: '11px',
                            }}>
                              {msg.row_count} sor
                            </span>
                          )}
                          {msg.response_time_ms != null && (
                            <span style={{
                              marginLeft: '6px', padding: '1px 6px', borderRadius: '10px',
                              background: '#EEF2FF', color: '#6366F1', fontSize: '11px',
                            }}>
                              {(msg.response_time_ms / 1000).toFixed(1)}s
                            </span>
                          )}
                          {(msg.retry_count ?? 0) > 0 && (
                            <span style={{
                              marginLeft: '6px', padding: '1px 6px', borderRadius: '10px',
                              background: '#FEF3C7', color: '#D97706', fontSize: '11px',
                            }}>
                              {msg.retry_count} retry
                            </span>
                          )}
                        </button>
                        {expandedSql.has(msg.id) && (
                          <pre style={{
                            margin: '4px 0 0', padding: '12px', borderRadius: '8px',
                            background: '#1e1e2e', color: '#cdd6f4', fontSize: '12px',
                            overflow: 'auto', maxHeight: '200px', lineHeight: 1.5,
                          }}>
                            {msg.sql}
                          </pre>
                        )}
                      </div>
                    )}

                    {/* Error indicator */}
                    {msg.error && (
                      <div style={{
                        marginTop: '6px', fontSize: '11px', color: '#EF4444',
                        display: 'flex', alignItems: 'center', gap: '4px',
                      }}>
                        Hiba: {msg.error}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {loading && (
              <div style={{ display: 'flex', gap: '10px' }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
                  background: '#8B5CF6', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', color: '#fff',
                }}>
                  <Bot size={16} />
                </div>
                <div style={{
                  padding: '12px 16px', borderRadius: '12px', background: '#fff',
                  border: '1px solid #e5e7eb', display: 'flex', gap: '4px',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {[0, 1, 2].map(i => (
                      <div
                        key={i}
                        style={{
                          width: '8px', height: '8px', borderRadius: '50%',
                          background: '#8B5CF6', opacity: 0.4,
                          animation: `chatBounce 1.4s infinite ${i * 0.2}s`,
                        }}
                      />
                    ))}
                  </div>
                  <style>{`
                    @keyframes chatBounce {
                      0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
                      40% { transform: translateY(-6px); opacity: 1; }
                    }
                  `}</style>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div style={{ padding: '16px 24px', borderTop: '1px solid #e5e7eb', background: '#fff' }}>
        <form
          onSubmit={handleSubmit}
          style={{
            maxWidth: '800px', margin: '0 auto', display: 'flex', gap: '10px',
          }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Kérdezz valamit a pénzügyi adatokról..."
            disabled={loading}
            style={{
              flex: 1, padding: '12px 16px', borderRadius: '12px',
              border: '1px solid #e0e0e0', fontSize: '14px',
              outline: 'none', background: loading ? '#f9f9f9' : '#fff',
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = '#8B5CF6'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = '#e0e0e0'; }}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            style={{
              width: '44px', height: '44px', borderRadius: '12px',
              border: 'none', cursor: input.trim() && !loading ? 'pointer' : 'default',
              background: input.trim() && !loading ? '#8B5CF6' : '#e0e0e0',
              color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 150ms',
            }}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
