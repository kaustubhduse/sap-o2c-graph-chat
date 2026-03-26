import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import GraphCanvas from './components/GraphCanvas';
import NodeDetail from './components/NodeDetail';
import DraggableOverlay from './components/DraggableOverlay';
import FilterPanel from './components/FilterPanel';
import ChatWindow from './components/ChatWindow';
import { useGraphData } from './hooks/useGraphData';
import { useGraphFilter } from './hooks/useGraphFilter';
import { useChat } from './hooks/useChat';
import { augmentHighlightsFromSql } from './utils/augmentHighlightsFromSql';
import { Columns, Minimize2, Maximize2, Layers, X } from 'lucide-react';

export default function App() {
  const { graphData, loading, error } = useGraphData();
  const {
    filteredData,
    activeTypes,
    toggleType,
    searchQuery,
    setSearchQuery,
    expandedNode,
    setExpandedNode,
  } = useGraphFilter(graphData);

  const { messages, isLoading: isChatLoading, sendMessage, highlightedNodes, setHighlightedNodes } = useChat();

  const lastSqlAssistantMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant' && m.sql),
    [messages]
  );

  const dismissedQueryMessageIdRef = useRef(null);
  const processedSqlMessageIdRef = useRef(null);

  const [detailContext, setDetailContext] = useState(null);
  const lastHighlightSigRef = useRef('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isOverlayVisible, setIsOverlayVisible] = useState(false); // Hidden by default to match clean UI
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  const resolveHighlightedToNodes = useCallback(
    (hl) => {
      if (!hl?.length || !filteredData.nodes.length) return [];
      return hl
        .map((h) => filteredData.nodes.find((n) => n.id === (h.graphNodeId || h)))
        .filter(Boolean);
    },
    [filteredData.nodes]
  );

  // Graph highlights: merged from API + SQL in useChat (never empty when SQL has literals)

  // New chat highlights: exit "expanded neighborhood" so the full graph can show the path
  useEffect(() => {
    const sig = JSON.stringify(highlightedNodes || []);
    if (!highlightedNodes?.length) {
      lastHighlightSigRef.current = '';
      return;
    }
    if (sig === lastHighlightSigRef.current) return;
    lastHighlightSigRef.current = sig;
    setExpandedNode(null);
  }, [highlightedNodes, setExpandedNode]);

  // Open / refresh the query detail panel when the latest assistant message includes SQL
  useEffect(() => {
    const last = lastSqlAssistantMessage;
    if (!last) return;
    if (last.id === dismissedQueryMessageIdRef.current) return;

    const resolved = resolveHighlightedToNodes(
      augmentHighlightsFromSql(last.sql || '', last.highlightedNodes || [])
    );

    if (processedSqlMessageIdRef.current !== last.id) {
      processedSqlMessageIdRef.current = last.id;
      setDetailContext({
        kind: 'query',
        nodes: resolved,
        sql: last.sql,
        messageId: last.id,
      });
      return;
    }

    setDetailContext((prev) => {
      if (prev?.kind === 'query' && prev.messageId === last.id) {
        return { ...prev, nodes: resolved };
      }
      return prev;
    });
  }, [lastSqlAssistantMessage, resolveHighlightedToNodes]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () =>
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleNodeClick = useCallback(
    (node) => {
      if (!node) {
        setDetailContext(null);
        setHighlightedNodes([]);
        return;
      }
      setDetailContext({ kind: 'manual', node });
    },
    [setHighlightedNodes]
  );

  const handleCloseDetail = useCallback(() => {
    setDetailContext((prev) => {
      if (prev?.kind === 'query' && lastSqlAssistantMessage?.id) {
        dismissedQueryMessageIdRef.current = lastSqlAssistantMessage.id;
      }
      return null;
    });
    setHighlightedNodes([]);
  }, [lastSqlAssistantMessage, setHighlightedNodes]);

  const selectedNodeId =
    detailContext?.kind === 'manual'
      ? detailContext.node.id
      : detailContext?.kind === 'query' && detailContext.nodes[0]
        ? detailContext.nodes[0].id
        : null;

  // Adjust canvas width based on chat sidebar state
  const chatWidth = 400;
  const canvasWidth = isChatOpen ? dimensions.width - chatWidth : dimensions.width;
  // Canvas height is full height minus top navbar (56px)
  const canvasHeight = dimensions.height - 56;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-white text-slate-900 font-sans">
      
      {/* Top Navbar */}
      <header className="flex-shrink-0 h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-3 z-50">
        <div className="flex items-center justify-center w-7 h-7 rounded border border-slate-200 text-slate-600 bg-slate-50 shadow-sm">
          <Columns size={14} />
        </div>
        <div className="text-slate-300">|</div>
        <div className="text-sm font-medium text-slate-500">
          Mapping <span className="mx-1.5 text-slate-300">/</span> <span className="text-slate-900 font-semibold">Order to Cash</span>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden relative">
        
        {/* Left: Graph Area */}
        <div className="flex-1 relative bg-[#fbfcfd] overflow-hidden" style={{ width: canvasWidth }}>
          
          {/* Top-left graph controls */}
          <div className="absolute top-4 left-4 z-20 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              {/* Toggle Chat/Sidebar Minimize */}
              <button 
                onClick={() => setIsChatOpen(!isChatOpen)}
                className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 shadow-[0_2px_10px_rgb(0,0,0,0.04)] rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-all"
              >
                {isChatOpen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                {isChatOpen ? "Minimize" : "Maximize"}
              </button>
              
              {/* Toggle Granular Overlay */}
              <button 
                onClick={() => setIsOverlayVisible(!isOverlayVisible)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-[0_2px_10px_rgb(0,0,0,0.06)] transition-all ${
                  isOverlayVisible 
                    ? 'bg-slate-900 text-white hover:bg-slate-800 border border-slate-900' 
                    : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {isOverlayVisible ? <X size={13} /> : <Layers size={13} />}
                {isOverlayVisible ? "Hide Granular Overlay" : "Show Granular Overlay"}
              </button>
            </div>

            {/* Filter Panel (Granular Overlay) */}
            {isOverlayVisible && (
              <div className="mt-1">
                <FilterPanel
                  activeTypes={activeTypes}
                  onToggleType={toggleType}
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  nodeCount={filteredData.nodes.length}
                  edgeCount={filteredData.links.length}
                  expandedNodeId={expandedNode}
                  onClearExpand={() => setExpandedNode(null)}
                />
              </div>
            )}
          </div>

          {/* Floating Movable Node Detail Overlay */}
          {detailContext && (
            <DraggableOverlay>
              <NodeDetail
                mode={detailContext.kind === 'query' ? 'query' : 'single'}
                nodes={
                  detailContext.kind === 'manual'
                    ? [detailContext.node]
                    : detailContext.nodes
                }
                sql={detailContext.kind === 'query' ? detailContext.sql : undefined}
                edges={graphData.links}
                onExpand={setExpandedNode}
                onClose={handleCloseDetail}
                expandedNodeId={expandedNode}
              />
            </DraggableOverlay>
          )}

          {/* Graph Canvas */}
          <div className="absolute inset-0 z-0">
            <GraphCanvas
              data={filteredData}
              pathfindingLinks={graphData.links}
              onNodeClick={handleNodeClick}
              onNodeRightClick={(n) => {
                setExpandedNode(n.id);
                setDetailContext({ kind: 'manual', node: n });
              }}
              selectedNodeId={selectedNodeId}
              expandedNodeId={expandedNode}
              highlightedNodes={highlightedNodes}
              width={canvasWidth}
              height={canvasHeight}
              backgroundColor="#fbfcfd"
              textColor="#334155"
            />
          </div>
        </div>

        {/* Right: Sliding Chat Interface */}
        <div 
          className={`h-full bg-white shadow-[-10px_0_30px_rgba(0,0,0,0.03)] border-l border-slate-200 z-40 transform transition-all duration-300 ease-in-out flex-shrink-0 relative overflow-hidden`}
          style={{ width: chatWidth, marginRight: isChatOpen ? 0 : -chatWidth }}
        >
          <ChatWindow 
            messages={messages} 
            isLoading={isChatLoading} 
            onSendMessage={sendMessage} 
          />
        </div>
        
      </div>
    </div>
  );
}
