from typing import Dict, Tuple, Any, Optional
import logging
import networkx as nx
import pulp

# Configure logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def minimal_fraction_max_matching(G: nx.Graph):
    """Find a maximum fractional matching in the graph with the minimum 0.5 edges.

    A fractional matching is a generalization of a matching where each edge
    can have a value of 0, 1/2, or 1. The sum of edge values incident to any
    vertex cannot exceed 1.

    Parameters
    ----------
    G : NetworkX graph
        Undirected graph

    initial_matching : dict, optional (default=None)
        A dictionary mapping edge tuples (u,v) to values (0, 0.5, or 1).
        If not provided, an empty matching is used.

    Returns
    -------
    matching : dict
        A dictionary mapping edge tuples (u,v) to values (0, 0.5, or 1)
        representing the maximum fractional matching.

    Examples
    --------
    >>> G = nx.Graph([(1, 2), (1,3),(2,3)])
    >>> minimal_fraction_max_matching(G)
    {(1, 2): 0.5, (1, 3): 0.5, (2, 3): 0.5}
    >>> G =  nx.Graph([(1, 2), (1,3),(2,3),(3,4)])
    >>> minimal_fraction_max_matching(G)
    {(1, 2): 1, (3, 4): 1}
    >>> G = nx.Graph([(1, 2), (1,3),(2,4),(3,5),(4,5),(5,6),(6,7)])
    >>> minimal_fraction_max_matching(G)
    {(1, 2): 0.5, (1, 3): 0.5, (2, 4): 0.5, (3, 5): 0.5, (4, 5): 0.5, (6, 7): 1}

    Notes
    -----
    Based on the algorithm described in:
    "Konig-Egervary graphs, 2-bicritical graphs and fractional matchings"
    by Jean-Marie Bourjolly and William R. Pulleyblank
    Proggramer: Roi Sibony
    Date: 20.05.2024
    """
    solver = FractionalMatchingSolver(G)
    log.debug("#"*20 + " Starting the solver for minimal_fractoin_max_matching " + "#"*20)
    log.info("Starting fractional matching solver.")
    log.debug("Initial Graph" ":%s", G.edges(data=True))
    return solver.solve() 


