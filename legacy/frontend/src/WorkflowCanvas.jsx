import React, { useCallback, useMemo, useState, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import ApprovalNode from './ApprovalNode';
import RightDetailPanel from './RightDetailPanel';
import { getElkLayoutedElements } from './elkLayout';
import { Workflow, Info } from 'lucide-react';

const nodeTypes = {
  approvalNode: ApprovalNode,
};

const NODE_WIDTH = 320;
const NODE_HEIGHT = 130;

export default function WorkflowCanvas({ uiData }) {
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [direction, setDirection] = useState('TB'); // 'TB' (Down) or 'LR' (Right)
  const [filterCategory, setFilterCategory] = useState('all');
  const [layoutLoading, setLayoutLoading] = useState(true);

  const approvalsMap = useMemo(() => uiData?.approvals_map || {}, [uiData]);
  const summary = uiData?.summary || {};

  // Extract unique categories for filtering
  const categories = useMemo(() => {
    const set = new Set();
    Object.values(approvalsMap).forEach((app) => {
      if (app.category) set.add(app.category.toLowerCase());
    });
    return Array.from(set);
  }, [approvalsMap]);

  // Base raw nodes from Agent 4 payload
  const initialNodes = useMemo(() => {
    if (!uiData?.nodes || uiData.nodes.length === 0) return [];
    return uiData.nodes.map((n, i) => ({
      id: String(n.id),
      type: 'approvalNode',
      data: {
        ...n.data,
        is_first: i === 0,
      },
      draggable: false, // Locked read-only graph: layout engine is sole source of truth
      position: n.position || { x: 0, y: 0 },
    }));
  }, [uiData]);

  // Base raw edges from Agent 4 payload with clean orthogonal styling
  const initialEdges = useMemo(() => {
    if (!uiData?.edges || uiData.edges.length === 0) return [];
    return uiData.edges.map((e) => ({
      id: String(e.id),
      source: String(e.source),
      target: String(e.target),
      type: 'smoothstep', // Clean right-angle rounded step routing
      animated: false,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 12,
        height: 12,
        color: '#10b981',
      },
      style: { stroke: '#10b981', strokeWidth: 1.75 },
    }));
  }, [uiData]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Compute ELK.js layout asynchronously whenever nodes, edges, or direction changes
  useEffect(() => {
    let isCancelled = false;
    setLayoutLoading(true);

    getElkLayoutedElements(initialNodes, initialEdges, direction).then(
      ({ layoutedNodes, layoutedEdges }) => {
        if (!isCancelled) {
          setNodes(layoutedNodes);
          setEdges(layoutedEdges);
          setLayoutLoading(false);
        }
      }
    );

    return () => {
      isCancelled = true;
    };
  }, [initialNodes, initialEdges, direction, setNodes, setEdges]);

  // Compute dynamic translateExtent bounds based on ELK layout positions to keep canvas bounded
  const translateExtent = useMemo(() => {
    if (!nodes || nodes.length === 0) {
      return [[-50, -50], [1200, 900]];
    }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    nodes.forEach((n) => {
      const x = n.position.x;
      const y = n.position.y;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x + NODE_WIDTH > maxX) maxX = x + NODE_WIDTH;
      if (y + NODE_HEIGHT > maxY) maxY = y + NODE_HEIGHT;
    });

    const paddingX = 80;
    const paddingY = 80;

    return [
      [minX - paddingX, minY - paddingY],
      [maxX + paddingX, maxY + paddingY],
    ];
  }, [nodes]);

  // Handle node selection: highlights immediate incoming & outgoing edges, de-emphasizing unrelated paths
  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeId(node.id);

    setEdges((eds) =>
      eds.map((edge) => {
        const isConnected = edge.source === node.id || edge.target === node.id;
        return {
          ...edge,
          style: isConnected
            ? { stroke: '#059669', strokeWidth: 3 }
            : { stroke: '#cbd5e1', strokeWidth: 1.5, opacity: 0.3 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: isConnected ? 16 : 10,
            height: isConnected ? 16 : 10,
            color: isConnected ? '#059669' : '#94a3b8',
          },
        };
      })
    );
  }, [setEdges]);

  // Handle panel close: restore standard clean emerald edge styling
  const handleClosePanel = useCallback(() => {
    setSelectedNodeId(null);
    setEdges((eds) =>
      eds.map((edge) => ({
        ...edge,
        style: { stroke: '#10b981', strokeWidth: 1.75, opacity: 1 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: '#10b981',
        },
      }))
    );
  }, [setEdges]);

  // Filter effect on nodes
  useEffect(() => {
    if (filterCategory === 'all') {
      setNodes((nds) => nds.map((n) => ({ ...n, hidden: false })));
    } else {
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          hidden: (n.data.category || '').toLowerCase() !== filterCategory,
        }))
      );
    }
  }, [filterCategory, setNodes]);

  const selectedApproval = useMemo(() => {
    if (!selectedNodeId) return null;
    return approvalsMap[selectedNodeId] || null;
  }, [selectedNodeId, approvalsMap]);

  return (
    <div className="relative w-full h-[780px] bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
      {/* Top Header Bar */}
      <div className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between z-10">
        <div className="flex items-center space-x-3.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shadow-2xs">
            <Workflow className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-slate-800 tracking-tight">
                Clearance Dependency Graph
              </h3>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                ELK.js Layered DAG
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              {summary.factory_name} • <span className="text-slate-700 font-semibold">{summary.total_approvals} Clearances</span> • <span className="text-emerald-600 font-semibold">~{summary.critical_path_days}d Timeline</span>
            </p>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center space-x-3">
          {/* Category Filter Pills */}
          {categories.length > 0 && (
            <div className="hidden md:flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
              <button
                onClick={() => setFilterCategory('all')}
                className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                  filterCategory === 'all'
                    ? 'bg-white text-emerald-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setFilterCategory(cat)}
                  className={`px-3 py-1 rounded-md text-[11px] font-semibold capitalize transition-all ${
                    filterCategory === cat
                      ? 'bg-white text-emerald-700 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}

          {/* Flowchart Layout Orientation Controls */}
          <div className="bg-slate-100 p-1 rounded-lg border border-slate-200 flex space-x-1">
            <button
              onClick={() => setDirection('TB')}
              className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                direction === 'TB'
                  ? 'bg-white text-emerald-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Top-to-Bottom
            </button>
            <button
              onClick={() => setDirection('LR')}
              className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                direction === 'LR'
                  ? 'bg-white text-emerald-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Left-to-Right
            </button>
          </div>
        </div>
      </div>

      {/* Attio Canvas Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Canvas with Dot Grid Background */}
        <div className="flex-1 h-full relative bg-[#fafafa]">
          {!layoutLoading && nodes.length > 0 && (
            <ReactFlow
              key={direction}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              nodesDraggable={false} // Strictly read-only
              nodesConnectable={false}
              elementsSelectable={true}
              translateExtent={translateExtent}
              fitView
              fitViewOptions={{ padding: 0.12, maxZoom: 1.0 }}
              minZoom={0.35}
              maxZoom={1.5}
              proOptions={{ hideAttribution: true }}
            >
              {/* Attio Dot Grid Background */}
              <Background 
                variant={BackgroundVariant.Dots} 
                gap={20} 
                size={1.5}
                color="#cbd5e1" 
              />
              
              {/* Zoom Controls */}
              <Controls 
                className="!bg-white !border-slate-200 !shadow-sm !rounded-xl overflow-hidden [&>button]:!bg-white [&>button]:!border-slate-200 [&>button]:!text-slate-700 hover:[&>button]:!bg-slate-50 hover:[&>button]:!text-emerald-600" 
                showInteractive={false}
              />

              {/* Helper Pill */}
              {!selectedNodeId && (
                <Panel position="bottom-left" className="bg-white border border-slate-200 rounded-lg px-3.5 py-2 text-xs text-slate-700 flex items-center space-x-2 shadow-sm">
                  <Info className="w-4 h-4 text-emerald-600" />
                  <span className="font-medium">Click any node to inspect official government links, documents checklist, and prerequisite blockers</span>
                </Panel>
              )}
            </ReactFlow>
          )}

          {layoutLoading && (
            <div className="w-full h-full flex items-center justify-center bg-[#fafafa]">
              <div className="flex items-center space-x-2 text-slate-500 text-sm font-medium">
                <Workflow className="w-5 h-5 animate-spin text-emerald-600" />
                <span>Computing optimal DAG layout...</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Detail Panel: Pops out when a flowchart node is clicked */}
        {selectedApproval && (
          <div className="w-[400px] lg:w-[440px] h-full transition-all duration-300 ease-in-out z-20 shrink-0 animate-in slide-in-from-right">
            <RightDetailPanel
              selectedApproval={selectedApproval}
              summary={summary}
              onClose={handleClosePanel}
            />
          </div>
        )}
      </div>
    </div>
  );
}
