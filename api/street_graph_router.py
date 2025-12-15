"""
Street Graph Router - A* pathfinding on real street network
Builds proper routes along streets when OSRM is unavailable
"""
import heapq
import math
from typing import Dict, List, Tuple, Optional


class StreetGraphRouter:
    """
    A* pathfinding on street network graph
    """
    
    def __init__(self, streets: List[Dict]):
        """
        Build graph from street data
        
        Args:
            streets: List of street dicts with 'coords' field
        """
        self.streets = streets
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Dict:
        """Build adjacency graph from streets"""
        graph = {}
        
        for street in self.streets:
            coords = street.get('coords', [])
            if len(coords) < 2:
                continue
            
            # Add edges between consecutive points
            for i in range(len(coords) - 1):
                p1 = tuple(coords[i])  # (lat, lng)
                p2 = tuple(coords[i + 1])
                
                # Calculate distance
                dist = self._haversine(p1[0], p1[1], p2[0], p2[1])
                
                # Add bidirectional edges
                if p1 not in graph:
                    graph[p1] = []
                if p2 not in graph:
                    graph[p2] = []
                
                graph[p1].append((p2, dist))
                graph[p2].append((p1, dist))
        
        return graph
    
    def find_route(self, start_lat: float, start_lng: float, 
                   end_lat: float, end_lng: float) -> List[List[float]]:
        """
        Find route using A* algorithm
        
        Returns:
            List of [lng, lat] coordinates (GeoJSON format)
        """
        # Find nearest nodes to start and end
        start_node = self._find_nearest_node(start_lat, start_lng)
        end_node = self._find_nearest_node(end_lat, end_lng)
        
        if not start_node or not end_node:
            # Fallback to direct line
            return [[start_lng, start_lat], [end_lng, end_lat]]
        
        # Run A* algorithm
        path = self._astar(start_node, end_node)
        
        if not path:
            # No path found, use direct line
            return [[start_lng, start_lat], [end_lng, end_lat]]
        
        # Convert path to GeoJSON format [lng, lat]
        route_coords = [[start_lng, start_lat]]  # Start point
        
        for node in path:
            route_coords.append([node[1], node[0]])  # node is (lat, lng), convert to [lng, lat]
        
        route_coords.append([end_lng, end_lat])  # End point
        
        return route_coords
    
    def _find_nearest_node(self, lat: float, lng: float) -> Optional[Tuple]:
        """Find nearest node in graph"""
        if not self.graph:
            return None
        
        min_dist = float('inf')
        nearest = None
        
        for node in self.graph.keys():
            dist = self._haversine(lat, lng, node[0], node[1])
            if dist < min_dist:
                min_dist = dist
                nearest = node
        
        return nearest
    
    def _astar(self, start: Tuple, goal: Tuple) -> List[Tuple]:
        """
        A* pathfinding algorithm
        
        Returns:
            List of nodes (lat, lng) from start to goal
        """
        # Priority queue: (f_score, node)
        open_set = [(0, start)]
        
        # Track path
        came_from = {}
        
        # g_score: cost from start to node
        g_score = {start: 0}
        
        # f_score: g_score + heuristic
        f_score = {start: self._haversine(start[0], start[1], goal[0], goal[1])}
        
        visited = set()
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Goal reached
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            # Explore neighbors
            for neighbor, edge_cost in self.graph.get(current, []):
                if neighbor in visited:
                    continue
                
                tentative_g = g_score[current] + edge_cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self._haversine(neighbor[0], neighbor[1], goal[0], goal[1])
                    f_score[neighbor] = f
                    heapq.heappush(open_set, (f, neighbor))
        
        # No path found
        return []
    
    def _reconstruct_path(self, came_from: Dict, current: Tuple) -> List[Tuple]:
        """Reconstruct path from came_from dict"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km"""
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