class FractionalMatchingSolver:
    """Class for finding a maximum fractional matching in a graph."""
    
    def __init__(self, G: nx.Graph):
        """Initialize with a graph and optional initial matching."""
        self.G = G
        # Initialize the matching if not provided
        self.x = {} 
        
        # Ensure symmetric representation (if (u,v):val then also (v,u):val)
        for (u, v), val in list(self.x.items()):
            self.x[(v, u)] = val
            
        # These will be initialized in each solve iteration
        self.labels = {}
        self.preds = {}
    
    def solve(self) -> Dict[Tuple[Any, Any], float]:
        """Find a maximum fractional matching."""
        # Main loop: keeps trying to augment the matching until no further improvement
        while True:
            # Step 1: Initialize labels and predecessors
            self._initialize_labels()
            
            # Continue until we can't augment anymore
            augmented = False
            
            while not augmented:
                # Step 2: Scan edges to find potential augmentation
                result = self._edge_scan()

                log.info("Edge scan result: %s", result)
                # If no augmenting structure found, we're done with this phase
                if result is None:
                    log.debug("#"*20 + " Finished the current iteration " + "#"*20)
                    break
                    
                u, v = result
                # Step 3: Check the labels of the vertices
                # Handle based on the type of augmenting structure found
                if self.labels.get(v) == "+":
                    # Found an augmenting path/cycle of type 1 or 3
                    log.info("V is labeled '+', performing type 1/3 augmentation.")
                    self._augment(u, v)
                    augmented = True
                else:
                    # step 4
                    # Found a potential type 2 augmentation or need to label more nodes
                    log.info("V is unlabeled, checking for type 2 augmentation or labeling.")
                    if self._label_or_augment(u, v):
                        log.info("Type 2 augmentation possible, augmenting.")
                        self._augment(u, v)
                        augmented = True
            # If we couldn't augment in this phase, we're done
            if not augmented:
                break
        
        # Return only one direction of edges to match NetworkX convention
        result = {}
        for (u, v), val in self.x.items():
            if val > 0 and u < v:  # Only keep one direction and non-zero edges
                result[(u, v)] = val
        log.info("Final matching: %s", result)  
        return result
    
    def _initialize_labels(self) -> None:
        """
        Step 1 (Initialization).
        Label every unsaturated node "+" and every saturated node None.
        Initialize all predecessor pointers to None.
        """
        self.labels = {}
        self.preds = {v: None for v in self.G.nodes}   
        log.debug("Initializing labels and predecessors.")
        # Calculate saturation for each node
        node_values = {}
        for (u, v), val in self.x.items():
            node_values[u] = node_values.get(u, 0) + val
        
        # Label unsaturated nodes with "+"
        for node in self.G:
            saturation = node_values.get(node, 0)
            if saturation < 1:
                self.labels[node] = "+"
            else:
                self.labels[node] = None
            if node not in self.preds:
                self.preds[node] = None
        log.debug("Labels initialized: %s \n finshed the initilization", self.labels)

    def _edge_scan(self) -> Optional[Tuple[Any, Any]]:
        """
        Step 2 (Edge scan).
        Scan every edge [u,v] with u labelled "+". 
        - If v is "-", termination condition reached (matching is max).
        - Otherwise return a pair (u,v) to indicate where to go next:
            • if v is "+", caller should perform the type-1/3 augment; 
            • if v is None, caller should do label_or_augment.
        """
        log.debug("Scanning edges for potential augmenting structures.")
        # Scan all edges where one endpoint is labeled "+"
        for u in self.G:
            if self.labels.get(u) == "+":
                for v in self.G.neighbors(u):
                    # Check if this edge can be used for augmentation
                    
                    # Case 1: v is labeled "-" - terminates search
                    if self.labels.get(v) == "-":
                        continue
                        
                    # Case 2: v is labeled "+" - type 1/3 augmentation possible
                    if self.labels.get(v) == "+":
                        return (u, v)
                        
                    # Case 3: v is unlabeled - potential type 2 augmentation
                    if self.labels.get(v) is None:
                        # Only consider edges with x-value < 1
                        edge_val = self.x.get((u, v), 0)
                        if edge_val < 1:
                            return (u, v)
        
        # No augmenting structure found
        return None
    # Helper function to build the cycle
    def _build_cycle(self,path_u: list[Any], path_v: list[Any]) -> list[Any]:
        """
        Return the ordered list of vertices that form the simple cycle
        u → ... → v → u (edge v-u closes it).
        Both paths run from the vertex to the common root,
        so they always share at least that root.
        """
        set_u = set(path_u)
        # first common vertex when climbing from v towards the root
        lca = next(node for node in path_v if node in set_u)

        idx_u = path_u.index(lca)   # where LCA sits inside path_u
        idx_v = path_v.index(lca)   #               inside path_v

        # u ... lca   +   lca-1 ... v   (second part reversed)
        cycle = path_u[:idx_u + 1] + list(reversed(path_v[:idx_v]))
        return cycle            # starts with u, ends with v

    def _augment(self, u: Any, v: Any) -> None:
        """
        Step 3 (Augment).
        Trace back from u and v via preds to their respective unsaturated roots,
        classify it as type 1 or type 3, flip x-values along the cycle/path,
        then clear all labels and preds so we can re-initialize.
        """
        log.debug("Augmenting matching between vertices %s and %s", u, v)
        # Construct paths from u and v back to their roots
        path_u = [u]
        path_v = [v]
        
        # Trace path from u to its root
        current = u
        while self.preds[current] is not None:
            current = self.preds[current]
            path_u.append(current)
        
        # Trace path from v to its root
        current = v
        while self.preds[current] is not None:
            current = self.preds[current]
            path_v.append(current)
        
        # Check if this is type 1 (different roots) or type 3 (same root)
        if path_u[-1] != path_v[-1]:
            # Type 1: augmenting path between two different roots
            # Flip x-values along the path
            # Path from u's root to u
            log.info("Type 1 augmentation: flipping edges along path from u to its root.")
            path_u.reverse()
            for i in range(len(path_u) - 1):
                a, b = path_u[i], path_u[i+1]
                log.debug("Flipping edge (%s, %s)", a, b)
                self.x[(a, b)] = 1 - self.x.get((a, b), 0)
                self.x[(b, a)] = self.x[(a, b)]
            
            # Edge connecting u and v
            self.x[(u, v)] = 1 - self.x.get((u, v), 0)
            self.x[(v, u)] = self.x[(u, v)]
            
            # Path from v to v's root
            for i in range(len(path_v) - 1):
                a, b = path_v[i], path_v[i+1]
                self.x[(a, b)] = 1 - self.x.get((a, b), 0)
                self.x[(b, a)] = self.x[(a, b)]
        else:
            # Type 3: augmenting cycle with a common root
            # Form the cycle by joining the paths
            log.info("Type 3 augmentation: found common root, building cycle.")
            cycle = self._build_cycle(path_u, path_v)
            log.debug("Type 3 augmentation: found cycle %s", cycle)
            if not cycle:
                log.info("No cycle found through vertices:", path_u)
            # Flip x-values around the cycle
            for i in range(len(cycle)):
                a = cycle[i]
                b = cycle[(i + 1) % len(cycle)] 
                log.debug("Flipping edge (%s, %s)", a, b)
                self.x[(a, b)] = 0.5 if self.x.get((a, b), 0) != 0.5 else 0
                self.x[(b, a)] = self.x[(a, b)]
            
            path_v = path_v[::-1]
            # I need i and i+1 to turn on the corresponding edge to 1 depending on if odd or even index
            for i in range(len(path_v) - 1):
                a, b = path_v[i], path_v[i+1]
                log.debug("Final step of the augmentation for the path\nFlipping edge (%s, %s)", a, b)
                self.x[(a, b)] = 1 - self.x.get((a, b), 0)
                self.x[(b, a)] = self.x[(a, b)]

    
    def _label_or_augment(self, u: Any, v: Any) -> None:
        """
        Step 4 (Label or augment).
        If v is saturated but has an incident edge j with x[j]==1, then
          • set label[v] = "-", label[w] = "+" for that neighbor w,
          • set preds[w] = v, preds[v] = u,
          • return to edge_scan.
        Otherwise v lies on a 1/2-cycle: do the type-2 augmentation on that cycle,
        then clear labels/preds for a fresh start.
        """
        # Check if v has a neighbor w with edge value 1
        for w in self.G.neighbors(v):
            if self.x.get((v, w), 0) == 1:
                log.info("We are in the labeling part of the algorithm.")
                log.info("Found saturated neighbor w with edge value 1: %s", w)
                log.debug("Setting labels and predecessors for v=%s, w=%s", v, w)
                # Set labels and predecessors
                self.labels[v] = "-"
                self.labels[w] = "+"
                self.preds[v] = u
                self.preds[w] = v
                return False #return to step 2 (edge scan)
            
        # If we get here, v must be on a 1/2-cycle (type 2 augmentation)
        # Find the 1/2 -cycle by tracing from v
        cycle = [v]
        visited = {v}
        log.info("No saturated neighbor found, looking for 1/2-cycle starting from v: %s", v)
        while True:
            # Find the next node in the cycle (connected by a 1/2 edge)
            current = cycle[-1]
            next_node_found = False
            log.debug("Looking for next node in 1/2-cycle from current: %s", current)
            for next_node in self.G.neighbors(current):
                if self.x.get((current, next_node), 0) == 0.5 and next_node not in visited:
                    cycle.append(next_node)
                    visited.add(next_node)
                    next_node_found = True
                    break
            
            if not next_node_found:
                # Check if we've found a cycle
                for next_node in self.G.neighbors(current):
                    if next_node == cycle[0] and self.x.get((current, next_node), 0) == 0.5:
                        # Found the cycle, now perform the type 2 augmentation
                        for i in range(len(cycle)):
                            a = cycle[i]
                            b = cycle[(i + 1) % len(cycle)]
                            # Change 0.5 edges to 0 or 1 alternately
                            new_val = 0 if i % 2 == 0 else 1
                            log.debug("Augmenting edge (%s, %s) to value %s", a, b, new_val)
                            self.x[(a, b)] = new_val
                            self.x[(b, a)] = new_val
                        return True
                # If we get here, no cycle was found - this shouldn't happen in theory
                log.error("No cycle found in type-2 augmentation step. This should not happen.")
                return False

