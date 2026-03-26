import { X } from 'lucide-react';
import { NODE_COLORS } from '../config/graphConfig';

const MAX_PROPS_PER_NODE = 14;

function countConnections(nodeId, edges) {
  if (!edges?.length) return 0;
  return edges.filter((e) => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source;
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target;
    return srcId === nodeId || tgtId === nodeId;
  }).length;
}

function NodeSection({ node, edges, onExpand, isExpanded, omitHeading }) {
  const props = node.properties || {};
  const entries = Object.entries(props);
  const displayEntries = omitHeading
    ? [['Entity', node.type], ...entries]
    : entries;
  const visible = displayEntries.slice(0, MAX_PROPS_PER_NODE);
  const hiddenCount = Math.max(0, displayEntries.length - MAX_PROPS_PER_NODE);
  const connCount = countConnections(node.id, edges);
  const color = NODE_COLORS[node.type] || '#64748b';

  return (
    <section className="border-b border-slate-100 last:border-b-0 pb-4 last:pb-0 mb-4 last:mb-0">
      {!omitHeading && (
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-slate-900 truncate" title={node.label}>
              {node.label || node.type}
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              <span className="font-medium text-slate-600">Entity</span>{' '}
              <span className="text-slate-800">{node.type}</span>
            </p>
          </div>
          <span
            className="flex-shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide"
            style={{ backgroundColor: `${color}18`, color }}
          >
            {node.type}
          </span>
        </div>
      )}

      <div className="space-y-1.5">
        {visible.map(([key, value]) => (
          <div
            key={key}
            className="flex flex-col sm:flex-row sm:gap-3 sm:items-baseline text-sm border-b border-slate-50 pb-1.5 last:border-0"
          >
            <span className="text-slate-500 font-medium min-w-[140px] shrink-0">{key}</span>
            <span className="text-slate-800 break-all font-normal">
              {value === null || value === undefined || value === '' ? (
                <span className="text-slate-400 italic">(empty)</span>
              ) : (
                String(value)
              )}
            </span>
          </div>
        ))}
        {displayEntries.length === 0 && (
          <p className="text-sm text-slate-500 italic">No properties on this node</p>
        )}
      </div>

      {hiddenCount > 0 && (
        <p className="text-xs text-slate-400 italic mt-3">*Additional fields hidden for readability*</p>
      )}

      <p className="text-xs text-slate-600 mt-3">
        <span className="font-semibold text-slate-700">Connections</span>{' '}
        <span className="text-slate-500">{connCount}</span>
      </p>

      {onExpand && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => onExpand(isExpanded ? null : node.id)}
            className={`w-full px-3 py-2 rounded-md text-xs font-semibold transition-colors
              ${isExpanded
                ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
                : 'bg-blue-50 text-blue-800 hover:bg-blue-100 border border-blue-200'
              }`}
          >
            {isExpanded ? '↩ Collapse neighborhood' : '⤢ Expand neighborhood'}
          </button>
        </div>
      )}
    </section>
  );
}

/**
 * Detail panel: single node (click) or all graph nodes tied to the latest chat SQL result.
 */
export default function NodeDetail({
  nodes = [],
  edges = [],
  sql,
  mode = 'single',
  onExpand,
  onClose,
  expandedNodeId,
}) {
  if (!nodes.length) {
    return (
      <div className="w-[min(100vw-2rem,22rem)] sm:w-96 bg-white border border-slate-200 shadow-xl rounded-xl overflow-hidden flex flex-col max-h-[70vh]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-white">
          <h1 className="text-base font-semibold text-slate-900">Query result</h1>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            aria-label="Close"
          >
            <X size={18} strokeWidth={2} />
          </button>
        </div>
        <div className="p-4 overflow-y-auto">
          <p className="text-sm text-slate-600 mb-3">
            No matching nodes were found on the graph for this query. The SQL still ran successfully.
          </p>
          {sql && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">SQL</div>
              <pre className="text-xs bg-slate-50 border border-slate-200 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap text-slate-800">
                {sql}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  const isQuery = mode === 'query';
  const showExpand = !isQuery && nodes.length === 1;

  return (
    <div className="w-[min(100vw-2rem,22rem)] sm:w-96 bg-white border border-slate-200 shadow-xl rounded-xl overflow-hidden flex flex-col max-h-[70vh]">
      <div className="flex-shrink-0 flex items-start justify-between gap-2 px-4 py-3 border-b border-slate-200 bg-white">
        <div className="min-w-0">
          <h1 className="text-base font-semibold text-slate-900 leading-tight">
            {isQuery ? 'Nodes from query' : nodes[0]?.label || nodes[0]?.type}
          </h1>
          {isQuery && (
            <p className="text-xs text-slate-500 mt-1">
              {nodes.length} node{nodes.length === 1 ? '' : 's'} linked to this result
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          aria-label="Close"
        >
          <X size={18} strokeWidth={2} />
        </button>
      </div>

      {isQuery && sql && (
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">Generated SQL</div>
          <pre className="text-[11px] text-slate-700 whitespace-pre-wrap break-all max-h-24 overflow-y-auto font-mono leading-snug">
            {sql}
          </pre>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {nodes.map((node) => (
          <NodeSection
            key={node.id}
            node={node}
            edges={edges}
            omitHeading={!isQuery && nodes.length === 1}
            onExpand={showExpand ? onExpand : undefined}
            isExpanded={expandedNodeId === node.id}
          />
        ))}
      </div>
    </div>
  );
}
