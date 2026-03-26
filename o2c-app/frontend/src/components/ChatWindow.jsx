import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import QueryInput from './QueryInput';
import { Database, Activity } from 'lucide-react';

export default function ChatWindow({ messages, isLoading, onSendMessage }) {
  const endOfMessagesRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-white overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center text-white shadow-sm">
            <span className="font-bold text-lg">D</span>
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900">Chat with Graph</h1>
            <p className="text-xs text-slate-500">Order to Cash</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400 font-medium tracking-wide">Dodge AI Graph Agent</span>
        </div>
      </header>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 scroll-smooth bg-[#f8fafc]">
        <div className="max-w-4xl mx-auto flex flex-col gap-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          
          {isLoading && (
            <div className="flex items-center gap-3 text-slate-500 text-sm py-4 px-2 animate-pulse w-full max-w-[85%]">
              <Activity size={18} className="text-blue-500 ml-5" />
              <span>Analyzing dataset and generating SQL query...</span>
            </div>
          )}
          
          <div ref={endOfMessagesRef} className="h-4" />
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 bg-white border-t border-slate-200 p-4 sm:p-6 z-10">
        <div className="max-w-4xl mx-auto">
          <QueryInput onSend={onSendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
