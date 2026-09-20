import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, Loader2 } from 'lucide-react';
import { chatWithAgent } from '../../api/agent';
import { Input } from '../common/Input';

interface Message {
  role: 'user' | 'agent';
  content: string;
}

interface AgentChatDrawerProps {
  tripId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function AgentChatDrawer({ tripId, isOpen, onClose }: AgentChatDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const historyPayload = messages.map(m => ({ role: m.role, content: m.content }));
      const response = await chatWithAgent({ trip_id: tripId, message: text, history: historyPayload } as any);
      setMessages(prev => [...prev, { role: 'agent', content: response.reply }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'agent', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const predefinedQueries = [
    "Can I fit one more activity this afternoon?",
    "Which activities are close to my hotel?",
    "What should I do tomorrow morning?",
    "Reduce the cost of Day 3."
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl z-50 flex flex-col border-l border-slate-200 transform transition-transform duration-300">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-white text-slate-900 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">TravelPilot Assistant</h2>
            <p className="text-[10px] text-slate-500 font-mono">Trip Context Aware AI</p>
          </div>
        </div>
        <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-slate-50">
        {messages.length === 0 && (
          <div className="text-center text-slate-500 mt-6 space-y-5">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-50 border border-blue-200 text-blue-600">
              <Bot className="h-7 w-7" />
            </div>
            <p className="text-slate-800 text-sm font-semibold">Hello! Ask me anything about your current trip.</p>
            
            <div className="space-y-2 text-xs text-left">
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Suggested Questions:</p>
              {predefinedQueries.map((q, i) => (
                <button 
                  key={i}
                  onClick={() => setInput(q)}
                  className="block w-full text-left px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/50 transition-all text-slate-700 font-medium"
                >
                  "{q}"
                </button>
              ))}
            </div>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center shadow-sm text-xs font-bold ${msg.role === 'user' ? 'bg-blue-600 text-white ml-2.5' : 'bg-blue-50 border border-blue-200 text-blue-600 mr-2.5'}`}>
                {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div className={`px-4 py-3 rounded-2xl text-xs leading-relaxed ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none font-medium' : 'bg-white border border-slate-200 text-slate-800 shadow-sm rounded-tl-none'}`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="flex flex-row max-w-[85%]">
              <div className="flex-shrink-0 h-8 w-8 rounded-full bg-blue-50 border border-blue-200 text-blue-600 mr-2.5 flex items-center justify-center shadow-sm">
                <Bot className="h-4 w-4" />
              </div>
              <div className="px-4 py-3 bg-white border border-slate-200 rounded-2xl rounded-tl-none shadow-sm flex items-center space-x-2 text-xs">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span className="text-slate-500 font-medium">Analyzing trip schedule & gaps...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-slate-200">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your trip schedule..."
            className="w-full pr-12 rounded-full border-slate-200 focus:border-blue-500 focus:ring-blue-500 bg-slate-50 text-slate-900 text-xs py-2.5"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-1.5 p-2 rounded-full text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
        <p className="text-[10px] text-center text-slate-400 mt-2 font-mono">TravelPilot Context Engine Connected</p>
      </div>
    </div>
  );
}