# def solve_fractional_matching_lp(G):
#     """
#     Solve the fractional matching problem using linear programming.
#     Constrains edge values to be in {0, 0.5, 1}.
#     Returns a dictionary mapping edges to their assigned value.
#     """
#     prob = pulp.LpProblem("FractionalMatching", pulp.LpMaximize)
#     edges = list(G.edges())
#     edge_vars = {}
#     for u, v in edges:
#         edge_vars[(u, v, 0)] = pulp.LpVariable(f"x_{u}_{v}_0", cat=pulp.LpBinary)
#         edge_vars[(u, v, 0.5)] = pulp.LpVariable(f"x_{u}_{v}_0.5", cat=pulp.LpBinary)
#         edge_vars[(u, v, 1)] = pulp.LpVariable(f"x_{u}_{v}_1", cat=pulp.LpBinary)
#         prob += edge_vars[(u, v, 0)] + edge_vars[(u, v, 0.5)] + edge_vars[(u, v, 1)] == 1
#     prob += pulp.lpSum([0.5 * edge_vars[(u, v, 0.5)] + 1 * edge_vars[(u, v, 1)] for u, v in edges])
#     for node in G.nodes():
#         incident_edges = [(u, v) for u, v in edges if u == node or v == node]
#         prob += pulp.lpSum([0.5 * edge_vars[(u, v, 0.5)] + 1 * edge_vars[(u, v, 1)] 
#                             for u, v in incident_edges]) <= 1
#     prob.solve(pulp.PULP_CBC_CMD(msg=False))
#     if prob.status != pulp.LpStatusOptimal:
#         return {}
#     result = {}
#     for u, v in edges:
#         if edge_vars[(u, v, 1)].value() > 0.5:
#             result[(u, v)] = 1.0
#         elif edge_vars[(u, v, 0.5)].value() > 0.5:
#             result[(u, v)] = 0.5
#         else:
#             result[(u, v)] = 0.0
#     return result

