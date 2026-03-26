import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Search } from 'lucide-react';

const SUGGESTED_QUERIES = [
  "Show me all customers and their sales orders",
  "What are the top products by sales volume?",
  "Show the complete order to cash flow",
  "List all unpaid billing documents",
  "Show me payments received from customers",
  "What products are available at each plant?",
  "Display all pending deliveries",
  "Show me the accounts receivable status",
  "Which customers have made purchases?",
  "Show all journal entries for accounts receivable"
];

export default function QueryInput({ onSend, isLoading }) {
  const [text, setText] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState([]);
  const textareaRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [text]);

  // Filter suggestions based on input
  useEffect(() => {
    if (text.trim().length > 0) {
      const filtered = SUGGESTED_QUERIES.filter(q =>
        q.toLowerCase().includes(text.toLowerCase())
      );
      setFilteredSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setFilteredSuggestions(SUGGESTED_QUERIES);
      setShowSuggestions(false);
    }
  }, [text]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !isLoading) {
      onSend(text.trim());
      setText('');
      setShowSuggestions(false);
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setText(suggestion);
    setShowSuggestions(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="relative">
      <form 
        onSubmit={handleSubmit}
        className="relative flex items-end gap-2 bg-slate-800 p-2 rounded-xl border border-slate-700 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500/50 transition-all shadow-lg"
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => text.length === 0 && setShowSuggestions(false)}
          placeholder="Ask a question about the O2C dataset..."
          disabled={isLoading}
          rows={1}
          className="flex-1 max-h-[120px] bg-transparent text-slate-200 placeholder-slate-500 py-3 px-3 resize-none focus:outline-none disabled:opacity-50 text-sm leading-relaxed"
        />
        
        <button
          type="submit"
          disabled={!text.trim() || isLoading}
          className="p-3 mb-0.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white disabled:bg-slate-700 disabled:text-slate-500 transition-colors flex-shrink-0"
        >
          {isLoading ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Send size={20} className={text.trim() ? "translate-x-0.5" : ""} />
          )}
        </button>
      </form>

      {/* Suggestions Dropdown */}
      {text.trim().length > 0 && filteredSuggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute bottom-full left-0 right-0 mb-2 bg-slate-900 border border-slate-700 rounded-lg shadow-xl overflow-hidden z-50 max-h-64 overflow-y-auto"
        >
          <div className="p-2 border-b border-slate-700">
            <p className="text-xs text-slate-400 font-semibold px-2 py-1">Suggested Queries</p>
          </div>
          <div className="divide-y divide-slate-700">
            {filteredSuggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full text-left px-4 py-3 hover:bg-slate-800 transition-colors text-slate-300 text-sm hover:text-slate-100 flex items-start gap-2 group"
              >
                <Search size={16} className="text-blue-400 mt-0.5 flex-shrink-0" />
                <span>{suggestion}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
