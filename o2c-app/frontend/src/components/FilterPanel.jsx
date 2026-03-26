import { NODE_COLORS, ALL_NODE_TYPES } from '../config/graphConfig';

/**
 * Filter panel for toggling node types and searching.
 */
export default function FilterPanel({
  activeTypes,
  onToggleType,
  searchQuery,
  onSearchChange,
  nodeCount,
  edgeCount,
  expandedNodeId,
  onClearExpand,
}) {
  return (
    <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-xl p-4 w-64 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
      {/* Title */}
      <h1 className="text-sm font-bold text-slate-900 mb-1">
        Graph Filters
      </h1>
      <p className="text-[11px] text-slate-500 mb-3">
        {nodeCount} nodes · {edgeCount} edges
      </p>

      {/* Search */}
      <input
        type="text"
        placeholder="Search nodes..."
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg
                   text-sm text-slate-800 placeholder-slate-400 
                   focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30
                   transition-all mb-3"
      />

      {/* Expanded Node Indicator */}
      {expandedNodeId && (
        <div className="mb-3 px-3 py-2 bg-blue-50 border border-blue-100 
                        rounded-lg flex items-center justify-between">
          <span className="text-xs text-blue-700">
            Expanded: <span className="font-mono font-medium">{expandedNodeId.split(':')[1]}</span>
          </span>
          <button
            onClick={onClearExpand}
            className="text-blue-600 hover:text-blue-800 text-xs font-medium"
          >
            Clear
          </button>
        </div>
      )}

      {/* Node type filters */}
      <div className="space-y-1.5">
        <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
          Node Types
        </p>
        {ALL_NODE_TYPES.map(type => {
          const isActive = activeTypes.has(type);
          const color = NODE_COLORS[type];
          return (
            <button
              key={type}
              onClick={() => onToggleType(type)}
              className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left
                          text-xs font-medium transition-all
                          ${isActive
                            ? 'bg-slate-100 text-slate-900'
                            : 'bg-transparent text-slate-400 hover:bg-slate-50'
                          }`}
            >
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: isActive ? color : '#cbd5e1' }}
              />
              {type}
            </button>
          );
        })}
      </div>

      {/* Instructions */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <p className="text-[10px] text-slate-500 leading-relaxed">
          <strong>Click</strong> a node to inspect · <strong>Right-click</strong> to expand
        </p>
      </div>
    </div>
  );
}
