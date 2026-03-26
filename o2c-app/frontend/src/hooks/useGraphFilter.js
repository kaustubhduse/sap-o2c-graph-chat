import { useState, useMemo, useCallback } from 'react';

/**
 * Hook to manage graph filtering and expansion state.
 */
export function useGraphFilter(graphData) {
  const [activeTypes, setActiveTypes] = useState(new Set([
    'Customer', 'SalesOrder', 'Product', 'Delivery',
    'BillingDocument', 'JournalEntry', 'Payment', 'Plant'
  ]));
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedNode, setExpandedNode] = useState(null);

  const toggleType = useCallback((type) => {
    setActiveTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const filteredData = useMemo(() => {
    if (!graphData.nodes.length) return { nodes: [], links: [] };

    const query = searchQuery.toLowerCase().trim();

    // Filter nodes by type and search
    let nodes = graphData.nodes.filter(n => {
      if (!activeTypes.has(n.type)) return false;
      if (query) {
        return n.id.toLowerCase().includes(query) ||
               n.label.toLowerCase().includes(query) ||
               Object.values(n.properties || {}).some(v =>
                 String(v).toLowerCase().includes(query)
               );
      }
      return true;
    });

    // If a node is expanded, show only it + direct neighbors
    if (expandedNode) {
      const neighborIds = new Set();
      neighborIds.add(expandedNode);
      graphData.links.forEach(link => {
        const srcId = typeof link.source === 'object' ? link.source.id : link.source;
        const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
        if (srcId === expandedNode) neighborIds.add(tgtId);
        if (tgtId === expandedNode) neighborIds.add(srcId);
      });
      nodes = graphData.nodes.filter(n => neighborIds.has(n.id));
    }

    const visibleIds = new Set(nodes.map(n => n.id));
    const links = graphData.links.filter(l => {
      const srcId = typeof l.source === 'object' ? l.source.id : l.source;
      const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
      return visibleIds.has(srcId) && visibleIds.has(tgtId);
    });

    return { nodes, links };
  }, [graphData, activeTypes, searchQuery, expandedNode]);

  return {
    filteredData,
    activeTypes,
    toggleType,
    searchQuery,
    setSearchQuery,
    expandedNode,
    setExpandedNode,
  };
}
