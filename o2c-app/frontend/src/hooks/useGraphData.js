import { useState, useEffect } from 'react';

/**
 * Hook to load nodes.json and edges.json from public/ folder
 * and transform into react-force-graph format.
 */
export function useGraphData() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [rawNodes, setRawNodes] = useState([]);
  const [rawEdges, setRawEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [nodesRes, edgesRes] = await Promise.all([
          fetch('/nodes.json'),
          fetch('/edges.json'),
        ]);
        const nodesData = await nodesRes.json();
        const edgesData = await edgesRes.json();

        setRawNodes(nodesData);
        setRawEdges(edgesData);

        // Transform for react-force-graph
        const nodes = nodesData.map(n => ({
          id: n.id,
          type: n.type,
          label: n.label,
          properties: n.properties,
          // initially all visible
          _visible: true,
        }));

        const links = edgesData.map((e, i) => ({
          id: `edge-${i}`,
          source: e.source,
          target: e.target,
          type: e.type,
          properties: e.properties,
        }));

        setGraphData({ nodes, links });
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }
    load();
  }, []);

  return { graphData, rawNodes, rawEdges, loading, error };
}
