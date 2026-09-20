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

  // Auto-scroll to bottom
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
      const response = await chatWithAgent({ trip_id: tripId, message: text });
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
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white/95 backdrop-blur-md shadow-2xl z-50 flex flex-col border-l border-gray-200 transform transition-transform duration-300">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-md">
        <div className="flex items-center space-x-3">
          <Bot className="h-6 w-6" />
          <h2 className="text-lg font-semibold tracking-wide">TravelPilot Assistant</h2>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full transition-colors">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/50">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-10 space-y-6">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 text-blue-600 mb-2">
              <Bot className="h-8 w-8" />
            </div>
            <p className="text-gray-600 font-medium">Hello! How can I help you customize this trip?</p>
            
            <div className="space-y-2 text-sm text-left">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Try asking:</p>
              {predefinedQueries.map((q, i) => (
                <button 
                  key={i}
                  onClick={() => setInput(q)}
                  className="block w-full text-left px-4 py-3 bg-white border border-gray-200 rounded-lg hover:border-blue-400 hover:shadow-sm transition-all text-gray-700"
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
              <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center shadow-sm ${msg.role === 'user' ? 'bg-indigo-100 text-indigo-700 ml-3' : 'bg-blue-600 text-white mr-3'}`}>
                {msg.role === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
              </div>
              <div className={`px-4 py-3 rounded-2xl shadow-sm text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'}`}>
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="flex flex-row max-w-[85%]">
              <div className="flex-shrink-0 h-8 w-8 rounded-full bg-blue-600 text-white mr-3 flex items-center justify-center shadow-sm">
                <Bot className="h-5 w-5" />
              </div>
              <div className="px-5 py-4 bg-white border border-gray-100 rounded-2xl rounded-tl-none shadow-sm flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span className="text-sm text-gray-500 font-medium tracking-wide">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this trip..."
            className="w-full pr-12 rounded-full border-gray-300 focus:border-blue-500 focus:ring-blue-500 shadow-inner bg-gray-50"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 p-2 rounded-full text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:bg-gray-400 transition-colors shadow-sm"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
        <p className="text-[10px] text-center text-gray-400 mt-2">TravelPilot AI can make mistakes. Check important information.</p>
      </div>
    </div>
  );
}
