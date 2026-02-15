"""
AutoDrive Network Data Structures

This module contains the data classes for representing an AutoDrive road network:
waypoints, connections, and map markers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Waypoint:
    """Represents a single waypoint in the AutoDrive network."""
    id: int
    x: float  # East-West coordinate
    y: float  # Altitude
    z: float  # North-South coordinate
    flag: int = 0  # 0=REGULAR, 1=SUBPRIO
    outgoing: List[int] = field(default_factory=list)  # IDs of destination waypoints
    incoming: List[int] = field(default_factory=list)  # IDs of source waypoints
    
    # Flag constants
    FLAG_REGULAR = 0
    FLAG_SUBPRIO = 1


@dataclass
class MapMarker:
    """Represents a named destination marker attached to a waypoint."""
    waypoint_id: int
    name: str
    group: str = "All"


class RoadNetwork:
    """
    Represents the complete AutoDrive road network for a map.
    Contains waypoints and their connections, plus named markers.
    """
    
    def __init__(self):
        self.waypoints: Dict[int, Waypoint] = {}
        self.markers: List[MapMarker] = []
        self.map_name: str = ""
        self.version: str = ""
        self.route_version: str = ""
        self.route_author: str = ""
        self.route_version: str = ""
        self.route_author: str = ""
    
    def get_next_id(self) -> int:
        """Get the next available waypoint ID."""
        if not self.waypoints:
            return 1
        return max(self.waypoints.keys()) + 1

    def add_waypoint(self, wp: Waypoint):
        """Add a waypoint to the network."""
        self.waypoints[wp.id] = wp
    
    def get_waypoint(self, wp_id: int) -> Optional[Waypoint]:
        """Get a waypoint by ID."""
        return self.waypoints.get(wp_id)
    
    def add_marker(self, marker: MapMarker):
        """Add a marker to the network."""
        self.markers.append(marker)
    
    def get_marker_for_waypoint(self, wp_id: int) -> Optional[MapMarker]:
        """Get the marker associated with a waypoint, if any."""
        for marker in self.markers:
            if marker.waypoint_id == wp_id:
                return marker
    def remove_marker(self, wp_id: int) -> bool:
        """Remove the marker associated with a waypoint."""
        for i, marker in enumerate(self.markers):
            if marker.waypoint_id == wp_id:
                del self.markers[i]
                return True
        return False

    def rename_marker(self, wp_id: int, new_name: str, new_group: str) -> bool:
        """
        Update or create a marker for a waypoint.
        Returns True if successful.
        """
        # Check if marker already exists
        for marker in self.markers:
            if marker.waypoint_id == wp_id:
                marker.name = new_name
                marker.group = new_group
                return True
        
        # If not, create it
        from .network_data import MapMarker
        new_marker = MapMarker(waypoint_id=wp_id, name=new_name, group=new_group)
        self.markers.append(new_marker)
        return True

    def get_all_groups(self) -> List[str]:
        """Get a sorted list of all unique marker groups."""
        groups = set()
        groups.add("All") # Always include 'All'
        for marker in self.markers:
            groups.add(marker.group)
        return sorted(list(groups))
    
    def clear(self):
        """Clear all network data."""
        self.waypoints.clear()
        self.markers.clear()
        self.map_name = ""
        self.version = ""
        self.route_version = ""
        self.route_author = ""
    
    def remove_waypoint(self, wp_id: int) -> bool:
        """
        Remove a waypoint and all associated connections and markers.
        """
        if wp_id not in self.waypoints:
            return False
            
        # 1. Remove from other waypoints' outgoing/incoming lists
        # We must iterate over all waypoints because 'incoming' lists might be unreliable 
        # (or simply because we need to clear references anywhere)
        # Optimization: use the 'incoming' and 'outgoing' lists of the node to be deleted to find neighbors
        
        target_wp = self.waypoints[wp_id]
        
        # Remove me from my neighbors' incoming lists
        for out_id in target_wp.outgoing:
            neighbor = self.get_waypoint(out_id)
            if neighbor and wp_id in neighbor.incoming:
                neighbor.incoming.remove(wp_id)
                
        # Remove me from my parents' outgoing lists
        for in_id in target_wp.incoming:
            parent = self.get_waypoint(in_id)
            if parent and wp_id in parent.outgoing:
                parent.outgoing.remove(wp_id)
        
        # 2. Remove markers associated with this waypoint
        self.markers = [m for m in self.markers if m.waypoint_id != wp_id]
        
        # 3. Remove the waypoint itself
        del self.waypoints[wp_id]
        
        return True

    def remove_route(self, from_id: int, to_id: int) -> bool:
        """
        Remove the connection(s) between two waypoints.
        Removes all directional links (outgoing/incoming) in both directions.
        The waypoints themselves are kept.
        
        Returns:
            True if any connection was removed, False otherwise.
        """
        wp1 = self.get_waypoint(from_id)
        wp2 = self.get_waypoint(to_id)
        if not wp1 or not wp2:
            return False
        
        removed = False
        # Remove from_id -> to_id
        if to_id in wp1.outgoing:
            wp1.outgoing.remove(to_id)
            removed = True
        if from_id in wp2.incoming:
            wp2.incoming.remove(from_id)
            removed = True
        # Remove to_id -> from_id (bidirectional case)
        if from_id in wp2.outgoing:
            wp2.outgoing.remove(from_id)
            removed = True
        if to_id in wp1.incoming:
            wp1.incoming.remove(to_id)
            removed = True
        
        return removed

    def add_route(self, from_id: int, to_id: int) -> bool:
        """
        Add a regular unidirectional route from from_id to to_id.
        Fails if any connection already exists between the two waypoints.
        
        Returns:
            True if the route was created, False otherwise.
        """
        wp1 = self.get_waypoint(from_id)
        wp2 = self.get_waypoint(to_id)
        if not wp1 or not wp2:
            return False
        
        # Check if any connection already exists between them
        if (to_id in wp1.outgoing or from_id in wp1.incoming or
            from_id in wp2.outgoing or to_id in wp2.incoming):
            return False
        
        # Create regular unidirectional: from -> to
        wp1.outgoing.append(to_id)
        wp2.incoming.append(from_id)
        return True

    def has_any_connection(self, id1: int, id2: int) -> bool:
        """
        Check if there is any direct connection between two waypoints 
        (in either direction).
        """
        wp1 = self.get_waypoint(id1)
        wp2 = self.get_waypoint(id2)
        if not wp1 or not wp2:
            return False
            
        return (id2 in wp1.outgoing or id1 in wp1.incoming or
                id1 in wp2.outgoing or id2 in wp2.incoming)

    # --- Connection Type Detection ---
    
    def is_dual(self, wp1_id: int, wp2_id: int) -> bool:
        """
        Check if connection between wp1 and wp2 is bidirectional.
        Both waypoints have each other in their outgoing AND incoming lists.
        """
        wp1 = self.get_waypoint(wp1_id)
        wp2 = self.get_waypoint(wp2_id)
        if not wp1 or not wp2:
            return False
        
        return (wp2_id in wp1.outgoing and wp1_id in wp2.incoming and
                wp1_id in wp2.outgoing and wp2_id in wp1.incoming)
    
    def is_reverse(self, wp1_id: int, wp2_id: int) -> bool:
        """
        Check if connection from wp1 to wp2 is reverse-only.
        wp1 has wp2 in outgoing, but wp2 doesn't know about wp1 at all.
        """
        wp1 = self.get_waypoint(wp1_id)
        wp2 = self.get_waypoint(wp2_id)
        if not wp1 or not wp2:
            return False
        
        return (wp2_id in wp1.outgoing and wp1_id not in wp2.incoming and
                wp1_id not in wp2.outgoing and wp2_id not in wp1.incoming)
    
    def is_regular(self, wp1_id: int, wp2_id: int) -> bool:
        """
        Check if connection from wp1 to wp2 is regular unidirectional.
        wp1 has wp2 in outgoing, wp2 has wp1 in incoming, but not vice versa.
        """
        wp1 = self.get_waypoint(wp1_id)
        wp2 = self.get_waypoint(wp2_id)
        if not wp1 or not wp2:
            return False
        
        return (wp2_id in wp1.outgoing and wp1_id in wp2.incoming and
                wp1_id not in wp2.outgoing and wp2_id not in wp1.incoming)
    
    def swap_route_direction(self, from_id: int, to_id: int) -> bool:
        """
        Cycle through route direction types: Regular -> Dual -> Reverse -> Regular
        
        Args:
            from_id: Source waypoint ID
            to_id: Destination waypoint ID
            
        Returns:
            True if successful, False otherwise.
        """
        wp1 = self.get_waypoint(from_id)
        wp2 = self.get_waypoint(to_id)
        
        if not wp1 or not wp2:
            return False
        
        # Check if there's any connection at all
        if to_id not in wp1.outgoing and from_id not in wp2.outgoing:
            return False
        
        # Determine current state and apply transformation
        # Determine current state and apply transformation
        # Use canonical order (min->max) to ensure deterministic cycle
        # Cycle: Regular(Min->Max) -> Regular(Max->Min) -> Dual -> Regular(Min->Max)
        p1, p2 = min(from_id, to_id), max(from_id, to_id)
        
        if self.is_dual(p1, p2):
            # Dual -> Regular (Min->Max) "Positif"
            # Remove Max->Min
            if p1 in self.get_waypoint(p2).outgoing:
                self.get_waypoint(p2).outgoing.remove(p1)
            if p2 in self.get_waypoint(p1).incoming:
                self.get_waypoint(p1).incoming.remove(p2)
            # Ensure Min->Max exists (it should in Dual)
            if p2 not in self.get_waypoint(p1).outgoing:
                self.get_waypoint(p1).outgoing.append(p2)
            if p1 not in self.get_waypoint(p2).incoming:
                self.get_waypoint(p2).incoming.append(p1)
                
        elif self.is_regular(p1, p2):
            # Regular (Min->Max) -> Regular (Max->Min) "Négatif"
            # Remove Min->Max
            if p2 in self.get_waypoint(p1).outgoing:
                self.get_waypoint(p1).outgoing.remove(p2)
            if p1 in self.get_waypoint(p2).incoming:
                self.get_waypoint(p2).incoming.remove(p1)
            # Add Max->Min
            if p1 not in self.get_waypoint(p2).outgoing:
                self.get_waypoint(p2).outgoing.append(p1)
            if p2 not in self.get_waypoint(p1).incoming:
                self.get_waypoint(p1).incoming.append(p2)
                
        elif self.is_regular(p2, p1):
            # Regular (Max->Min) -> Dual
            # Add Min->Max (Max->Min already exists)
            if p2 not in self.get_waypoint(p1).outgoing:
                self.get_waypoint(p1).outgoing.append(p2)
            if p1 not in self.get_waypoint(p2).incoming:
                self.get_waypoint(p2).incoming.append(p1)
                
        else:
            # Fallback or Reverse state -> Regular (Min->Max)
            # Clean up
            wp1 = self.get_waypoint(from_id)
            wp2 = self.get_waypoint(to_id)
            
            # Remove all connections between them
            if to_id in wp1.outgoing: wp1.outgoing.remove(to_id)
            if from_id in wp1.incoming: wp1.incoming.remove(from_id) # Error in original logic, fixed here? No, incoming contains neighbor IDs
            
            # Safe cleanup manually using IDs
            wpp1 = self.get_waypoint(p1)
            wpp2 = self.get_waypoint(p2)
            
            if p2 in wpp1.outgoing: wpp1.outgoing.remove(p2)
            if p1 in wpp1.incoming: wpp1.incoming.remove(p1)
            if p1 in wpp2.outgoing: wpp2.outgoing.remove(p1)
            if p2 in wpp2.incoming: wpp2.incoming.remove(p2)
            
            # Add Regular (Min->Max)
            wpp1.outgoing.append(p2)
            wpp2.incoming.append(p1)
        
        return True
    
    def get_bounds(self) -> tuple:
        """
        Get the bounding box of all waypoints.
        Returns (min_x, min_z, max_x, max_z) or None if no waypoints.
        """
        if not self.waypoints:
            return None
        
        xs = [wp.x for wp in self.waypoints.values()]
        zs = [wp.z for wp in self.waypoints.values()]
        
        return (min(xs), min(zs), max(xs), max(zs))
    
    def __len__(self):
        return len(self.waypoints)
