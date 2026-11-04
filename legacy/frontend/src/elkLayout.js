import ELK from 'elkjs/lib/elk.bundled.js';

const elk = new ELK();

const NODE_WIDTH = 320;
const NODE_HEIGHT = 130;

/**
 * Transitive reduction of a DAG to remove redundant bypass edges:
 * E.g., if A -> B and B -> C, then any direct edge A -> C is redundant and causes edge overlap/crossing.
 */
export const performTransitiveReduction = (nodes, edges) => {
  const adj = new Map();
  nodes.forEach((n) => adj.set(n.id, new Set()));
  edges.forEach((e) => {
    if (adj.has(e.source)) {
      adj.get(e.source).add(e.target);
    }
  });

  // Check if target is reachable from source via path of length >= 2
  const isReachable = (source, target, visited = new Set()) => {
    const neighbors = adj.get(source) || new Set();
    for (const neighbor of neighbors) {
      if (neighbor === target) continue; // Direct edge doesn't count
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);

      const subNeighbors = adj.get(neighbor) || new Set();
      if (subNeighbors.has(target)) return true;
      if (isReachable(neighbor, target, visited)) return true;
    }
    return false;
  };

  return edges.filter((e) => !isReachable(e.source, e.target));
};

/**
 * ELK Layered Layout with Orthogonal Edge Routing, Crossing Minimization,
 * and Separated Port Positioning.
 */
export const getElkLayoutedElements = async (nodes, edges, direction = 'TB') => {
  if (!nodes || nodes.length === 0) {
    return { layoutedNodes: [], layoutedEdges: [] };
  }

  // 1. Clean up redundant transitive edges that cause crossing/long-detours
  const reducedEdges = performTransitiveReduction(nodes, edges);

  const isVertical = direction === 'TB';
  const elkDirection = isVertical ? 'DOWN' : 'RIGHT';

  // 2. Build ELK Graph with layered algorithm and orthogonal routing
  const elkGraph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': elkDirection,
      // Layering & Crossing Minimization
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.layered.nodePlacement.strategy': 'BRANDES_KOEPF',
      'elk.layered.nodePlacement.favorStraightEdges': 'true',
      'elk.layered.cycleBreaking.strategy': 'DEPTH_FIRST',
      
      // Spacing & Clear Corridors
      'elk.spacing.nodeNode': isVertical ? '90' : '100',
      'elk.layered.spacing.nodeNodeBetweenLayers': isVertical ? '110' : '120',
      'elk.layered.spacing.edgeEdgeBetweenLayers': '30',
      'elk.layered.spacing.edgeNodeBetweenLayers': '40',
      'elk.spacing.edgeNode': '40',
      'elk.spacing.edgeEdge': '25',
      
      // Edge Routing & Clean Orthogonal Right-Angle Routes
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.layered.unnecessaryBendpoints': 'false',
      'elk.layered.mergeEdges': 'false', // Keep branches physically separated
      'elk.layered.separateConnectedComponents': 'true',
      
      // Port distribution to avoid bunching all edges on one single point
      'elk.portConstraints': 'FREE',
    },
    children: nodes.map((node) => ({
      id: node.id,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    })),
    edges: reducedEdges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };

  try {
    const layoutedGraph = await elk.layout(elkGraph);

    const layoutedNodes = nodes.map((node, index) => {
      const elkNode = layoutedGraph.children?.find((n) => n.id === node.id);
      const posX = elkNode?.x ?? 0;
      const posY = elkNode?.y ?? 0;

      return {
        ...node,
        targetPosition: isVertical ? 'top' : 'left',
        sourcePosition: isVertical ? 'bottom' : 'right',
        data: {
          ...node.data,
          is_first: index === 0 || (!reducedEdges.some((e) => e.target === node.id)),
        },
        position: { x: posX, y: posY },
      };
    });

    return { layoutedNodes, layoutedEdges: reducedEdges };
  } catch (error) {
    console.error('ELK Layout Error, falling back to original coordinates:', error);
    return { layoutedNodes: nodes, layoutedEdges: edges };
  }
};
