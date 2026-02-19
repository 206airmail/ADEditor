import wx
from Core import DatasManager

_ = wx.GetTranslation

class MapCanvas(wx.Panel):
    """
    Custom panel for displaying the map and the AutoDrive waypoints.
    Supports zoom (mouse wheel, +/-, Ctrl+RMB vertical) and pan (RMB drag).
    """
    
    # Zoom constraints
    ZOOM_MIN = 0.1
    ZOOM_MAX = 30.0
    ZOOM_STEP = 1.1  # Multiplicative factor for zoom
    PAN_MARGIN = 100  # Pixels of empty space allowed when panning
    
    def __init__(self, parent, datas_manager=None):
        super().__init__(parent)
        
        if datas_manager:
            self._datasMngr = datas_manager
        else:
            self._datasMngr = DatasManager()
        
        # View state
        self._zoom = 1.0
        self._panX = 0  # Pan offset in pixels
        self._panY = 0
        
        # Cached bitmap for rendering
        self._mapBitmap = None
        
        # Mouse interaction state
        self._lastMousePos = None
        self._isRightDragging = False
        self._isLeftDragging = False
        self._isShiftLeftDragging = False  # For Shift+drag to select routes
        self._dragStartPos = None
        self._currentDragPos = None
        self._selected_waypoints = set()
        self._selected_routes = set()  # Store selected routes as (from_id, to_id) tuples
        
        # Waypoint dragging state
        self._isDraggingWaypoint = False
        self._draggedWaypointId = None
        self._draggedWaypointOriginalPos = None
        self._draggedWaypointStartSnapshot = None
        
        # Route dragging state
        self._isDraggingRoute = False
        self._draggedRouteWaypoints = None  # Tuple of (from_id, to_id)
        self._draggedRouteOriginalPositions = None  # Dict {wp_id: (x, z)}
        self._dragRouteOffset = None  # (dx, dz) offset from click to route midpoint
        self._draggedRouteStartSnapshot = None
        
        # Path selection state
        self._lastSelectedWaypoint = None  # For Shift+click path selection
        self._lastSelectedRoute = None  # For Shift+click route path selection
        
        # Setup
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetBackgroundColour(wx.Colour(40, 40, 45))  # Dark background
        
        # Bind events
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        
        # Allow key events
        self.SetFocus()
        
        # Tool modes
        self._toolMode = 'default'  # 'default', 'zoom_window'
        self._isZoomWindowDragging = False

    def RefreshMapData(self):
        """Refresh the map data from DatasManager and update the display."""
        self._updateMapBitmap()
        self.Refresh()

    def _updateMapBitmap(self):
        """Update the cached map bitmap from DatasManager."""
        overview = self._datasMngr.getOverviewImage()
        if overview and overview.IsOk():
            self._mapBitmap = wx.Bitmap(overview)
        else:
            self._mapBitmap = None

    def ResetView(self):
        """Reset zoom and pan to default values."""
        self._zoom = 1.0
        self._panX = 0
        self._panY = 0
        self.Refresh()

    def FitToWindow(self):
        """Adjust zoom and pan to fit the map in the window."""
        if not self._mapBitmap:
            return
        
        canvasW, canvasH = self.GetClientSize()
        mapW = self._mapBitmap.GetWidth()
        mapH = self._mapBitmap.GetHeight()
        
        if mapW > 0 and mapH > 0:
            zoomX = canvasW / mapW
            zoomY = canvasH / mapH
            self._zoom = min(zoomX, zoomY) * 0.95  # 95% to leave some margin
            self._zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self._zoom))
            
            # Center the map
            self._panX = (canvasW - mapW * self._zoom) / 2
            self._panY = (canvasH - mapH * self._zoom) / 2
            
            self.Refresh()
    
    def GetSelectedWaypoints(self):
        """Return the set of selected waypoint IDs."""
        return self._selected_waypoints.copy()
    
    def GetSelectedRoutes(self):
        """Return the set of selected routes as (from_id, to_id) tuples."""
        return self._selected_routes.copy()

    def ClearSelection(self):
        """Clear all selected waypoints and routes."""
        self._selected_waypoints.clear()
        self._selected_routes.clear()
        
    def SelectRoute(self, route_tuple, add=False):
        """
        Select a specific route.
        
        Args:
            route_tuple: Tuple (from_id, to_id)
            add: If True, add to existing selection. If False, clear others.
        """
        if not add:
            self.ClearSelection()
        self._selected_routes.add(route_tuple)
        
    def ZoomIn(self):
        """Zoom in relative to center of view."""
        cx, cy = self._getCanvasCenter()
        self._zoomAt(cx, cy, self.ZOOM_STEP)
        
    def ZoomOut(self):
        """Zoom out relative to center of view."""
        cx, cy = self._getCanvasCenter()
        self._zoomAt(cx, cy, 1.0 / self.ZOOM_STEP)
        
    def SetZoomWindowMode(self, active=True):
        """Enable or disable zoom window mode."""
        if active:
            self._toolMode = 'zoom_window'
            self.SetCursor(wx.Cursor(wx.CURSOR_MAGNIFIER))
        else:
            self._toolMode = 'default'
            self._isZoomWindowDragging = False
            self.SetCursor(wx.NullCursor)
            self.Refresh()
    
    def GetSelectionInfo(self):
        """
        Get detailed information about the current selection.
        
        Returns:
            dict: Dictionary with keys:
                - 'total': Total number of selected elements
                - 'waypoints': Number of selected waypoints
                - 'routes': Number of selected routes
                - 'markers': Number of selected markers (currently 0, for future use)
                - 'types': List of types that have selections (e.g., ['Waypoints', 'Routes'])
        """
        waypoints_count = len(self._selected_waypoints)
        routes_count = len(self._selected_routes)
        
        # Count markers: selected waypoints that have an associated marker label
        markers_count = 0
        network = self._datasMngr.getRoadNetwork()
        if network:
            for wp_id in self._selected_waypoints:
                if network.get_marker_for_waypoint(wp_id):
                    markers_count += 1
        
        types = []
        if waypoints_count > 0:
            types.append('Waypoints')
        if routes_count > 0:
            types.append('Routes')
        if markers_count > 0:
            types.append('Markers')
        
        return {
            'total': waypoints_count + routes_count,
            'waypoints': waypoints_count,
            'routes': routes_count,
            'markers': markers_count,
            'types': types
        }
    
    def GetSelectionCount(self):
        """
        Get the total number of selected elements.
        
        Returns:
            int: Total count of all selected elements (waypoints + routes + markers)
        """
        return len(self._selected_waypoints) + len(self._selected_routes)
    
    def GetSelectionTypes(self):
        """
        Get the list of element types that have selections.
        
        Returns:
            list: List of strings representing types with selections.
                  Possible values: 'Waypoints', 'Routes', 'Markers'
        """
        types = []
        if len(self._selected_waypoints) > 0:
            types.append('Waypoints')
        if len(self._selected_routes) > 0:
            types.append('Routes')
        # Check if any selected waypoint is a marker
        network = self._datasMngr.getRoadNetwork()
        if network:
            for wp_id in self._selected_waypoints:
                if network.get_marker_for_waypoint(wp_id):
                    types.append('Markers')
                    break
        return types

    # --- Event Handlers ---

    def OnPaint(self, event):
        """Handle paint events for the canvas."""
        dc = wx.AutoBufferedPaintDC(self)
        self._draw_background(dc)
        self._draw_map(dc)
        self._draw_waypoints(dc)
        self._draw_selection_rect(dc)
        self._draw_zoom_window_rect(dc)
        self._update_selection_status()

    def OnSize(self, event):
        """Handle resize events."""
        self.Refresh()
        event.Skip()

    def OnMouseWheel(self, event):
        """Handle mouse wheel for zooming."""
        rotation = event.GetWheelRotation()
        mouseX, mouseY = event.GetPosition()
        
        # Calculate zoom factor
        if rotation > 0:
            factor = self.ZOOM_STEP
        else:
            factor = 1.0 / self.ZOOM_STEP
        
        self._zoomAt(mouseX, mouseY, factor)
        event.Skip()

    def OnRightDown(self, event):
        """Handle right mouse button down for pan/zoom."""
        self._lastMousePos = event.GetPosition()
        self._isRightDragging = True
        self.CaptureMouse()
        event.Skip()

    def OnRightUp(self, event):
        """Handle right mouse button up."""
        self._isRightDragging = False
        self._lastMousePos = None
        if self.HasCapture():
            self.ReleaseMouse()
        event.Skip()

    def OnMouseMotion(self, event):
        """Handle mouse motion for pan and Ctrl+RMB zoom."""
        currentPos = event.GetPosition()
        
        # Update coordinates and zoom in Status Bar
        self._update_status_bar(currentPos.x, currentPos.y)
        
        # Handle waypoint dragging
        if self._isDraggingWaypoint and self._draggedWaypointId is not None:
            network = self._datasMngr.getRoadNetwork()
            if network:
                wp = network.get_waypoint(self._draggedWaypointId)
                if wp:
                    # Convert screen position to world coordinates
                    wx, wz = self.screen_to_world(currentPos.x, currentPos.y)
                    # Update waypoint position
                    wp.x = wx
                    wp.z = wz
                    # Update altitude from heightmap
                    wp.y = self._datasMngr.get_height_at(wx, wz)
                    self.Refresh()
            event.Skip()
            return
        
        # Handle route dragging
        if self._isDraggingRoute and self._draggedRouteWaypoints is not None:
            network = self._datasMngr.getRoadNetwork()
            if network:
                from_id, to_id = self._draggedRouteWaypoints
                from_wp = network.get_waypoint(from_id)
                to_wp = network.get_waypoint(to_id)
                
                if from_wp and to_wp:
                    # Convert screen position to world coordinates
                    click_wx, click_wz = self.screen_to_world(currentPos.x, currentPos.y)
                    
                    # Apply the offset to get the route midpoint position
                    mid_x = click_wx + self._dragRouteOffset[0]
                    mid_z = click_wz + self._dragRouteOffset[1]
                    
                    # Calculate original distance between waypoints
                    orig_from = self._draggedRouteOriginalPositions[from_id]
                    orig_to = self._draggedRouteOriginalPositions[to_id]
                    orig_mid_x = (orig_from[0] + orig_to[0]) / 2
                    orig_mid_z = (orig_from[1] + orig_to[1]) / 2
                    
                    # Calculate offset from original midpoint
                    dx = mid_x - orig_mid_x
                    dz = mid_z - orig_mid_z
                    
                    # Move both waypoints by the same offset
                    from_wp.x = orig_from[0] + dx
                    from_wp.z = orig_from[1] + dz
                    from_wp.y = self._datasMngr.get_height_at(from_wp.x, from_wp.z)
                    
                    to_wp.x = orig_to[0] + dx
                    to_wp.z = orig_to[1] + dz
                    to_wp.y = self._datasMngr.get_height_at(to_wp.x, to_wp.z)
                    
                    self.Refresh()
            event.Skip()
            return
        
        # Handle left drag selection update
        if self._isZoomWindowDragging:
            self._currentDragPos = currentPos
            self.Refresh()
            event.Skip()
            return
            
        if (self._isLeftDragging or self._isShiftLeftDragging) and self._dragStartPos:
            self._currentDragPos = currentPos
            self.Refresh()
        
        if not self._isRightDragging or self._lastMousePos is None:
            event.Skip()
            return
        
        dx = currentPos.x - self._lastMousePos.x
        dy = currentPos.y - self._lastMousePos.y
        
        if event.ControlDown():
            # Ctrl + RMB vertical movement = zoom
            # Moving up = zoom in, moving down = zoom out
            if dy != 0:
                factor = 1.0 + (-dy * 0.005)  # Sensitivity adjustment
                factor = max(0.5, min(2.0, factor))  # Clamp factor
                centerX, centerY = self.GetClientSize()
                self._zoomAt(centerX // 2, centerY // 2, factor)
                # Note: _zoomAt will update status bar too if mouse is there
        else:
            # RMB drag = pan
            self._panX += dx
            self._panY += dy
            self._clampPan()
            self.Refresh()
        
        self._lastMousePos = currentPos
        event.Skip()

    def world_to_screen(self, wx, wz):
        """Convert world coordinates to screen coordinates."""
        if not self._mapBitmap:
            return 0, 0
            
        mapW = self._mapBitmap.GetWidth()
        mapH = self._mapBitmap.GetHeight()
        
        # World centered on image center
        # World (0,0) -> Image (W/2, H/2)
        px = wx + (mapW / 2.0)
        pz = wz + (mapH / 2.0)
        
        sx = px * self._zoom + self._panX
        sy = pz * self._zoom + self._panY
        return int(sx), int(sy)

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        if not self._mapBitmap:
            return 0.0, 0.0
            
        mapW = self._mapBitmap.GetWidth()
        mapH = self._mapBitmap.GetHeight()
        
        # Reverse zoom/pan
        px = (sx - self._panX) / self._zoom
        pz = (sy - self._panY) / self._zoom
        
        # Reverse center offset
        wx = px - (mapW / 2.0)
        wz = pz - (mapH / 2.0)
        return wx, wz

    def _update_status_bar(self, screen_x, screen_y):
        """Update the status bar with world coordinates and zoom level."""
        if self._mapBitmap:
            wx_c, wz_c = self.screen_to_world(screen_x, screen_y)
            parent = self.GetParent()
            while parent:
                if isinstance(parent, wx.Frame) or hasattr(parent, 'SetStatusText'):
                    try:
                        # Status bar field 1 (second field)
                        h = self._datasMngr.get_height_at(wx_c, wz_c)
                        text = f"X: {wx_c:.1f} Y: {wz_c:.1f} Z: {h:.1f}  Zoom: {self._zoom:.2f}x"
                        parent.SetStatusText(text, 1)
                        break
                    except:
                        pass
                parent = parent.GetParent()

    def _update_selection_status(self):
        """Update the status bar (field 2) with selection information."""
        parent = self.GetParent()
        while parent:
            if isinstance(parent, wx.Frame) or hasattr(parent, 'SetStatusText'):
                try:
                    info = self.GetSelectionInfo()
                    if info['total'] == 0:
                        parent.SetStatusText("", 2)
                    else:
                        parts = []
                        if info['waypoints'] > 0:
                            parts.append(f"{info['waypoints']} Wp")
                        if info['routes'] > 0:
                            parts.append(f"{info['routes']} Rt")
                        if info['markers'] > 0:
                            parts.append(f"{info['markers']} Mk")
                        text = f"Sel: {info['total']} ({', '.join(parts)})"
                        parent.SetStatusText(text, 2)
                    break
                except:
                    pass
            parent = parent.GetParent()

    def OnKeyDown(self, event):
        """Handle keyboard shortcuts for zoom."""
        keyCode = event.GetKeyCode()
        
        if keyCode in (ord('+'), wx.WXK_NUMPAD_ADD):
            self._zoomAt(*self._getCanvasCenter(), self.ZOOM_STEP)
        elif keyCode in (ord('-'), wx.WXK_NUMPAD_SUBTRACT):
            self._zoomAt(*self._getCanvasCenter(), 1.0 / self.ZOOM_STEP)
        elif keyCode == ord('0'):
            self.FitToWindow()
        elif keyCode == ord('1'):
            self.ResetView()
        elif keyCode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            # Delete selected items (waypoints and/or routes)
            parent = self.GetParent()
            if hasattr(parent, 'OnDeleteSelection'):
                parent.OnDeleteSelection(event)
        else:
            event.Skip()

    # --- Drawing Methods ---

    def _draw_background(self, dc):
        """Draw the background of the canvas."""
        width, height = self.GetClientSize()
        dc.SetBrush(wx.Brush(self.GetBackgroundColour()))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, width, height)

    def _draw_map(self, dc):
        """Draw the map on the canvas with current zoom and pan."""
        if not self._mapBitmap:
            # Try to load from DatasManager
            self._updateMapBitmap()
        
        if not self._mapBitmap:
            # No map available, draw placeholder text
            dc.SetTextForeground(wx.Colour(100, 100, 100))
            dc.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
            w, h = self.GetClientSize()
            text = _("No map loaded")
            tw, th = dc.GetTextExtent(text)
            dc.DrawText(text, (w - tw) // 2, (h - th) // 2)
            return
        
        # Get visible area
        canvasW, canvasH = self.GetClientSize()
        mapW = self._mapBitmap.GetWidth()
        mapH = self._mapBitmap.GetHeight()
        scaledW = int(mapW * self._zoom)
        scaledH = int(mapH * self._zoom)
        
        if scaledW <= 0 or scaledH <= 0:
            return
        
        # Calculate visible portion of the map (in source coordinates)
        srcX = max(0, int(-self._panX / self._zoom))
        srcY = max(0, int(-self._panY / self._zoom))
        srcW = min(mapW - srcX, int(canvasW / self._zoom) + 2)
        srcH = min(mapH - srcY, int(canvasH / self._zoom) + 2)
        
        if srcW <= 0 or srcH <= 0:
            return
        
        # Extract only the visible portion
        visibleRect = wx.Rect(srcX, srcY, srcW, srcH)
        subImg = self._mapBitmap.ConvertToImage().GetSubImage(visibleRect)
        
        # Scale the visible portion
        dstW = int(srcW * self._zoom)
        dstH = int(srcH * self._zoom)
        if dstW > 0 and dstH > 0:
            scaledImg = subImg.Scale(dstW, dstH, wx.IMAGE_QUALITY_NEAREST)
            scaledBmp = wx.Bitmap(scaledImg)
            
            # Calculate draw position
            drawX = int(self._panX + srcX * self._zoom)
            drawY = int(self._panY + srcY * self._zoom)
            
            dc.DrawBitmap(scaledBmp, drawX, drawY, True)

    def _draw_waypoints(self, dc):
        """Draw the AutoDrive waypoints and connections on the canvas."""
        network = self._datasMngr.getRoadNetwork()
        if not network or not network.waypoints:
            # print("No network or waypoints")
            return
        
        if not self._mapBitmap:
            # print("No map bitmap")
            return
        
        # Colors for connection types
        COLOR_REGULAR = wx.Colour(0, 255, 0)        # Green - unidirectional
        COLOR_DUAL = wx.Colour(0, 0, 139)           # Dark Blue - bidirectional
        COLOR_REVERSE = wx.Colour(135, 206, 235)    # Sky Blue - reverse
        COLOR_WAYPOINT = wx.Colour(255, 255, 0)     # Yellow - waypoint dot
        COLOR_SELECTED = wx.Colour(255, 0, 0)       # Red - selected
        
        # Map coordinate system: FS world coords -> image pixel coords -> screen coords
        # Standard FS25 maps are 2048x2048 image representing the game world
        # World coords: typically -1024 to +1024 or 0 to 2048 depending on map

        
        # Get visible screen bounds for culling
        
        # Get visible screen bounds for culling
        canvasW, canvasH = self.GetClientSize()
        
        # Track drawn bidirectional connections to avoid duplicates
        drawn_dual = set()
        
        # Draw connections first (under waypoints)
        # Fixed line width
        lineWidth = 3
        
        for wp in network.waypoints.values():
            sx1, sy1 = self.world_to_screen(wp.x, wp.z)
            
            for out_id in wp.outgoing:
                out_wp = network.get_waypoint(out_id)
                if not out_wp:
                    continue
                
                sx2, sy2 = self.world_to_screen(out_wp.x, out_wp.z)
                
                # Skip if both points are off-screen
                if (sx1 < -50 and sx2 < -50) or (sx1 > canvasW + 50 and sx2 > canvasW + 50):
                    continue
                if (sy1 < -50 and sy2 < -50) or (sy1 > canvasH + 50 and sy2 > canvasH + 50):
                    continue
                
                # Determine connection type and color
                if network.is_dual(wp.id, out_id):
                    # Skip if already drawn from the other direction
                    pair = (min(wp.id, out_id), max(wp.id, out_id))
                    if pair in drawn_dual:
                        continue
                    drawn_dual.add(pair)
                    dc.SetPen(wx.Pen(COLOR_DUAL, lineWidth))
                elif network.is_reverse(wp.id, out_id):
                    dc.SetPen(wx.Pen(COLOR_REVERSE, lineWidth))
                else:
                    # Regular unidirectional connection
                    dc.SetPen(wx.Pen(COLOR_REGULAR, lineWidth))
                
                dc.DrawLine(sx1, sy1, sx2, sy2)
                
                # Draw arrow for unidirectional connections (Regular and Reverse/marche arriere)
                if not network.is_dual(wp.id, out_id):
                    import math
                    # Calculate midpoint
                    mid_x = (sx1 + sx2) / 2
                    mid_y = (sy1 + sy2) / 2
                    
                    # Calculate direction angle
                    # For reverse (marche arriere) segments, invert the arrow to show
                    # the vehicle physically moves backward along the segment direction.
                    angle = math.atan2(sy2 - sy1, sx2 - sx1)
                    if network.is_reverse(wp.id, out_id):
                        angle += math.pi
                    arrow_len = 10
                    arrow_angle = math.pi / 6  # 30 degrees
                    
                    # Arrowhead points
                    ax1 = mid_x - arrow_len * math.cos(angle - arrow_angle)
                    ay1 = mid_y - arrow_len * math.sin(angle - arrow_angle)
                    ax2 = mid_x - arrow_len * math.cos(angle + arrow_angle)
                    ay2 = mid_y - arrow_len * math.sin(angle + arrow_angle)
                    
                    dc.DrawLine(int(mid_x), int(mid_y), int(ax1), int(ay1))
                    dc.DrawLine(int(mid_x), int(mid_y), int(ax2), int(ay2))
        
        # Draw selected routes on top with highlighting
        if self._selected_routes:
            import math
            COLOR_SELECTED_ROUTE = wx.Colour(255, 140, 0)  # Orange - selected route
            selectedLineWidth = 5
            
            for route in self._selected_routes:
                from_id, to_id = route
                from_wp = network.get_waypoint(from_id)
                to_wp = network.get_waypoint(to_id)
                
                if not from_wp or not to_wp:
                    continue
                
                sx1, sy1 = self.world_to_screen(from_wp.x, from_wp.z)
                sx2, sy2 = self.world_to_screen(to_wp.x, to_wp.z)
                
                # Skip if both points are off-screen
                if (sx1 < -50 and sx2 < -50) or (sx1 > canvasW + 50 and sx2 > canvasW + 50):
                    continue
                if (sy1 < -50 and sy2 < -50) or (sy1 > canvasH + 50 and sy2 > canvasH + 50):
                    continue
                
                # Draw selected route with thicker line
                dc.SetPen(wx.Pen(COLOR_SELECTED_ROUTE, selectedLineWidth))
                dc.DrawLine(sx1, sy1, sx2, sy2)
                
                # Draw arrow for unidirectional connections (Regular and Reverse/marche arriere)
                if not network.is_dual(from_id, to_id):
                    # Calculate midpoint
                    mid_x = (sx1 + sx2) / 2
                    mid_y = (sy1 + sy2) / 2
                    
                    # Calculate direction angle
                    # For reverse (marche arriere) segments, invert the arrow.
                    angle = math.atan2(sy2 - sy1, sx2 - sx1)
                    if network.is_reverse(from_id, to_id):
                        angle += math.pi
                    arrow_len = 12  # Slightly larger for selected
                    arrow_angle = math.pi / 6  # 30 degrees
                    
                    # Arrowhead points
                    ax1 = mid_x - arrow_len * math.cos(angle - arrow_angle)
                    ay1 = mid_y - arrow_len * math.sin(angle - arrow_angle)
                    ax2 = mid_x - arrow_len * math.cos(angle + arrow_angle)
                    ay2 = mid_y - arrow_len * math.sin(angle + arrow_angle)
                    
                    dc.DrawLine(int(mid_x), int(mid_y), int(ax1), int(ay1))
                    dc.DrawLine(int(mid_x), int(mid_y), int(ax2), int(ay2))

        
        # Draw waypoint nodes on top
        # Fixed size radius regardless of zoom level
        node_radius = 5  
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0), 1))  # Black outline
        
        for wp in network.waypoints.values():
            sx, sy = self.world_to_screen(wp.x, wp.z)
            
            # Skip if off-screen
            if sx < -node_radius or sx > canvasW + node_radius:
                continue
            if sy < -node_radius or sy > canvasH + node_radius:
                continue
            
            # Highlight selected
            if wp.id in self._selected_waypoints:
                dc.SetBrush(wx.Brush(COLOR_SELECTED))
            else:
                dc.SetBrush(wx.Brush(COLOR_WAYPOINT))
            
            dc.DrawCircle(sx, sy, node_radius)
            
        # Draw markers on top of everything
        if network.markers:
            # Font for markers (fixed size 10)
            font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            dc.SetFont(font)
            
            for marker in network.markers:
                wp = network.get_waypoint(marker.waypoint_id)
                if wp:
                    sx, sy = self.world_to_screen(wp.x, wp.z)
                    
                    # Skip if off-screen
                    if sx < -50 or sx > canvasW + 50 or sy < -50 or sy > canvasH + 50:
                        continue
                    
                    label = marker.name
                    # Draw text offset from point
                    tx = sx + 8
                    ty = sy - 8
                    
                    # Use red text for selected markers, white for normal
                    if marker.waypoint_id in self._selected_waypoints:
                        # Selected: dark red shadow + red text
                        dc.SetTextForeground(wx.Colour(139, 0, 0))
                        dc.DrawText(label, tx+1, ty+1)
                        dc.SetTextForeground(wx.Colour(255, 0, 0))
                        dc.DrawText(label, tx, ty)
                    else:
                        # Normal: black shadow + white text
                        dc.SetTextForeground(wx.Colour(0, 0, 0))
                        dc.DrawText(label, tx+1, ty+1)
                        dc.SetTextForeground(wx.Colour(255, 255, 255))
                        dc.DrawText(label, tx, ty)

    # --- Helper Methods ---

    def _zoomAt(self, mouseX, mouseY, factor):
        """Zoom in/out centered on (mouseX, mouseY)."""
        oldZoom = self._zoom
        newZoom = oldZoom * factor
        newZoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, newZoom))
        
        if newZoom == oldZoom:
            return
        
        # Adjust pan so the point under cursor stays in place
        self._panX = mouseX - (mouseX - self._panX) * (newZoom / oldZoom)
        self._panY = mouseY - (mouseY - self._panY) * (newZoom / oldZoom)
        self._zoom = newZoom
        
        self._clampPan()
        self.Refresh()
        
        # Update status bar immediately
        self._update_status_bar(mouseX, mouseY)

    def _clampPan(self):
        """Limit pan so the empty margin around the map is at most PAN_MARGIN pixels."""
        if not self._mapBitmap:
            return
        
        canvasW, canvasH = self.GetClientSize()
        scaledW = int(self._mapBitmap.GetWidth() * self._zoom)
        scaledH = int(self._mapBitmap.GetHeight() * self._zoom)
        
        # Max empty space on left = PAN_MARGIN -> panX <= PAN_MARGIN
        # Max empty space on right = PAN_MARGIN -> panX >= canvasW - scaledW - PAN_MARGIN
        maxPanX = self.PAN_MARGIN
        minPanX = canvasW - scaledW - self.PAN_MARGIN
        
        maxPanY = self.PAN_MARGIN
        minPanY = canvasH - scaledH - self.PAN_MARGIN
        
        # If map is smaller than canvas, center it instead
        if scaledW < canvasW - 2 * self.PAN_MARGIN:
            self._panX = (canvasW - scaledW) / 2
        else:
            self._panX = max(minPanX, min(maxPanX, self._panX))
        
        if scaledH < canvasH - 2 * self.PAN_MARGIN:
            self._panY = (canvasH - scaledH) / 2
        else:
            self._panY = max(minPanY, min(maxPanY, self._panY))

    def _getCanvasCenter(self):
        """Return the center point of the canvas."""
        w, h = self.GetClientSize()
        return w // 2, h // 2
    
    def _find_path_between_waypoints(self, start_id, end_id):
        """
        Find the shortest path between two waypoints using BFS.
        
        Args:
            start_id: Starting waypoint ID
            end_id: Ending waypoint ID
            
        Returns:
            List of waypoint IDs representing the path from start to end,
            or None if no path exists.
        """
        network = self._datasMngr.getRoadNetwork()
        if not network:
            return None
        
        # Check if both waypoints exist
        if not network.get_waypoint(start_id) or not network.get_waypoint(end_id):
            return None
        
        if start_id == end_id:
            return [start_id]
        
        # BFS to find shortest path
        from collections import deque
        
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
        
        while queue:
            current_id, path = queue.popleft()
            current_wp = network.get_waypoint(current_id)
            
            if not current_wp:
                continue
            
            # Check all outgoing connections
            for next_id in current_wp.outgoing:
                if next_id == end_id:
                    # Found the target
                    return path + [next_id]
                
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))
        
        # No path found
        return None
    
    def _find_route_path_between_routes(self, start_route, end_route):
        """
        Find the shortest path between two routes using BFS.
        Routes are connected if they share a common waypoint.
        
        Args:
            start_route: Starting route tuple (from_id, to_id)
            end_route: Ending route tuple (from_id, to_id)
            
        Returns:
            List of route tuples representing the path from start to end,
            or None if no path exists.
        """
        network = self._datasMngr.getRoadNetwork()
        if not network:
            return None
        
        if start_route == end_route:
            return [start_route]
        
        # BFS to find shortest route path
        from collections import deque
        
        queue = deque([(start_route, [start_route])])
        visited = {start_route}
        
        while queue:
            current_route, path = queue.popleft()
            from_id, to_id = current_route
            
            # Find all routes that share a waypoint with current route
            # A route shares a waypoint if its from_id or to_id matches
            # the current route's from_id or to_id
            connected_routes = set()
            
            for wp_id in [from_id, to_id]:
                wp = network.get_waypoint(wp_id)
                if not wp:
                    continue
                
                # Add all outgoing routes from this waypoint
                for out_id in wp.outgoing:
                    connected_routes.add((wp_id, out_id))
                
                # Add all incoming routes to this waypoint
                for other_wp in network.waypoints.values():
                    if wp_id in other_wp.outgoing:
                        connected_routes.add((other_wp.id, wp_id))
            
            # Check each connected route
            for next_route in connected_routes:
                if next_route == end_route:
                    # Found the target
                    return path + [next_route]
                
                if next_route not in visited:
                    visited.add(next_route)
                    queue.append((next_route, path + [next_route]))
        
        # No path found
        return None

    def OnLeftDown(self, event):
        """Handle left click for selection start."""
        self.SetFocus()
        currentPos = event.GetPosition()
        
        # Handle Zoom Window Mode
        if self._toolMode == 'zoom_window':
            self._isZoomWindowDragging = True
            self._dragStartPos = currentPos
            self._currentDragPos = currentPos
            self.CaptureMouse()
            return
        
        # Check if clicking on a waypoint to drag it
        wp_id = self._hit_test(currentPos)
        if wp_id is not None:
            # Handle Shift+click for path selection
            if event.ShiftDown() and self._lastSelectedWaypoint is not None:
                # Find path between last selected and current waypoint
                path = self._find_path_between_waypoints(self._lastSelectedWaypoint, wp_id)
                if path:
                    # Select all waypoints in the path
                    if not event.ControlDown():
                        # Clear routes selection but keep waypoint selection
                        self._selected_routes.clear()
                    
                    for waypoint_id in path:
                        self._selected_waypoints.add(waypoint_id)
                    
                    self._lastSelectedWaypoint = wp_id
                    self.Refresh()
                    event.Skip()
                    return
            
            # Select the waypoint if not already selected (unless Ctrl is held)
            if not event.ControlDown():
                # Clear selection and select only this waypoint
                self._selected_waypoints.clear()
                self._selected_routes.clear()
                self._selected_waypoints.add(wp_id)
            else:
                # Ctrl is held
                if wp_id in self._selected_waypoints:
                    # Toggle off: remove from selection and don't drag
                    self._selected_waypoints.remove(wp_id)
                    self.Refresh()
                    event.Skip()
                    return
                else:
                    # Add to selection
                    self._selected_waypoints.add(wp_id)
            
            # Update last selected waypoint for Shift+click
            self._lastSelectedWaypoint = wp_id
            
            # Start dragging the waypoint
            network = self._datasMngr.getRoadNetwork()
            if network:
                wp = network.get_waypoint(wp_id)
                if wp:
                    self._isDraggingWaypoint = True
                    self._draggedWaypointId = wp_id
                    self._draggedWaypointOriginalPos = (wp.x, wp.z)
                    self._draggedWaypointStartSnapshot = self._datasMngr.capture_snapshot()
                    if not self.HasCapture():
                        self.CaptureMouse()
                    self.Refresh()  # Refresh to show selection change
                    event.Skip()
                    return
        
        # Check if clicking on a route to drag it
        route = self._hit_test_route(currentPos)
        if route is not None:
            from_id, to_id = route
            
            # Handle Shift+click for route path selection
            if event.ShiftDown() and self._lastSelectedRoute is not None:
                # Find path between last selected route and current route
                path = self._find_route_path_between_routes(self._lastSelectedRoute, route)
                if path:
                    # Select all routes in the path
                    if not event.ControlDown():
                        # Clear waypoints selection but keep route selection
                        self._selected_waypoints.clear()
                    
                    for route_tuple in path:
                        self._selected_routes.add(route_tuple)
                    
                    self._lastSelectedRoute = route
                    self.Refresh()
                    event.Skip()
                    return
            
            # Select the route if not already selected (unless Ctrl is held)
            if not event.ControlDown():
                # Clear selection and select only this route
                self._selected_waypoints.clear()
                self._selected_routes.clear()
                self._selected_routes.add(route)
            else:
                # Ctrl is held
                if route in self._selected_routes:
                    # Toggle off: remove from selection and don't drag
                    self._selected_routes.remove(route)
                    self.Refresh()
                    event.Skip()
                    return
                else:
                    # Add to selection
                    self._selected_routes.add(route)
            
            # Update last selected route for Shift+click
            self._lastSelectedRoute = route
            
            # Start dragging the route (both waypoints)
            network = self._datasMngr.getRoadNetwork()
            if network:
                from_wp = network.get_waypoint(from_id)
                to_wp = network.get_waypoint(to_id)
                if from_wp and to_wp:
                    self._isDraggingRoute = True
                    self._draggedRouteWaypoints = (from_id, to_id)
                    self._draggedRouteOriginalPositions = {
                        from_id: (from_wp.x, from_wp.z),
                        to_id: (to_wp.x, to_wp.z)
                    }
                    self._draggedRouteStartSnapshot = self._datasMngr.capture_snapshot()
                    
                    # Calculate the offset from click position to route midpoint
                    mid_x = (from_wp.x + to_wp.x) / 2
                    mid_z = (from_wp.z + to_wp.z) / 2
                    click_wx, click_wz = self.screen_to_world(currentPos.x, currentPos.y)
                    self._dragRouteOffset = (mid_x - click_wx, mid_z - click_wz)
                    
                    if not self.HasCapture():
                        self.CaptureMouse()
                    self.Refresh()  # Refresh to show selection change
                    event.Skip()
                    return
        
        # Handle Ctrl+Click on empty space: Create waypoint
        if event.ControlDown():
            # Get world coordinates
            wx_c, wz_c = self.screen_to_world(currentPos.x, currentPos.y)
            
            # Check for previous selection (for chain creation)
            previous_wp_id = None
            if len(self._selected_waypoints) == 1 and not self._selected_routes:
                previous_wp_id = list(self._selected_waypoints)[0]
            
            # Create new waypoint
            new_id = self._datasMngr.create_waypoint(wx_c, wz_c)
            
            if new_id is not None:
                # If we had a previous selection, try to link them
                if previous_wp_id is not None:
                    self._datasMngr.add_route(previous_wp_id, new_id)
                
                # Update selection to the new waypoint
                self._selected_waypoints.clear()
                self._selected_routes.clear()
                self._selected_waypoints.add(new_id)
                
                self.Refresh()
                # Update UI (title, status)
                parent = self.GetParent()
                while parent:
                    if hasattr(parent, 'UpdateModifiedState'):
                        parent.UpdateModifiedState()
                        break
                    parent = parent.GetParent()
                    
                event.Skip()
                return

        # Normal selection behavior
        self._lastMousePos = currentPos
        self._dragStartPos = currentPos
        self._currentDragPos = currentPos
        
        # Check if Shift is pressed for Shift+drag route selection
        if event.ShiftDown():
            self._isShiftLeftDragging = True
        else:
            self._isLeftDragging = True
        
        if not self.HasCapture():
            self.CaptureMouse()
        event.Skip()

    def OnLeftUp(self, event):
        """Handle left click release for selection end."""
        # Handle end of waypoint dragging
        if self._isDraggingWaypoint:
            # Reset dragging state
            # Check if actual drag occurred
            if self._draggedWaypointOriginalPos and self._draggedWaypointOriginalPos != (self._datasMngr.getRoadNetwork().get_waypoint(self._draggedWaypointId).x, self._datasMngr.getRoadNetwork().get_waypoint(self._draggedWaypointId).z):
                 self._datasMngr.register_external_change(self._draggedWaypointStartSnapshot)
                 
                 # Update main frame title
                 parent = self.GetParent()
                 while parent:
                    if hasattr(parent, 'UpdateModifiedState'):
                        parent.UpdateModifiedState()
                        break
                    parent = parent.GetParent()

            self._isDraggingWaypoint = False
            self._draggedWaypointId = None
            self._draggedWaypointOriginalPos = None
            self._draggedWaypointStartSnapshot = None
            
            if self.HasCapture():
                self.ReleaseMouse()
            self.Refresh()
            event.Skip()
            return
        
        # Handle end of route dragging
        if self._isDraggingRoute:
            # Check if actual drag occurred by comparing positions
            if self._draggedRouteOriginalPositions and self._draggedRouteWaypoints:
                network = self._datasMngr.getRoadNetwork()
                if network:
                    from_id, to_id = self._draggedRouteWaypoints
                    from_wp = network.get_waypoint(from_id)
                    to_wp = network.get_waypoint(to_id)
                    orig_from = self._draggedRouteOriginalPositions[from_id]
                    orig_to = self._draggedRouteOriginalPositions[to_id]
                    if from_wp and to_wp and ((from_wp.x, from_wp.z) != orig_from or (to_wp.x, to_wp.z) != orig_to):
                        self._datasMngr.register_external_change(self._draggedRouteStartSnapshot)
                        
                        # Update main frame title
                        parent = self.GetParent()
                        while parent:
                            if hasattr(parent, 'UpdateModifiedState'):
                                parent.UpdateModifiedState()
                                break
                            parent = parent.GetParent()
            
            # Reset dragging state
            self._isDraggingRoute = False
            self._draggedRouteWaypoints = None
            self._draggedRouteOriginalPositions = None
            self._dragRouteOffset = None
            self._draggedRouteStartSnapshot = None
            
            if self.HasCapture():
                self.ReleaseMouse()
            self.Refresh()
            event.Skip()
            return
        
        # Handle Zoom Window
        if self._isZoomWindowDragging:
            self._isZoomWindowDragging = False
            self.SetCursor(wx.NullCursor)
            if self.HasCapture():
                self.ReleaseMouse()
            
            if self._dragStartPos and self._currentDragPos:
                # Calculate rect
                x1, y1 = self._dragStartPos.x, self._dragStartPos.y
                x2, y2 = self._currentDragPos.x, self._currentDragPos.y
                
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                
                if w > 5 and h > 5:
                    # Calculate center of selection in screen coords
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    
                    # Convert center to world coords
                    wx_center, wz_center = self.screen_to_world(cx, cy)
                    
                    # Calculate scale
                    canvasW, canvasH = self.GetClientSize()
                    scaleX = canvasW / w
                    scaleY = canvasH / h
                    scale = min(scaleX, scaleY)
                    
                    # Apply new zoom
                    oldZoom = self._zoom
                    newZoom = oldZoom * scale
                    self._zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, newZoom))
                    
                    # Recalculate pan to center the selection
                    # screen_center = (world + map_center) * zoom + pan
                    # pan = screen_center - (world + map_center) * zoom
                    # We want screen_center to be (canvasW/2, canvasH/2)
                    
                    mapW = 0
                    mapH = 0
                    if self._mapBitmap:
                        mapW = self._mapBitmap.GetWidth()
                        mapH = self._mapBitmap.GetHeight()
                        
                    self._panX = (canvasW / 2) - (wx_center + mapW / 2.0) * self._zoom
                    self._panY = (canvasH / 2) - (wz_center + mapH / 2.0) * self._zoom
                    
                    self._clampPan()
            
            self._toolMode = 'default'
            self.Refresh()
            return

        if self._isLeftDragging:
            currentPos = event.GetPosition()
            
            # Check if it was a click (small movement) or a drag
            dragVec = currentPos - self._dragStartPos
            dist = (dragVec.x**2 + dragVec.y**2)**0.5
            
            network = self._datasMngr.getRoadNetwork()
            
            if dist < 5: # Considered a click
                # Single point selection - check waypoints first, then routes
                wp_id = self._hit_test(currentPos)
                
                if wp_id is not None:
                    # Clicked on a waypoint
                    if not event.ControlDown():
                        # Clear both selections if Ctrl not pressed
                        self._selected_waypoints.clear()
                        self._selected_routes.clear()
                    
                    if event.ControlDown() and wp_id in self._selected_waypoints:
                        self._selected_waypoints.remove(wp_id)
                    else:
                        self._selected_waypoints.add(wp_id)
                else:
                    # No waypoint hit, check for route
                    route = self._hit_test_route(currentPos)
                    
                    if route is not None:
                        # Clicked on a route
                        if not event.ControlDown():
                            # Clear both selections if Ctrl not pressed
                            self._selected_waypoints.clear()
                            self._selected_routes.clear()
                        
                        if event.ControlDown() and route in self._selected_routes:
                            self._selected_routes.remove(route)
                        else:
                            self._selected_routes.add(route)
                    else:
                        # Clicked on empty space
                        if not event.ControlDown():
                            self._selected_waypoints.clear()
                            self._selected_routes.clear()
                        
            elif network: # Drag selection - only selects waypoints
                # Calculate selection rect bounds
                start_x, start_y = self._dragStartPos.x, self._dragStartPos.y
                end_x, end_y = currentPos.x, currentPos.y
                
                x_min, x_max = min(start_x, end_x), max(start_x, end_x)
                y_min, y_max = min(start_y, end_y), max(start_y, end_y)
                
                # Handling Ctrl
                if not event.ControlDown():
                    self._selected_waypoints.clear()
                    self._selected_routes.clear()  # Clear routes on rectangle selection
                    
                # Convert screen rect to world coords
                # We need to handle each corner to get the min/max world bounds
                # screen_to_world takes screen coord and returns world coord
                wx1, wz1 = self.screen_to_world(x_min, y_min)
                wx2, wz2 = self.screen_to_world(x_max, y_max)
                
                # World bounds (min/max might be flipped depending on zoom/pan axes, normally X is consistent, Z might flip if inverted axis)
                w_min_x, w_max_x = min(wx1, wx2), max(wx1, wx2)
                w_min_z, w_max_z = min(wz1, wz2), max(wz1, wz2)
                
                for wp in network.waypoints.values():
                    if w_min_x <= wp.x <= w_max_x and w_min_z <= wp.z <= w_max_z:
                        self._selected_waypoints.add(wp.id)
            
            self._isLeftDragging = False
            self._dragStartPos = None
            self._currentDragPos = None
            if self.HasCapture():
                self.ReleaseMouse()
            self.Refresh()

        if self._isShiftLeftDragging:
            # Shift+drag selection - selects routes only
            currentPos = event.GetPosition()
            
            # Check if it was a click (small movement) or a drag
            dragVec = currentPos - self._dragStartPos
            dist = (dragVec.x**2 + dragVec.y**2)**0.5
            
            network = self._datasMngr.getRoadNetwork()
            
            if dist >= 5 and network: # Drag selection for routes
                # Calculate selection rect bounds
                start_x, start_y = self._dragStartPos.x, self._dragStartPos.y
                end_x, end_y = currentPos.x, currentPos.y
                
                x_min, x_max = min(start_x, end_x), max(start_x, end_x)
                y_min, y_max = min(start_y, end_y), max(start_y, end_y)
                
                # Handling Ctrl
                if not event.ControlDown():
                    self._selected_waypoints.clear()
                    self._selected_routes.clear()
                    
                # Convert screen rect to world coords
                wx1, wz1 = self.screen_to_world(x_min, y_min)
                wx2, wz2 = self.screen_to_world(x_max, y_max)
                
                w_min_x, w_max_x = min(wx1, wx2), max(wx1, wx2)
                w_min_z, w_max_z = min(wz1, wz2), max(wz1, wz2)
                
                # Select routes that are ENTIRELY within the selection rect
                for wp in network.waypoints.values():
                    for out_id in wp.outgoing:
                        route = (wp.id, out_id)
                        
                        # Get the other waypoint of the route
                        out_wp = network.get_waypoint(out_id)
                        if not out_wp:
                            continue
                        
                        # Select route only if BOTH waypoints are in the rect
                        if ((w_min_x <= wp.x <= w_max_x and w_min_z <= wp.z <= w_max_z) and
                            (w_min_x <= out_wp.x <= w_max_x and w_min_z <= out_wp.z <= w_max_z)):
                            self._selected_routes.add(route)
            
            self._isShiftLeftDragging = False
            self._dragStartPos = None
            self._currentDragPos = None
            if self.HasCapture():
                self.ReleaseMouse()
            self.Refresh()
            
        event.Skip()

    def OnLeftDClick(self, event):
        """Handle left double-click to select entire route chain."""
        currentPos = event.GetPosition()
        
        # Check if double-clicked on a waypoint first (higher priority)
        waypoint_id = self._hit_test(currentPos)
        
        if waypoint_id is not None:
            network = self._datasMngr.getRoadNetwork()
            if network:
                waypoint = network.get_waypoint(waypoint_id)
                if waypoint:
                    # Find all routes connected to this waypoint (incoming and outgoing)
                    connected_routes = set()
                    for outgoing_id in waypoint.outgoing:
                        route = (waypoint_id, outgoing_id)
                        connected_routes.add(route)
                    for incoming_id in waypoint.incoming:
                        route = (incoming_id, waypoint_id)
                        connected_routes.add(route)
                    
                    # Find the route chain for all connected routes
                    route_chain = set()
                    for start_route in connected_routes:
                        chain = self._find_route_chain(start_route)
                        route_chain.update(chain)
                    
                    if not event.ControlDown():
                        # Clear selections if Ctrl not pressed
                        self._selected_waypoints.clear()
                        self._selected_routes.clear()
                    
                    # Add all routes in the chain to selection
                    self._selected_routes.update(route_chain)
                    
                    # Also select intermediate waypoints (exclude endpoints)
                    intermediate_waypoints = self._get_intermediate_waypoints_from_routes(route_chain)
                    self._selected_waypoints.update(intermediate_waypoints)
                    
                    self.Refresh()
            
            event.Skip()
            return
        
        # Check if double-clicked on a route
        route = self._hit_test_route(currentPos)
        
        if route is not None:
            # Find the entire chain of connected routes
            route_chain = self._find_route_chain(route)
            
            if not event.ControlDown():
                # Clear selections if Ctrl not pressed
                self._selected_waypoints.clear()
                self._selected_routes.clear()
            
            # Add all routes in the chain to selection (don't select waypoints for route double-click)
            self._selected_routes.update(route_chain)
            
            self.Refresh()
        
        event.Skip()

    
    def _hit_test(self, pos):
        """Find the topmost waypoint under the mouse cursor."""
        network = self._datasMngr.getRoadNetwork()
        if not network:
            return None
        
        # Threshold squared (5px radius + 3px margin = 8px)
        threshold_sq = 64
        
        found_id = None
        canvasW, canvasH = self.GetClientSize()
        
        for wp_id, wp in network.waypoints.items():
            sx, sy = self.world_to_screen(wp.x, wp.z)
            
            # Culling optimization
            if sx < -10 or sx > canvasW + 10 or sy < -10 or sy > canvasH + 10:
                continue
                
            dx = pos.x - sx
            dy = pos.y - sy
            if dx*dx + dy*dy <= threshold_sq:
                found_id = wp_id
        
        return found_id
    
    def _hit_test_route(self, pos):
        """Find a route line under the mouse cursor.
        Returns (from_id, to_id) tuple if hit, None otherwise."""
        network = self._datasMngr.getRoadNetwork()
        if not network or not network.waypoints:
            return None
        
        # Threshold for line hit detection (in pixels)
        threshold = 8
        threshold_sq = threshold * threshold
        
        canvasW, canvasH = self.GetClientSize()
        
        # Check all connections
        for wp in network.waypoints.values():
            sx1, sy1 = self.world_to_screen(wp.x, wp.z)
            
            for out_id in wp.outgoing:
                out_wp = network.get_waypoint(out_id)
                if not out_wp:
                    continue
                
                sx2, sy2 = self.world_to_screen(out_wp.x, out_wp.z)
                
                # Skip if both points are off-screen
                if (sx1 < -50 and sx2 < -50) or (sx1 > canvasW + 50 and sx2 > canvasW + 50):
                    continue
                if (sy1 < -50 and sy2 < -50) or (sy1 > canvasH + 50 and sy2 > canvasH + 50):
                    continue
                
                # Calculate point-to-line-segment distance
                # Vector from point 1 to point 2
                dx = sx2 - sx1
                dy = sy2 - sy1
                
                # Vector from point 1 to mouse position
                px = pos.x - sx1
                py = pos.y - sy1
                
                # Length squared of the line segment
                len_sq = dx*dx + dy*dy
                
                if len_sq == 0:
                    # Degenerate case: line segment is a point
                    dist_sq = px*px + py*py
                else:
                    # Parameter t of the projection of point onto the line
                    # t = 0 means projection is at point 1, t = 1 means at point 2
                    t = max(0, min(1, (px*dx + py*dy) / len_sq))
                    
                    # Closest point on the line segment
                    closest_x = sx1 + t * dx
                    closest_y = sy1 + t * dy
                    
                    # Distance squared from mouse to closest point
                    dist_x = pos.x - closest_x
                    dist_y = pos.y - closest_y
                    dist_sq = dist_x*dist_x + dist_y*dist_y
                
                if dist_sq <= threshold_sq:
                    # Return the route as a tuple (from_id, to_id)
                    return (wp.id, out_id)
        
        return None

    def _find_route_chain(self, start_route):
        """Find a direction-continuous route chain from a start segment.
        
        Args:
            start_route: Tuple (from_id, to_id) representing the starting segment
            
        Returns:
            Set of route tuples forming the chain.
        """
        network = self._datasMngr.getRoadNetwork()
        if not network:
            return {start_route}
        
        chain = {start_route}
        start_from, start_to = start_route

        # Forward propagation: ... -> start_to -> next ...
        cur_from, cur_to = start_from, start_to
        while True:
            to_wp = network.get_waypoint(cur_to)
            if not to_wp:
                break

            # Keep only strict forward candidates (exclude immediate back edge).
            candidates = []
            for next_id in to_wp.outgoing:
                if next_id == cur_from:
                    continue
                next_route = (cur_to, next_id)
                if next_route not in chain:
                    candidates.append(next_route)

            # Stop on endpoint or branch: not a single direction-continuous path anymore.
            if len(candidates) != 1:
                break

            nxt = candidates[0]
            chain.add(nxt)
            cur_from, cur_to = nxt

        # Build a temporary reverse-lookup map for "Reverse" segments.
        # Standard predecessors are in wp.incoming.
        # Reverse predecessors (A->B where A is not in B.incoming) are NOT in incoming.
        # We need to scan the network or at least relevant parts to find them.
        # Since we don't know where they are, scanning the network once is the safest O(N) approach.
        # Optimization: lazy build or only if needed?
        # For simplicity and robustness, we build it. It's fast enough for 50k nodes.
        reverse_incoming = {} # target_id -> list of source_ids (that are reverse-connected)
        
        # We only really need to search if we risk encountering a reverse segment.
        # But to be safe, let's just do the scan.
        for wp in network.waypoints.values():
            for out_id in wp.outgoing:
                # If this is a one-way connection A->B and B doesn't know A, it's a reverse segment A->B
                # (or just a potential predecessor for B)
                target_wp = network.get_waypoint(out_id)
                if target_wp and wp.id not in target_wp.incoming:
                    reverse_incoming.setdefault(out_id, []).append(wp.id)

        # Backward propagation: ... -> prev -> start_from -> ...
        cur_from, cur_to = start_from, start_to
        while True:
            from_wp = network.get_waypoint(cur_from)
            if not from_wp:
                break

            # Candidates come from:
            # 1. Regular incoming connections (in from_wp.incoming)
            # 2. Reverse connections (in reverse_incoming[cur_from])
            
            raw_predecessors = list(from_wp.incoming)
            if cur_from in reverse_incoming:
                raw_predecessors.extend(reverse_incoming[cur_from])

            candidates = []
            for prev_id in raw_predecessors:
                if prev_id == cur_to:
                    continue
                prev_route = (prev_id, cur_from)
                if prev_route not in chain:
                    candidates.append(prev_route)

            # Stop on endpoint or branch.
            if len(candidates) != 1:
                break

            prv = candidates[0]
            chain.add(prv)
            cur_from, cur_to = prv

        return chain

    def _get_intermediate_waypoints_from_routes(self, routes):
        """Extract waypoint IDs from selected routes, excluding the endpoints.
        
        Endpoints are defined as:
        - The 'from_id' of routes with no incoming routes from the selection
        - The 'to_id' of routes with no outgoing routes from the selection
        
        Args:
            routes: Set of route tuples (from_id, to_id)
            
        Returns:
            Set of waypoint IDs that are intermediate (not endpoints)
        """
        if not routes:
            return set()
        
        network = self._datasMngr.getRoadNetwork()
        if not network:
            return set()
        
        # Build a map of all waypoints involved in the routes
        all_waypoints = set()
        outgoing_in_chain = {}  # wp_id -> set of out_ids in chain
        incoming_in_chain = {}  # wp_id -> set of in_ids in chain
        
        for from_id, to_id in routes:
            all_waypoints.add(from_id)
            all_waypoints.add(to_id)
            
            if from_id not in outgoing_in_chain:
                outgoing_in_chain[from_id] = set()
            outgoing_in_chain[from_id].add(to_id)
            
            if to_id not in incoming_in_chain:
                incoming_in_chain[to_id] = set()
            incoming_in_chain[to_id].add(from_id)
        
        # Find endpoints: waypoints that are only incoming or only outgoing in the chain
        endpoints = set()
        
        for wp_id in all_waypoints:
            has_incoming = wp_id in incoming_in_chain and len(incoming_in_chain[wp_id]) > 0
            has_outgoing = wp_id in outgoing_in_chain and len(outgoing_in_chain[wp_id]) > 0
            
            # If a waypoint has no incoming (start of chain) or no outgoing (end of chain),
            # and it's not a junction (single route in and single route out)
            if not has_incoming or not has_outgoing:
                endpoints.add(wp_id)
        
        # Return all waypoints except endpoints
        intermediate = all_waypoints - endpoints
        return intermediate

    def _get_orphan_endpoints_from_routes(self, routes):
        """Find endpoint waypoints that become orphaned after deleting the given routes.
        
        A waypoint becomes orphan if:
        - It's an endpoint of the selected routes (has no incoming or no outgoing within the chain)
        - After deleting the selected routes, it would have no other connections (incoming or outgoing)
        
        Args:
            routes: Set of route tuples (from_id, to_id) to be deleted
            
        Returns:
            Set of waypoint IDs that would become orphaned
        """
        if not routes:
            return set()
        
        network = self._datasMngr.getRoadNetwork()
        if not network:
            return set()
        
        # Get the endpoints first
        endpoints = set()
        all_waypoints_in_routes = set()
        outgoing_in_selection = {}  # wp_id -> set of out_ids in selection
        incoming_in_selection = {}  # wp_id -> set of in_ids in selection
        
        for from_id, to_id in routes:
            all_waypoints_in_routes.add(from_id)
            all_waypoints_in_routes.add(to_id)
            
            if from_id not in outgoing_in_selection:
                outgoing_in_selection[from_id] = set()
            outgoing_in_selection[from_id].add(to_id)
            
            if to_id not in incoming_in_selection:
                incoming_in_selection[to_id] = set()
            incoming_in_selection[to_id].add(from_id)
        
        # Find endpoints
        for wp_id in all_waypoints_in_routes:
            has_incoming = wp_id in incoming_in_selection and len(incoming_in_selection[wp_id]) > 0
            has_outgoing = wp_id in outgoing_in_selection and len(outgoing_in_selection[wp_id]) > 0
            
            if not has_incoming or not has_outgoing:
                endpoints.add(wp_id)
        
        # Now check which endpoints would become orphaned
        orphans = set()
        for wp_id in endpoints:
            wp = network.get_waypoint(wp_id)
            if not wp:
                continue
            
            # Count remaining connections after deletion of selected routes
            remaining_incoming = 0
            remaining_outgoing = 0
            
            # Check incoming connections that are NOT in the to-be-deleted routes
            for incoming_id in wp.incoming:
                if (incoming_id, wp_id) not in routes:
                    remaining_incoming += 1
            
            # Check outgoing connections that are NOT in the to-be-deleted routes
            for outgoing_id in wp.outgoing:
                if (wp_id, outgoing_id) not in routes:
                    remaining_outgoing += 1
            
            # If no remaining connections, this waypoint becomes orphaned
            if remaining_incoming == 0 and remaining_outgoing == 0:
                orphans.add(wp_id)
        
        return orphans

    def _draw_selection_rect(self, dc):
        """Draw the selection rectangle if dragging."""
        # Regular left drag (select waypoints)
        if self._isLeftDragging and self._dragStartPos and self._currentDragPos:
            # Check if it's a drag (dist > 5)
            dragVec = self._currentDragPos - self._dragStartPos
            dist = (dragVec.x**2 + dragVec.y**2)**0.5
            if dist < 5:
                # Don't draw rect for simple click
                return
                
            # Use GCDC for transparency if available, otherwise just line
            try:
                gc = wx.GraphicsContext.Create(dc)
                if gc:
                    x = self._dragStartPos.x
                    y = self._dragStartPos.y
                    w = self._currentDragPos.x - x
                    h = self._currentDragPos.y - y
                    
                    gc.SetPen(wx.Pen(wx.Colour(255, 255, 255, 128), 1, wx.PENSTYLE_SHORT_DASH))
                    gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 40)))
                    gc.DrawRectangle(x, y, w, h)
                    return
            except:
                pass
            
            # Fallback for standard DC if GC failed (no transparency brush on standard DC usually)
            dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 1, wx.PENSTYLE_SHORT_DASH))
            dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255), wx.BRUSHSTYLE_TRANSPARENT))
            
            x = self._dragStartPos.x
            y = self._dragStartPos.y
            w = self._currentDragPos.x - x
            h = self._currentDragPos.y - y
            
            dc.DrawRectangle(x, y, w, h)
        
        # Shift+drag (select routes) - draw in different color (green)
        elif self._isShiftLeftDragging and self._dragStartPos and self._currentDragPos:
            # Check if it's a drag (dist > 5)
            dragVec = self._currentDragPos - self._dragStartPos
            dist = (dragVec.x**2 + dragVec.y**2)**0.5
            if dist < 5:
                # Don't draw rect for simple click
                return
                
            # Use GCDC for transparency if available
            try:
                gc = wx.GraphicsContext.Create(dc)
                if gc:
                    x = self._dragStartPos.x
                    y = self._dragStartPos.y
                    w = self._currentDragPos.x - x
                    h = self._currentDragPos.y - y
                    
                    # Green color for route selection
                    gc.SetPen(wx.Pen(wx.Colour(0, 255, 100, 200), 2, wx.PENSTYLE_SOLID))
                    gc.SetBrush(wx.Brush(wx.Colour(0, 255, 100, 60)))
                    gc.DrawRectangle(x, y, w, h)
                    return
            except:
                pass
            
            # Fallback for standard DC
            dc.SetPen(wx.Pen(wx.Colour(0, 255, 100), 2, wx.PENSTYLE_SOLID))
            dc.SetBrush(wx.Brush(wx.Colour(0, 255, 100), wx.BRUSHSTYLE_TRANSPARENT))
            
            x = self._dragStartPos.x
            y = self._dragStartPos.y
            w = self._currentDragPos.x - x
            h = self._currentDragPos.y - y
            
            dc.DrawRectangle(x, y, w, h)

    def _draw_zoom_window_rect(self, dc):
        """Draw the zoom window rectangle if dragging."""
        if self._isZoomWindowDragging and self._dragStartPos and self._currentDragPos:
            # Check if it's a drag (dist > 5)
            dragVec = self._currentDragPos - self._dragStartPos
            dist = (dragVec.x**2 + dragVec.y**2)**0.5
            if dist < 5:
                return
                
            x = min(self._dragStartPos.x, self._currentDragPos.x)
            y = min(self._dragStartPos.y, self._currentDragPos.y)
            w = abs(self._currentDragPos.x - self._dragStartPos.x)
            h = abs(self._currentDragPos.y - self._dragStartPos.y)
            
            # Use GCDC for transparency
            try:
                gc = wx.GraphicsContext.Create(dc)
                if gc:
                    # Blue solid border, semi-transparent blue fill
                    gc.SetPen(wx.Pen(wx.Colour(0, 120, 255), 2, wx.PENSTYLE_SOLID))
                    gc.SetBrush(wx.Brush(wx.Colour(0, 120, 255, 40)))
                    gc.DrawRectangle(x, y, w, h)
                    return
            except:
                pass
            
            # Fallback
            dc.SetPen(wx.Pen(wx.Colour(0, 120, 255), 2, wx.PENSTYLE_SOLID))
            dc.SetBrush(wx.Brush(wx.Colour(0, 120, 255), wx.BRUSHSTYLE_TRANSPARENT))
            dc.DrawRectangle(x, y, w, h)
