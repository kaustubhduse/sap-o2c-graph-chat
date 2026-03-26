import { useRef, useCallback, useEffect, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { forceX, forceY, forceCollide, forceRadial } from 'd3-force';
import { NODE_COLORS, NODE_SIZES, EDGE_COLORS } from '../config/graphConfig';

function undirectedEdgeKey(a, b) {
  return a < b ? `${a}|||${b}` : `${b}|||${a}`;
}

function buildEntityAdjacency(links) {
  const adj = new Map();
  const add = (u, v) => {
    if (!u || !v) return;
    if (!adj.has(u)) adj.set(u, []);
    if (!adj.has(v)) adj.set(v, []);
    adj.get(u).push(v);
    adj.get(v).push(u);
  };
  for (const link of links || []) {
    const s = typeof link.source === 'object' ? link.source.id : link.source;
    const t = typeof link.target === 'object' ? link.target.id : link.target;
    add(s, t);
  }
  return adj;
}

/** BFS shortest path: every edge and every node on the path (data graph only). */
function shortestPathBetween(adj, start, end) {
  if (start === end) return { edgeKeys: [], nodes: [start] };
  const queue = [start];
  const parent = new Map([[start, null]]);
  while (queue.length) {
    const u = queue.shift();
    for (const v of adj.get(u) || []) {
      if (!parent.has(v)) {
        parent.set(v, u);
        if (v === end) {
          const rev = [];
          let cur = v;
          while (cur !== start) {
            rev.push(cur);
            cur = parent.get(cur);
            if (cur === null) return { edgeKeys: [], nodes: [] };
          }
          rev.push(start);
          const nodes = rev.reverse();
          const edgeKeys = [];
          for (let i = 0; i < nodes.length - 1; i++) {
            edgeKeys.push(undirectedEdgeKey(nodes[i], nodes[i + 1]));
          }
          return { edgeKeys, nodes };
        }
        queue.push(v);
      }
    }
  }
  return { edgeKeys: [], nodes: [] };
}

function computeQueryPathHighlight(links, highlightIds) {
  const pathLinkKeys = new Set();
  const pathNodeIds = new Set();
  const adj = buildEntityAdjacency(links);
  const ids = [...highlightIds].filter((id) => id && !String(id).startsWith('HUB_') && adj.has(id));
  if (ids.length < 2) return { pathLinkKeys, pathNodeIds };
  for (let i = 0; i < ids.length; i++) {
    for (let j = i + 1; j < ids.length; j++) {
      const { edgeKeys, nodes } = shortestPathBetween(adj, ids[i], ids[j]);
      edgeKeys.forEach((k) => pathLinkKeys.add(k));
      nodes.forEach((n) => pathNodeIds.add(n));
    }
  }
  return { pathLinkKeys, pathNodeIds };
}

/**
 * The main 2D force-graph canvas.
 */
export default function GraphCanvas({
  data,
  /** Full graph links for pathfinding (avoids broken paths when the view is filtered / expanded) */
  pathfindingLinks,
  onNodeClick,
  onNodeRightClick,
  selectedNodeId,
  expandedNodeId,
  highlightedNodes = [],
  width,
  height,
  backgroundColor = '#ffffff',
  textColor = '#1e293b'
}) {
  const fgRef = useRef();

  // Fast lookup for highlighting
  const highlightedSet = useMemo(() => {
    return new Set(highlightedNodes.map(h => h.graphNodeId || h));
  }, [highlightedNodes]);

  const entityLinks = data?.links || data?.edges || [];
  const linksForPaths = pathfindingLinks?.length ? pathfindingLinks : entityLinks;
  const { pathLinkKeys, pathNodeIds } = useMemo(
    () => computeQueryPathHighlight(linksForPaths, highlightedSet),
    [linksForPaths, highlightedSet]
  );

  const queryHighlightActive = highlightedNodes.length > 0;

  // Hierarchical radial layout with CENTER table in the middle
  const { processedData, clusters, orbitPositions } = useMemo(() => {
    if (!data || !data.nodes) return { processedData: { nodes: [], links: [] }, clusters: {}, orbitPositions: {} };

    const nodes = [...data.nodes];
    const hubLinks = [];
    const types = Array.from(new Set(data.nodes.map(n => n.type)));
    
    // Define center table (usually Customer or the main entity)
    const centerType = 'Customer';
    const otherTypes = types.filter(t => t !== centerType);
    
    // Manual positioning for radial layout
    const centers = {};
    const hubRadius = 600; // Distance of peripheral tables from center
    
    // Center position
    centers[centerType] = { x: 0, y: 0 };
    
    // Position other tables around center in a radial pattern
    // Distribute them around the center based on their index
    otherTypes.forEach((type, idx) => {
      const angle = (idx / otherTypes.length) * 2 * Math.PI;
      centers[type] = {
        x: hubRadius * Math.cos(angle),
        y: hubRadius * Math.sin(angle)
      };
    });

    // Create Hub nodes for each table
    types.forEach((type) => {
      nodes.push({
        id: `HUB_${type}`,
        type: type, 
        label: type,
        isHub: true,
        val: type === centerType ? 18 : 15
      });
    });

    // Group entities by table type and arrange them in orbits
    const orbitPositions = {};
    const entitiesByType = {};
    
    data.nodes.forEach(n => {
      if (!n.isHub) {
        if (!entitiesByType[n.type]) entitiesByType[n.type] = [];
        entitiesByType[n.type].push(n);
      }
    });

    // Create orbiting positions for entities around their hubs
    Object.entries(entitiesByType).forEach(([type, entities]) => {
      const numEntities = entities.length;
      const hubCenter = centers[type];
      const orbitRadius = 200; // Distance of entities from their hub
      
      entities.forEach((entity, idx) => {
        const angle = (idx / numEntities) * 2 * Math.PI;
        const x = hubCenter.x + orbitRadius * Math.cos(angle);
        const y = hubCenter.y + orbitRadius * Math.sin(angle);
        
        orbitPositions[entity.id] = { x, y };
      });

      // Create hub-to-entity links (spokes)
      entities.forEach(entity => {
        hubLinks.push({
          source: `HUB_${type}`,
          target: entity.id,
          type: 'HUB_LINK',
          isHubLink: true
        });
      });
    });

    return { 
      processedData: { nodes, links: [...hubLinks, ...(data.links || data.edges || [])] },
      clusters: centers,
      orbitPositions
    };
  }, [data]);

  // Zoom and layout config on data change
  useEffect(() => {
    if (fgRef.current && processedData.nodes.length) {
      const fg = fgRef.current;
      
      // Disable default center force
      fg.d3Force('center', null); 
      
      // 1. Lock hubs strictly to their grid positions
      fg.d3Force('x', forceX(n => {
        if (n.isHub) return clusters[n.type]?.x || 0;
        return orbitPositions[n.id]?.x || 0;
      }).strength(n => n.isHub ? 1 : 0.8));
      
      fg.d3Force('y', forceY(n => {
        if (n.isHub) return clusters[n.type]?.y || 0;
        return orbitPositions[n.id]?.y || 0;
      }).strength(n => n.isHub ? 1 : 0.8));
      
      // 2. Link force for connections
      fg.d3Force('link')
        .distance(link => link.isHubLink ? 200 : 350)
        .strength(link => link.isHubLink ? 2 : 0.08);
      
      // 3. Charge force for repulsion
      fg.d3Force('charge').strength(node => node.isHub ? -150 : -50);
      
      // 4. Collision between nodes
      fg.d3Force('collide', forceCollide(node => (NODE_SIZES[node.type] || 5) + 5).strength(0.9));
      
      // Re-heat and let physics settle
      fg.d3ReheatSimulation();
      
      setTimeout(() => fgRef.current.zoomToFit(800, 150), 2000);
    }
  }, [processedData.nodes.length, clusters, orbitPositions]);

  // Pan to highlighted nodes
  useEffect(() => {
    if (fgRef.current && highlightedNodes.length > 0 && processedData.nodes.length) {
      const nodes = processedData.nodes.filter(n => highlightedSet.has(n.id));
      if (nodes.length > 0) {
        const sumX = nodes.reduce((sum, n) => sum + (n.x || 0), 0);
        const sumY = nodes.reduce((sum, n) => sum + (n.y || 0), 0);
        const avgX = sumX / nodes.length;
        const avgY = sumY / nodes.length;
        
        // Use a slight delay to allow physics to settle if it just loaded
        setTimeout(() => {
          if (fgRef.current) {
            fgRef.current.centerAt(avgX, avgY, 1000);
            fgRef.current.zoom(1.5, 1000);
          }
        }, 500);
      }
    }
  }, [highlightedNodes, highlightedSet, processedData.nodes]);

  const handleNodeClick = useCallback((node) => {
    // Avoid triggering full details for synthesized hubs
    if (node && node.isHub) return; 
    onNodeClick?.(node);
  }, [onNodeClick]);

  const handleNodeRightClick = useCallback((node) => {
    if (node && node.isHub) return;
    onNodeRightClick?.(node);
  }, [onNodeRightClick]);

  const handleBackgroundClick = useCallback(() => {
    onNodeClick?.(null);
  }, [onNodeClick]);

  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const isHub = node.isHub;
    const isHighlighted = highlightedSet.has(node.id);
    const onPathChain =
      queryHighlightActive && !isHub && pathNodeIds.has(node.id);
    const paintQueryBlack = isHighlighted || onPathChain;

    // Hub: Blue dot (larger), Entities: Smaller colorful dots
    const size = isHub ? 8 : (NODE_SIZES[node.type] || 4);
    
    // Hub is always bright BLUE, entities get their type color (vibrant and visible)
    let color = isHub ? '#2563eb' : (NODE_COLORS[node.type] || '#94a3b8');
    if (paintQueryBlack) color = '#000000';

    const isSelected = node.id === selectedNodeId;
    const isExpanded = node.id === expandedNodeId;

    // Glow effect for hub or highlighted nodes
    if (isHub || paintQueryBlack || isSelected || isExpanded) {
      ctx.beginPath();
      const glowSize = paintQueryBlack ? 16 : (isHub ? 10 : 6);
      ctx.arc(node.x, node.y, size + glowSize, 0, 2 * Math.PI);
      
      let glowColor = paintQueryBlack ? '#000000' : (isHub ? '#2563eb' : color);
      ctx.fillStyle = `${glowColor}33`;
      ctx.fill();
    }

    // Main circle - vibrant colors
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    
    // Border
    ctx.lineWidth = (isHub || paintQueryBlack) ? 2 / globalScale : 1 / globalScale;
    ctx.strokeStyle = paintQueryBlack ? '#000000' : (isHub ? '#1e3a8a' : '#f3f4f644');
    ctx.stroke();

    // Label: Show for all nodes at sufficient zoom, always show hubs and highlighted
    if (globalScale > 0.5 || isHub || paintQueryBlack) {
      const labelText = isHub ? node.label : node.label;
      const fontSize = isHub ? Math.max(13 / globalScale, 6.5) : Math.max(8 / globalScale, 3.5);
      ctx.font = `${isHub ? 'bold' : 'normal'} ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = isHub ? '#000000' : (paintQueryBlack ? '#000000' : '#1f2937');
      ctx.lineWidth = 2 / globalScale;
      ctx.strokeStyle = '#ffffff';
      ctx.strokeText(labelText, node.x, node.y);
      ctx.fillText(labelText, node.x, node.y);
    }
  }, [selectedNodeId, expandedNodeId, highlightedSet, pathNodeIds, queryHighlightActive]);

  const linkColor = useCallback((link) => {
    const srcId = typeof link.source === 'object' ? link.source.id : link.source;
    const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
    
    const srcHigh = highlightedSet.has(srcId);
    const tgtHigh = highlightedSet.has(tgtId);
    const onDataPath =
      !link.isHubLink && pathLinkKeys.has(undirectedEdgeKey(srcId, tgtId));

    if (onDataPath || (srcHigh && tgtHigh)) {
      return '#000000';
    }

    if (link.isHubLink && queryHighlightActive) {
      const entitySide = srcId.startsWith('HUB_')
        ? tgtId
        : tgtId.startsWith('HUB_')
          ? srcId
          : null;
      if (
        entitySide &&
        !String(entitySide).startsWith('HUB_') &&
        (highlightedSet.has(entitySide) || pathNodeIds.has(entitySide))
      ) {
        return '#000000';
      }
    }

    // Hub spokes: Light blue with lower opacity
    if (link.isHubLink) return '#60a5fa66'; 
    
    // Regular links: Use edge colors with light opacity
    return EDGE_COLORS[link.type] || '#9ca3af44'; 
  }, [highlightedSet, pathLinkKeys, pathNodeIds, queryHighlightActive]);

  const linkDirectionalArrowLength = useCallback((link) => link.isHubLink ? 0 : 3, []);
  const linkDirectionalArrowRelPos = useCallback(() => 0.85, []);

  return (
    <ForceGraph2D
      ref={fgRef}
      graphData={processedData}
      width={width}
      height={height}
      backgroundColor={backgroundColor}
      nodeCanvasObject={nodeCanvasObject}
      onNodeClick={handleNodeClick}
      onNodeRightClick={handleNodeRightClick}
      onBackgroundClick={handleBackgroundClick}
      linkColor={linkColor}
      linkWidth={link => {
        const srcId = typeof link.source === 'object' ? link.source.id : link.source;
        const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
        const srcHigh = highlightedSet.has(srcId);
        const tgtHigh = highlightedSet.has(tgtId);
        const onDataPath =
          !link.isHubLink && pathLinkKeys.has(undirectedEdgeKey(srcId, tgtId));
        
        if (onDataPath || (srcHigh && tgtHigh)) return 5;

        if (link.isHubLink && queryHighlightActive) {
          const entitySide = srcId.startsWith('HUB_')
            ? tgtId
            : tgtId.startsWith('HUB_')
              ? srcId
              : null;
          if (
            entitySide &&
            !String(entitySide).startsWith('HUB_') &&
            (highlightedSet.has(entitySide) || pathNodeIds.has(entitySide))
          ) {
            return 3.5;
          }
        }

        // Show hub links for highlighted nodes slightly bolder
        if (link.isHubLink && (srcHigh || tgtHigh)) return 2.5;

        return link.isHubLink ? 0.3 : 0.2; // Barely visible threads
      }}
      linkCurvature={link => link.isHubLink ? 0 : 0.15} // Slight curve to avoid messy overlap
      linkDirectionalArrowLength={linkDirectionalArrowLength}
      linkDirectionalArrowRelPos={linkDirectionalArrowRelPos}
      linkDirectionalArrowColor={linkColor}
      d3AlphaDecay={0.04}
      d3VelocityDecay={0.4} 
      cooldownTicks={150}
      enableNodeDrag={true}
    />
  );
}
