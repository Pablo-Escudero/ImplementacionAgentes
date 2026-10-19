import { useState, useEffect, useRef } from 'react';
import api from '../api';

export default function Chat() {
  const [conversations, setConversations] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    if (currentId) fetchMessages(currentId);
    else setMessages([]);
  }, [currentId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const fetchConversations = async () => {
    try {
      const res = await api.get('/conversations');
      setConversations(res.data);
    } catch (e) { console.error(e); }
  };

  const fetchMessages = async (id) => {
    try {
      const res = await api.get(`/conversations/${id}`);
      setMessages(res.data.messages);
    } catch (e) { console.error(e); }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');
    setError('');
    setLoading(true);

    // Optimistic UI update
    const tempUserMsg = { id: Date.now().toString(), role: 'user', content: question };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const payload = { question };
      if (currentId) payload.conversation_id = currentId;

      const res = await api.post('/chat', payload, { timeout: 120000 });
      
      if (!currentId) {
        setCurrentId(res.data.conversation_id);
        fetchConversations();
      }
      
      const agentMsg = { 
        id: Date.now().toString(), 
        role: 'assistant', 
        content: res.data.answer, 
        sources: res.data.sources,
        answered: res.data.answered
      };
      setMessages(prev => [...prev, agentMsg]);

    } catch (err) {
      setError('ERROR DE CONEXIÓN CON EL AGENTE. INTENTA DE NUEVO.');
      if (err.response?.status === 502) setError('EL MODELO LOCAL NO RESPONDE (502).');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('¿ELIMINAR ESTA CONVERSACIÓN?')) return;
    try {
      await api.delete(`/conversations/${id}`);
      setConversations(prev => prev.filter(c => c.id !== id));
      if (currentId === id) setCurrentId(null);
    } catch (err) { alert('ERROR AL ELIMINAR'); }
  };

  const startNewConversation = () => {
    setCurrentId(null);
    setMessages([]);
    setError('');
  };

  return (
    <div className="flex h-[calc(100vh-80px)] gap-4">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 flex flex-col gap-4 hidden md:flex">
        <button onClick={startNewConversation} className="cyber-button py-2 text-sm">NUEVA CONVERSACIÓN</button>
        <div className="flex-1 overflow-y-auto cyber-panel p-2 space-y-2">
          {conversations.map(c => (
            <div 
              key={c.id} 
              onClick={() => setCurrentId(c.id)}
              className={`p-2 cursor-pointer text-sm font-bold uppercase truncate transition-colors flex justify-between items-center group ${currentId === c.id ? 'bg-cyber-red text-white' : 'hover:bg-cyber-yellow hover:text-black text-gray-300'}`}
            >
              <span className="truncate pr-2">{c.title}</span>
              <button onClick={(e) => handleDeleteConversation(c.id, e)} className="opacity-0 group-hover:opacity-100 text-cyber-yellow hover:text-white">X</button>
            </div>
          ))}
          {conversations.length === 0 && <p className="text-gray-500 text-xs text-center mt-4">NO HAY CONVERSACIONES</p>}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col cyber-panel relative">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col">
          {messages.length === 0 && (
            <div className="m-auto text-center text-gray-500">
              <p className="tag-label text-cyber-yellow text-xl mb-2">SISTEMA LISTO</p>
              <p>Realiza una pregunta sobre la franquicia Cyberpunk.</p>
            </div>
          )}
          
          {messages.map((m, idx) => (
            <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={m.role === 'user' ? 'chat-message-user' : (m.answered === false ? 'chat-message-error' : 'chat-message-agent')}>
                {m.role === 'assistant' && m.answered === false && (
                  <svg className="w-6 h-6 text-cyber-red flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                )}
                <div>{m.content}</div>
              </div>

              {/* Sources */}
              {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
                <details className="mt-2 w-full max-w-[80%]">
                  <summary className="text-cyber-yellow text-xs cursor-pointer tag-label hover:text-white transition-colors">
                    FUENTES ({m.sources.length})
                  </summary>
                  <div className="mt-2 space-y-2">
                    {m.sources.map((s, i) => (
                      <div key={i} className="bg-black/50 border border-gray-700 p-2 text-xs text-gray-300">
                        <div className="flex justify-between font-bold text-cyber-yellow mb-1">
                          <span>{s.filename}</span>
                          <span>{(s.score * 100).toFixed(1)}%</span>
                        </div>
                        <p className="italic text-gray-400">"{s.excerpt}"</p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="chat-message-agent animate-pulse flex items-center gap-2">
              <span className="tag-label text-cyber-yellow">PROCESANDO...</span>
            </div>
          )}
          {error && <div className="chat-message-error text-sm font-bold">{error}</div>}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="p-4 border-t border-gray-700 flex gap-2 bg-black/40">
          <input 
            type="text" 
            value={input} 
            onChange={e => setInput(e.target.value)} 
            placeholder="ESCRIBE TU PREGUNTA AQUÍ..." 
            className="cyber-input flex-1"
            disabled={loading}
          />
          <button type="submit" disabled={loading} className="cyber-button px-6 py-2 disabled:opacity-50">ENVIAR</button>
        </form>
      </div>
    </div>
  );
}
