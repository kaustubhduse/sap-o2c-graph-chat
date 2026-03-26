import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Code2, AlertTriangle, CheckCircle2, Database } from 'lucide-react';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const defaultShowSql = Boolean(message.resultEmpty && message.sql);
  const [showSql, setShowSql] = useState(defaultShowSql);

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div 
        className={`max-w-[85%] rounded-2xl p-5 shadow-sm
        ${isUser 
          ? 'bg-blue-600 text-white rounded-tr-sm' 
          : 'bg-surface-800 text-slate-200 rounded-tl-sm border border-surface-700'
        }`}
      >
        {/* Header / Meta */}
        <div className="flex items-center gap-2 mb-2 text-xs opacity-70">
          <span className="font-semibold">{isUser ? 'You' : 'O2C Explorer'}</span>
          <span>•</span>
          <span>{new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
          
          {message.status === 'error' && (
            <span className="flex items-center gap-1 text-red-400 ml-2 bg-red-400/10 px-2 py-0.5 rounded-full">
              <AlertTriangle size={12} /> Error
            </span>
          )}
          {message.status === 'success' && message.resultEmpty && (
            <span className="flex items-center gap-1 text-amber-400 ml-2 bg-amber-400/10 px-2 py-0.5 rounded-full">
              <Database size={12} /> Ran — 0 rows
            </span>
          )}
          {message.status === 'success' && !message.resultEmpty && (
            <span className="flex items-center gap-1 text-emerald-400 ml-2 bg-emerald-400/10 px-2 py-0.5 rounded-full">
              <CheckCircle2 size={12} /> Success
            </span>
          )}
        </div>

        {/* Markdown Content */}
        <div className="prose prose-invert max-w-none text-sm leading-relaxed">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Actions for Assistant Messages */}
        {!isUser && message.sql && (
          <div className="mt-4 pt-4 border-t border-surface-700 flex flex-wrap gap-2">
            <button 
              onClick={() => setShowSql(!showSql)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
                ${showSql ? 'bg-blue-500/20 text-blue-300' : 'bg-surface-700 text-slate-400 hover:text-slate-200 hover:bg-surface-600'}`
              }
            >
              <Code2 size={14} />
              {showSql ? 'Hide SQL' : 'View SQL'}
            </button>
          </div>
        )}

        {/* SQL Viewer */}
        {showSql && message.sql && (
          <div className="mt-2 bg-surface-950 rounded-lg p-3 border border-surface-700 overflow-x-auto">
            <pre className="text-xs text-blue-300 font-mono m-0">{message.sql}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