# def solve_fractional_matching_lp(G: nx.Graph) -> Dict[Tuple[Any, Any], float]:
#     """
#     Solve via LP, forcing each edge to {0, .5, 1}.
#     Uses the default CBC backend that ships with PuLP.
#     """
#     prob = pulp.LpProblem("FractionalMatching", pulp.LpMaximize)
#     edges = [(min(u, v), max(u, v)) for u, v in G.edges()]   # canonical order
#     x0, x05, x1 = {}, {}, {}                                 # binary vars

#     # variables + "exactly one value" constraints
#     for u, v in edges:
#         x0[(u, v)]  = pulp.LpVariable(f"x_{u}_{v}_0",   cat="Binary")
#         x05[(u, v)] = pulp.LpVariable(f"x_{u}_{v}_05",  cat="Binary")
#         x1[(u, v)]  = pulp.LpVariable(f"x_{u}_{v}_1",   cat="Binary")
#         prob += x0[(u, v)] + x05[(u, v)] + x1[(u, v)] == 1

#     # objective
#     prob += pulp.lpSum(0.5 * x05[e] + 1.0 * x1[e] for e in edges)

#     # vertex capacity ≤ 1
#     for v in G.nodes():
#         incident = [(min(v, u), max(v, u)) for u in G.neighbors(v)]
#         prob += pulp.lpSum(0.5 * x05[e] + 1.0 * x1[e] for e in incident) <= 1

#     prob.solve(pulp.PULP_CBC_CMD(msg=False))
#     if pulp.LpStatus[prob.status] != "Optimal":
#         log.warning("LP did not reach optimality; returning empty dict.")
#         return {}

#     return {
#         e: 1.0 if x1[e].value() > 0.5 else 0.5 if x05[e].value() > 0.5 else 0.0
#         for e in edges
#     }

# ---------------------------------------------------------------
# helper: objective value of any matching
# ---------------------------------------------------------------
def matching_value(matching: Dict[Tuple[Any, Any], float]) -> float:
    return sum(matching.values())

def solve_fractional_matching_lp(G: nx.Graph) -> Dict[Tuple[Any, Any], float]:
    """
    Solve the fractional matching problem using pure Linear Programming.
    Values can be any real number between 0 and 1, but are typically
    restricted to {0, 0.5, 1} at optimal solutions.
    """
    try:
        import cvxpy as cp
    except ImportError:
        raise ImportError("CVXPY is required. Install with: pip install cvxpy")
    
    # Get edges in canonical order
    edges = list(G.edges())
    edges = [(min(u, v), max(u, v)) for u, v in edges]
    
    if not edges:
        return {}
    
    # Create one continuous variable per edge with bounds [0, 1]
    n_edges = len(edges)
    x = cp.Variable(n_edges)
    
    # Create constraints
    constraints = []
    
    # Edge values must be between 0 and 1
    constraints.append(0 <= x)
    constraints.append(x <= 1)
    
    # For each vertex, sum of incident edge values must not exceed 1
    for v in G.nodes():
        incident_indices = []
        for i, (u, w) in enumerate(edges):
            if u == v or w == v:
                incident_indices.append(i)
        
        if incident_indices:  # Only add constraint if vertex has edges
            incident_sum = cp.sum([x[i] for i in incident_indices])
            constraints.append(incident_sum <= 1)
    
    # Objective: maximize the sum of edge values
    objective = cp.Maximize(cp.sum(x))
    
    # Create and solve the problem
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(verbose=False)
    except Exception as e:
        log.error(f"CVXPY solver error: {e}")
        return {}
    
    # Check if the problem was solved successfully
    if prob.status != 'optimal':
        log.warning("LP did not reach optimality; returning empty dict.")
        return {}
    
    # Create result dictionary - only include non-zero values
    # Rounding to handle floating point issues
    result = {}
    for i, (u, v) in enumerate(edges):
        val = x[i].value
        if val > 1e-6:  # Ignore very small values that are essentially zero
            if abs(val - 0.5) < 1e-6:
                result[(u, v)] = 0.5
            elif abs(val - 1.0) < 1e-6:
                result[(u, v)] = 1.0
            else:
                result[(u, v)] = val
    
    return result