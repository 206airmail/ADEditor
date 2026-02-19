import copy
from io import BytesIO
import os
import xml.etree.ElementTree as ET
import zipfile

import wx

from .network_data import RoadNetwork, Waypoint

_ = wx.GetTranslation

class DatasManager(object):
    """
    Singleton class to manage project data
    Only one instance of this class is created, and every one can access it
    """
    _instance = None
    
    # Project data properties
    _projectName = ""
    _savegamePath = ""
    _mapPath = ""
    _adConfigPath = ""
    _mapImages = {} # Stores 'overview' and 'heightmap' keys (wx.Image)
    _projectFilePath = ""
    _roadNetwork = None  # RoadNetwork instance
    _isModified = False
    _hasModifiedData = False  # True if road network data has been modified

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatasManager, cls).__new__(cls)
            cls._instance.Initialize()
        return cls._instance

    def Initialize(self):
        """
        Singleton instance initialization
        """
        self.Clear()
        print("DatasManager initialized")
    
    def Clear(self):
        self._projectName = ""
        self._savegamePath = ""
        self._mapPath = ""
        self._adConfigPath = ""
        self._mapImages = {
            "overview": None,
            "heightmap": None
        }
        self._projectFilePath = ""
        self._roadNetwork = None
        self._isModified = False
        self._hasModifiedData = False
        self._undoStack = []
        self._redoStack = []
        self._historyLimit = 100
        self._isHistoryAction = False

    def createProject(self, project_name=None):
        """
        Reset all data for a new project
        """
        default_name = _("New Project")
        self._projectName = project_name if project_name else default_name
        
        self._savegamePath = ""
        self._mapPath = ""
        self._adConfigPath = ""
        self._mapImages = {
            "overview": None,
            "heightmap": None
        }
        self._roadNetwork = RoadNetwork()
        self._isModified = False
        self._hasModifiedData = False
        self._undoStack.clear()
        self._redoStack.clear()
        print(f"Project created: {self._projectName}")

    def _clone_map_images(self, images_dict):
        cloned = {}
        for key, image in images_dict.items():
            if image is None:
                cloned[key] = None
                continue
            if hasattr(image, "Copy"):
                try:
                    cloned[key] = image.Copy()
                    continue
                except Exception:
                    pass
            cloned[key] = image
        return cloned

    def _create_snapshot(self):
        return {
            "projectName": self._projectName,
            "savegamePath": self._savegamePath,
            "mapPath": self._mapPath,
            "adConfigPath": self._adConfigPath,
            "mapImages": self._clone_map_images(self._mapImages),
            "projectFilePath": self._projectFilePath,
            "roadNetwork": copy.deepcopy(self._roadNetwork),
            "isModified": self._isModified,
            "hasModifiedData": self._hasModifiedData,
        }

    def _restore_snapshot(self, snapshot):
        self._projectName = snapshot["projectName"]
        self._savegamePath = snapshot["savegamePath"]
        self._mapPath = snapshot["mapPath"]
        self._adConfigPath = snapshot["adConfigPath"]
        self._mapImages = self._clone_map_images(snapshot["mapImages"])
        self._projectFilePath = snapshot["projectFilePath"]
        self._roadNetwork = copy.deepcopy(snapshot["roadNetwork"])
        self._isModified = snapshot["isModified"]
        self._hasModifiedData = snapshot["hasModifiedData"]

    def _record_undo_snapshot(self, snapshot):
        if self._isHistoryAction or snapshot is None:
            return
        self._undoStack.append(snapshot)
        if len(self._undoStack) > self._historyLimit:
            self._undoStack.pop(0)
        self._redoStack.clear()

    def _set_network_modified(self):
        self._isModified = True
        self._hasModifiedData = True

    def can_undo(self):
        return len(self._undoStack) > 0

    def can_redo(self):
        return len(self._redoStack) > 0

    def undo(self):
        if not self.can_undo():
            return False

        current_snapshot = self._create_snapshot()
        snapshot = self._undoStack.pop()

        self._isHistoryAction = True
        try:
            self._restore_snapshot(snapshot)
        finally:
            self._isHistoryAction = False

        self._redoStack.append(current_snapshot)
        if len(self._redoStack) > self._historyLimit:
            self._redoStack.pop(0)
        return True

    def redo(self):
        if not self.can_redo():
            return False

        current_snapshot = self._create_snapshot()
        snapshot = self._redoStack.pop()

        self._isHistoryAction = True
        try:
            self._restore_snapshot(snapshot)
        finally:
            self._isHistoryAction = False

        self._undoStack.append(current_snapshot)
        if len(self._undoStack) > self._historyLimit:
            self._undoStack.pop(0)
        return True

    def capture_snapshot(self):
        return self._create_snapshot()

    def register_external_change(self, before_snapshot):
        if before_snapshot is None or self._isHistoryAction:
            return
        self._record_undo_snapshot(before_snapshot)
        self._set_network_modified()

    def saveProjectFile(self, filepath):
        """
        Save current project state to a .adproject file (ZIP format with project.xml)
        """
        try:
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 1. Create and save metadata as XML
                root = ET.Element("AutoDriveProject")
                root.set("version", "1.0")
                
                ET.SubElement(root, "projectName").text = self._projectName
                ET.SubElement(root, "savegamePath").text = self._savegamePath
                ET.SubElement(root, "mapPath").text = self._mapPath
                ET.SubElement(root, "adConfigPath").text = self._adConfigPath
                
                xml_str = ET.tostring(root, encoding='utf-8', method='xml')
                zf.writestr("project.xml", xml_str)
                
                
                # 2. Save AutoDrive config
                # Always save the original from the savegame path if it exists
                if self._adConfigPath and os.path.exists(self._adConfigPath):
                    zf.write(self._adConfigPath, "AutoDrive_config.xml")
                
                # If data has been modified, also save the modified version
                if self._hasModifiedData and self._roadNetwork:
                    from .autodrive_parser import save_autodrive_xml
                    import tempfile
                    # Save to temporary file first
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as tmp:
                        tmp_path = tmp.name
                    try:
                        if save_autodrive_xml(self._roadNetwork, tmp_path):
                            zf.write(tmp_path, "AutoDrive_config_modified.xml")
                            print("Saved modified AutoDrive data to project")
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                    
                # 3. Save images (convert wx.Image to PNG bytes)
                for img_type, img in self._mapImages.items():
                    if img and img.IsOk():
                        import io
                        stream = io.BytesIO()
                        if img.SaveFile(stream, wx.BITMAP_TYPE_PNG):
                            zf.writestr(f"{img_type}.png", stream.getvalue())
                        else:
                            print(f"Warning: Failed to save {img_type} image to stream")

            print(f"Project saved to {filepath}")
            self._projectFilePath = filepath
            self._isModified = False
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            import traceback
            traceback.print_exc()
            return False

    def loadProjectFile(self, filepath):
        """
        Load project from a .adproject file
        """
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                # 1. Load metadata
                if "project.xml" not in zf.namelist():
                    print("Error: Invalid project file (missing project.xml)")
                    return False
                
                xml_data = zf.read("project.xml")
                root = ET.fromstring(xml_data)
                
                self._projectName = root.find("projectName").text if root.find("projectName") is not None else "Unknown"
                self._savegamePath = root.find("savegamePath").text if root.find("savegamePath") is not None else ""
                self._mapPath = root.find("mapPath").text if root.find("mapPath") is not None else ""
                self._adConfigPath = root.find("adConfigPath").text if root.find("adConfigPath") is not None else ""
                
                # 2. Load images
                self._mapImages = {"overview": None, "heightmap": None}
                
                for img_type in ["overview", "heightmap"]:
                    filename = f"{img_type}.png"
                    if filename in zf.namelist():
                        data = zf.read(filename)
                        stream = BytesIO(data)
                        img = wx.Image(stream, wx.BITMAP_TYPE_PNG)
                        if img.IsOk():
                            self._mapImages[img_type] = img
                
                # 3. Load AutoDrive network
                self._roadNetwork = RoadNetwork()
                loaded_from = None
                
                # Check if modified version exists - it takes priority
                if "AutoDrive_config_modified.xml" in zf.namelist():
                    print("Loading MODIFIED AutoDrive network from project file...")
                    from .autodrive_parser import parse_autodrive_xml
                    with zf.open("AutoDrive_config_modified.xml") as xml_f:
                        network = parse_autodrive_xml(xml_f)
                        if network:
                            self._roadNetwork = network
                            self._hasModifiedData = True
                            loaded_from = "modified"
                            print(f"✓ Loaded {len(network.waypoints)} waypoints from MODIFIED data")
                
                # If no modified version, load original
                if not loaded_from and "AutoDrive_config.xml" in zf.namelist():
                    print("Loading original AutoDrive network from project file...")
                    from .autodrive_parser import parse_autodrive_xml
                    with zf.open("AutoDrive_config.xml") as xml_f:
                        network = parse_autodrive_xml(xml_f)
                        if network:
                            self._roadNetwork = network
                            self._hasModifiedData = False
                            loaded_from = "original"
                            print(f"✓ Loaded {len(network.waypoints)} waypoints from original data")
                
                # Fallback to original path if not in ZIP (legacy projects)
                if not loaded_from:
                    if self._adConfigPath and os.path.isfile(self._adConfigPath):
                        print(f"Loading AutoDrive network from savegame path: {self._adConfigPath}")
                        from .autodrive_parser import parse_autodrive_xml
                        network = parse_autodrive_xml(self._adConfigPath)
                        if network:
                            self._roadNetwork = network
                            self._hasModifiedData = False
                            loaded_from = "savegame"
                            print(f"✓ Loaded {len(network.waypoints)} waypoints from savegame")
                            
            print(f"Project loaded: {self._projectName}")
            self._projectFilePath = filepath
            self._isModified = False
            self._undoStack.clear()
            self._redoStack.clear()
            return True
        except Exception as e:
            print(f"Error loading project: {e}")
            return False


    # -- Getters --
    def getProjectName(self):
        return self._projectName

    def isModified(self):
        return self._isModified
    
    def setModified(self, modified=True):
        self._isModified = modified

    def isOk(self):
        """Returns True if a project is loaded and valid"""
        return self._projectName != "" and self._roadNetwork is not None
    
    def hasModifiedData(self):
        """Returns True if road network data has been modified"""
        return self._hasModifiedData

    def getSavegamePath(self):
        return self._savegamePath

    def getMapPath(self):
        return self._mapPath

    def getADConfigPath(self):
        return self._adConfigPath
    
    def getProjectFilePath(self):
        return self._projectFilePath

    def getMapImages(self):
        """Returns directory containing 'overview' and 'heightmap' images"""
        return self._mapImages

    def getOverviewImage(self):
        return self._mapImages.get("overview")

    def getHeightmapImage(self):
        return self._mapImages.get("heightmap")

    def getRoadNetwork(self):
        """Returns the AutoDrive road network"""
        return self._roadNetwork

    def getOriginalADConfigBytes(self):
        """
        Returns original AutoDrive_config.xml content as bytes.
        Priority:
          1) embedded in current .adproject (AutoDrive_config.xml)
          2) file from original _adConfigPath
        Returns None if unavailable.
        """
        # 1) Try embedded original in project archive
        if self._projectFilePath and os.path.isfile(self._projectFilePath):
            try:
                with zipfile.ZipFile(self._projectFilePath, 'r') as zf:
                    if "AutoDrive_config.xml" in zf.namelist():
                        return zf.read("AutoDrive_config.xml")
            except Exception as e:
                print(f"Warning: Failed reading embedded original AD config: {e}")

        # 2) Fallback to original source path
        if self._adConfigPath and os.path.isfile(self._adConfigPath):
            try:
                with open(self._adConfigPath, "rb") as f:
                    return f.read()
            except Exception as e:
                print(f"Warning: Failed reading original AD config from path: {e}")

        return None
    
    def remove_waypoints(self, waypoint_ids):
        """
        Remove a list of waypoints from the network.
        returns: The count of removed waypoints.
        """
        if not self._roadNetwork:
            return 0

        before = self._create_snapshot()
        removed = 0
        for wp_id in waypoint_ids:
            if self._roadNetwork.remove_waypoint(wp_id):
                removed += 1

        if removed > 0:
            self._record_undo_snapshot(before)
            self._set_network_modified()

        return removed

    def remove_routes(self, route_list):
        """
        Remove a list of routes (connections) from the network.
        Each route is a tuple (from_id, to_id).
        Returns: The count of removed routes.
        """
        if not self._roadNetwork:
            return 0

        before = self._create_snapshot()
        removed = 0
        for from_id, to_id in route_list:
            if self._roadNetwork.remove_route(from_id, to_id):
                removed += 1

        if removed > 0:
            self._record_undo_snapshot(before)
            self._set_network_modified()

        return removed
    
    def get_height_at(self, x, z):
        """
        Get the height (Y) at the given world coordinates (x, z).
        Returns the height in meters, or 0 if no heightmap is available.
        """
        heightmap = self.getHeightmapImage()
        if not heightmap or not heightmap.IsOk():
            return 0.0
            
        mapW = heightmap.GetWidth()
        mapH = heightmap.GetHeight()
        
        # World (0,0) -> Image (W/2, H/2)
        # 1 World Unit = 1 Image Pixel (assuming standard FS map)
        px = int(x + (mapW / 2.0))
        py = int(z + (mapH / 2.0))
        
        if 0 <= px < mapW and 0 <= py < mapH:
            # GetRed returns 0-255 (8-bit)
            # Standard FS maps usually map 0-255 to some height range (e.g. 0-256m or 0-400m)
            # Without map.xml config, we'll try a sensible default
            # For 8-bit heightmaps, 1 unit = 1 meter is a common assumption or scaling factor
            # Ideal would be reading 16-bit PNG but wx.Image loads as 8-bit RGB
            val = heightmap.GetRed(px, py)
            
            # Simple scaling factor (1.0)
            return float(val)
        
        return 0.0

    def create_waypoint(self, x, z):
        """
        Create a new waypoint at the given coordinates.
        Returns: The ID of the new waypoint, or None if failed.
        """
        if not self._roadNetwork:
            return None

        before = self._create_snapshot()
        # Create new waypoint
        new_id = self._roadNetwork.get_next_id()

        # Get height from heightmap
        y = self.get_height_at(x, z)

        new_wp = Waypoint(id=new_id, x=x, y=y, z=z)
        self._roadNetwork.add_waypoint(new_wp)

        self._record_undo_snapshot(before)
        self._set_network_modified()

        return new_id

    def add_marker(self, wp_id, name, group):
        """Add a new marker to the given waypoint."""
        if not self._roadNetwork:
            return False

        before = self._create_snapshot()
        # rename_marker handles creation too
        if self._roadNetwork.rename_marker(wp_id, name, group):
            self._record_undo_snapshot(before)
            self._set_network_modified()
            return True
        return False

    def edit_marker(self, wp_id, name, group):
        """Edit an existing marker."""
        return self.add_marker(wp_id, name, group)

    def remove_marker(self, wp_id):
        """Remove a marker from the given waypoint."""
        if not self._roadNetwork:
            return False

        before = self._create_snapshot()
        if self._roadNetwork.remove_marker(wp_id):
            self._record_undo_snapshot(before)
            self._set_network_modified()
            return True
        return False

    def add_route(self, from_id, to_id):
        """
        Add a route between two waypoints.
        Returns: True if the route was created, False otherwise.
        """
        if not self._roadNetwork:
            return False

        before = self._create_snapshot()
        if self._roadNetwork.add_route(from_id, to_id):
            self._record_undo_snapshot(before)
            self._set_network_modified()
            return True
        return False
    
    def create_curve(self, start_id, end_id, intermediate_points, direction_mode):
        """
        Create a curve of waypoints between start_id and end_id.
        intermediate_points: list of (x, y, z) tuples.
        direction_mode: 0=S->E, 1=E->S, 2=Dual, 3=Reverse (S->E)
        """
        if not self._roadNetwork:
            return False
            
        before = self._create_snapshot()
        
        # Create intermediate waypoints
        created_ids = []
        for p in intermediate_points:
            new_id = self._roadNetwork.get_next_id()
            new_wp = Waypoint(id=new_id, x=p[0], y=p[1], z=p[2])
            self._roadNetwork.add_waypoint(new_wp)
            created_ids.append(new_id)
            
        # Full sequence of IDs
        sequence = [start_id] + created_ids + [end_id]
        
        # Create connections
        for i in range(len(sequence) - 1):
            u = sequence[i]
            v = sequence[i+1]
            
            if direction_mode == 0: # S->E
                self._roadNetwork.add_route(u, v)
            elif direction_mode == 1: # E->S
                self._roadNetwork.add_route(v, u)
            elif direction_mode == 2: # Dual
                self._roadNetwork.add_route(u, v)
                self._roadNetwork.add_route(v, u)
            elif direction_mode == 3: # Reverse S->E
                # Create Regular first
                self._roadNetwork.add_route(u, v)
                # Then convert to Reverse (remove u from v.incoming)
                wp_v = self._roadNetwork.get_waypoint(v)
                if wp_v and u in wp_v.incoming:
                    wp_v.incoming.remove(u)

        if created_ids or len(sequence) > 2:
            self._record_undo_snapshot(before)
            self._set_network_modified()
            return True
            
        return False

    
    def swap_selected_routes(self, route_list):
        """
        Swap direction for multiple selected routes.
        If selected routes are not uniform, first uniformize each continuous
        chain so all segments follow the same traversal direction.
        
        Args:
            route_list: List of route tuples (from_id, to_id)
            
        Returns:
            List of new route tuples (from_id, to_id) that are valid after the swap.
        """
        if not self._roadNetwork:
            return []

        before = self._create_snapshot()
        # Deduplicate by undirected edge.
        unique_edges = {}
        for u, v in route_list:
            key = (min(u, v), max(u, v))
            if key not in unique_edges:
                unique_edges[key] = (u, v)

        if not unique_edges:
            return []

        # Build adjacency (undirected graph of selected routes).
        adjacency = {}
        for a, b in unique_edges.keys():
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)

        visited_nodes = set()

        def _edge_state(u, v):
            # Relative to oriented edge u->v
            if self._roadNetwork.is_dual(u, v):
                return "double"
            if self._roadNetwork.is_regular(u, v) or self._roadNetwork.is_reverse(u, v):
                return "sens1"
            if self._roadNetwork.is_regular(v, u) or self._roadNetwork.is_reverse(v, u):
                return "sens2"
            return "none"

        def _set_edge_state(u, v, target):
            # target in {"sens1","sens2","double"}, relative to u->v
            wp_u = self._roadNetwork.get_waypoint(u)
            wp_v = self._roadNetwork.get_waypoint(v)
            if not wp_u or not wp_v:
                return False

            while v in wp_u.outgoing:
                wp_u.outgoing.remove(v)
            while v in wp_u.incoming:
                wp_u.incoming.remove(v)
            while u in wp_v.outgoing:
                wp_v.outgoing.remove(u)
            while u in wp_v.incoming:
                wp_v.incoming.remove(u)

            if target in ("sens1", "double"):
                wp_u.outgoing.append(v)
                wp_v.incoming.append(u)
            if target in ("sens2", "double"):
                wp_v.outgoing.append(u)
                wp_u.incoming.append(v)
            return True

        def _get_edge_key(a, b):
            return (min(a, b), max(a, b))

        # Process each connected component independently.
        component_oriented_edges = []
        component_target_states = []

        for start in adjacency.keys():
            if start in visited_nodes:
                continue

            # Collect nodes in this component
            stack = [start]
            comp_nodes = []
            visited_nodes.add(start)
            while stack:
                n = stack.pop()
                comp_nodes.append(n)
                for nxt in adjacency.get(n, ()):
                    if nxt not in visited_nodes:
                        visited_nodes.add(nxt)
                        stack.append(nxt)

            # Build edge set for this component.
            comp_edge_keys = set()
            for node in comp_nodes:
                for nxt in adjacency.get(node, ()):
                    comp_edge_keys.add(_get_edge_key(node, nxt))

            # Preferred start: endpoint (degree 1) when possible.
            endpoints = [n for n in comp_nodes if len(adjacency.get(n, ())) == 1]
            if endpoints:
                path_start = min(endpoints)
            else:
                path_start = min(comp_nodes)

            # Traverse all edges once; orientation follows traversal direction.
            oriented_edges = []
            used_edges = set()
            node_stack = [path_start]
            while node_stack:
                node = node_stack.pop()
                for nxt in sorted(adjacency.get(node, ())):
                    ek = _get_edge_key(node, nxt)
                    if ek in used_edges:
                        continue
                    if ek not in comp_edge_keys:
                        continue
                    used_edges.add(ek)
                    oriented_edges.append((node, nxt))
                    node_stack.append(nxt)

            # Safety: component might have disconnected traversal leftovers in rare graph shapes.
            if len(used_edges) < len(comp_edge_keys):
                for a, b in sorted(comp_edge_keys):
                    if (a, b) in used_edges:
                        continue
                    oriented_edges.append((a, b))

            states = [_edge_state(u, v) for (u, v) in oriented_edges if _edge_state(u, v) != "none"]
            if not states:
                continue

            unique_states = set(states)
            if len(unique_states) > 1:
                target_state = "sens1"  # Uniformize this component only.
            else:
                cur = states[0]
                if cur == "sens1":
                    target_state = "sens2"
                elif cur == "sens2":
                    target_state = "double"
                else:  # double
                    target_state = "sens1"

            component_oriented_edges.append(oriented_edges)
            component_target_states.append(target_state)

        if not component_oriented_edges:
            return []

        new_selection = []
        modified = False
        for oriented_edges, target_state in zip(component_oriented_edges, component_target_states):
            for u, v in oriented_edges:
                if _set_edge_state(u, v, target_state):
                    modified = True
                    if target_state == "sens2":
                        # Keep UI selection aligned with actual visible direction.
                        new_selection.append((v, u))
                    else:
                        new_selection.append((u, v))
        
        if modified:
            self._record_undo_snapshot(before)
            self._set_network_modified()

        return new_selection

    def toggle_reverse_routes(self, route_list):
        """
        Toggle the "marche arriere" (reverse driving) state for a list of route segments.

        For each segment (from_id -> to_id):
          - If currently REGULAR  (from_wp.outgoing has to_id AND to_wp.incoming has from_id):
              -> becomes REVERSE by removing from_id from to_wp.incoming.
          - If currently REVERSE  (from_wp.outgoing has to_id AND to_wp.incoming does NOT have from_id):
              -> becomes REGULAR again by adding from_id back to to_wp.incoming.
          - If currently DUAL: left untouched (n/a for marche arriere).

        Returns:
            List of route tuples (from_id, to_id) that were actually modified.
        """
        if not self._roadNetwork:
            return []

        before = self._create_snapshot()
        modified_routes = []

        for from_id, to_id in route_list:
            from_wp = self._roadNetwork.get_waypoint(from_id)
            to_wp   = self._roadNetwork.get_waypoint(to_id)
            if not from_wp or not to_wp:
                continue
            # Only act on segments where from_id->to_id exists as an outgoing link
            if to_id not in from_wp.outgoing:
                continue
            # Skip dual segments
            if self._roadNetwork.is_dual(from_id, to_id):
                continue

            if self._roadNetwork.is_regular(from_id, to_id):
                # Regular -> Reverse (marche arriere): remove the incoming link
                if from_id in to_wp.incoming:
                    to_wp.incoming.remove(from_id)
                modified_routes.append((from_id, to_id))
            elif self._roadNetwork.is_reverse(from_id, to_id):
                # Reverse -> Regular: restore the incoming link
                if from_id not in to_wp.incoming:
                    to_wp.incoming.append(from_id)
                modified_routes.append((from_id, to_id))

        if modified_routes:
            self._record_undo_snapshot(before)
            self._set_network_modified()

        return modified_routes

    # -- Setters --
    def setProjectName(self, name):
        if self._projectName != name:
            before = self._create_snapshot()
            self._projectName = name
            self._isModified = True
            self._record_undo_snapshot(before)

    def setSavegamePath(self, path):
        if self._savegamePath != path:
            before = self._create_snapshot()
            self._savegamePath = path
            self._isModified = True
            self._record_undo_snapshot(before)

    def setMapPath(self, path):
        if self._mapPath != path:
            before = self._create_snapshot()
            self._mapPath = path
            self._isModified = True
            self._record_undo_snapshot(before)

    def setADConfigPath(self, path):
        if self._adConfigPath != path:
            before = self._create_snapshot()
            self._adConfigPath = path
            self._isModified = True
            # Auto-parse the AutoDrive config when path is set
            if path and os.path.isfile(path):
                from .autodrive_parser import parse_autodrive_xml
                network = parse_autodrive_xml(path)
                if network:
                    self._roadNetwork = network
                    self._hasModifiedData = False  # Fresh load from savegame
                    print(f"Loaded {len(network.waypoints)} waypoints from AutoDrive config")
            self._record_undo_snapshot(before)

    def setMapImages(self, images_dict):
        """
        Set the map images dictionary.
        Expected keys: 'overview', 'heightmap' (wx.Image or wx.Bitmap)
        """
        if isinstance(images_dict, dict):
            before = self._create_snapshot()
            self._mapImages.update(images_dict)
            self._isModified = True
            self._record_undo_snapshot(before)
            
    def setOverviewImage(self, image):
        before = self._create_snapshot()
        self._mapImages["overview"] = image
        self._isModified = True
        self._record_undo_snapshot(before)
        
    def setHeightmapImage(self, image):
        before = self._create_snapshot()
        self._mapImages["heightmap"] = image
        self._isModified = True
        self._record_undo_snapshot(before)
