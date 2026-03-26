import { useState } from 'react';
import { augmentHighlightsFromSql } from '../utils/augmentHighlightsFromSql';

export function useChat() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Welcome to the SAP O2C Chat Explorer. You can ask me questions about sales orders, deliveries, billing documents, payments, customers, and products.\n\nFor example:\n- *What are the top 5 customers by order count?*\n- *Show me sales orders that are delivered but not billed.*',
      timestamp: new Date().toISOString()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedNodes, setHighlightedNodes] = useState([]);

  const sendMessage = async (text) => {
    if (!text.trim()) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      const data = await response.json();

      const graphHighlights =
        data.status === 'success'
          ? augmentHighlightsFromSql(data.sql || '', data.highlighted_nodes || [])
          : [];

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        sql: data.sql,
        data: data.data,
        highlightedNodes: graphHighlights,
        status: data.status,
        resultEmpty: data.result_empty,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (data.status === 'success') {
        setHighlightedNodes(graphHighlights);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered a network error. Please ensure the backend server is running on port 8000.',
        status: 'error',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    isLoading,
    sendMessage,
    highlightedNodes,
    setHighlightedNodes,
  };
}
