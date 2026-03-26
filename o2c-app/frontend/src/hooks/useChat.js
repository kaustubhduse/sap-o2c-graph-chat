import { useState } from 'react';
import { augmentHighlightsFromSql } from '../utils/augmentHighlightsFromSql';
import { API_BASE_URL } from '../config';

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

  const readSseEvents = async (response, onEvent) => {
    const reader = response.body?.getReader();
    if (!reader) throw new Error('Streaming reader unavailable');
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const rawEvent of events) {
        const dataLines = rawEvent
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim());
        if (!dataLines.length) continue;
        try {
          const payload = JSON.parse(dataLines.join(''));
          onEvent(payload);
        } catch (e) {
          console.warn('Failed to parse stream event:', e);
        }
      }
    }
  };

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
      const assistantId = (Date.now() + 1).toString();
      const baseAssistant = {
        id: assistantId,
        role: 'assistant',
        content: '',
        sql: null,
        data: null,
        highlightedNodes: [],
        status: 'streaming',
        resultEmpty: null,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, baseAssistant]);

      let streamedContent = '';
      let latestSql = null;
      let finalResult = null;

      const streamResponse = await fetch(`${API_BASE_URL}/api/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      if (streamResponse.ok && streamResponse.body) {
        await readSseEvents(streamResponse, (event) => {
          if (event.event === 'sql' && event.sql) {
            latestSql = event.sql;
            setMessages(prev =>
              prev.map(m => (m.id === assistantId ? { ...m, sql: latestSql } : m))
            );
            return;
          }

          if (event.event === 'answer_chunk' && typeof event.chunk === 'string') {
            streamedContent += event.chunk;
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId ? { ...m, content: streamedContent, sql: latestSql } : m
              )
            );
            return;
          }

          if (event.event === 'final' && event.result) {
            finalResult = event.result;
          }
        });
      } else {
        // Fallback to non-stream endpoint
        const response = await fetch(`${API_BASE_URL}/api/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        finalResult = await response.json();
      }

      if (!finalResult) {
        throw new Error('No final result from stream');
      }

      const graphHighlights =
        finalResult.status === 'success'
          ? augmentHighlightsFromSql(finalResult.sql || '', finalResult.highlighted_nodes || [])
          : [];

      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? {
                ...m,
                content: finalResult.answer || streamedContent || m.content,
                sql: finalResult.sql,
                data: finalResult.data,
                highlightedNodes: graphHighlights,
                status: finalResult.status,
                resultEmpty: finalResult.result_empty,
              }
            : m
        )
      );

      if (finalResult.status === 'success') {
        setHighlightedNodes(graphHighlights);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Sorry, I encountered a network error. Check that the API is reachable (${API_BASE_URL}).`,
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
