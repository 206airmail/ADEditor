import math
import wx

_ = wx.GetTranslation

class AddCurveDialog(wx.Dialog):
    """
    Dialog for creating a curve of waypoints between two selected points.
    """
    def __init__(self, parent, start_wp, end_wp, network, preview_callback=None):
        super().__init__(parent, title=_("Add Curve"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.start_wp = start_wp
        self.end_wp = end_wp
        self.network = network
        self.preview_callback = preview_callback
        
        # Internal state
        self._num_points = 5
        self._tangent_start_mode = 0  # 0=None, 1=In, 2=Out
        self._tangent_end_mode = 0    # 0=None, 1=In, 2=Out
        self._direction_mode = 0      # 0=OneWay(S->E), 1=OneWay(E->S), 2=Dual, 3=Reverse
        
        self._init_ui()
        self._update_preview()
        
    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 1. Number of points
        hbox_num = wx.BoxSizer(wx.HORIZONTAL)
        hbox_num.Add(wx.StaticText(self, label=_("Intermediate Waypoints:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.spin_points = wx.SpinCtrl(self, min=1, max=50, initial=5)
        self.spin_points.Bind(wx.EVT_SPINCTRL, self._on_param_change)
        hbox_num.Add(self.spin_points, 0, wx.ALIGN_CENTER_VERTICAL)
        main_sizer.Add(hbox_num, 0, wx.ALL | wx.EXPAND, 10)
        
        # 2. Tangency options
        sb_tangency = wx.StaticBox(self, label=_("Tangency"))
        sizer_tangency = wx.StaticBoxSizer(sb_tangency, wx.VERTICAL)
        
        # Start Tangency
        hbox_start = wx.BoxSizer(wx.HORIZONTAL)
        hbox_start.Add(wx.StaticText(self, label=_("Start (from selected):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        start_choices = [_("None"), _("Align with Incoming"), _("Align with Outgoing")]
        self.choice_start = wx.Choice(self, choices=start_choices)
        self.choice_start.SetSelection(0)
        
        # Logic to enable/disable based on connections
        has_incoming = len(self.start_wp.incoming) > 0
        has_outgoing = len(self.start_wp.outgoing) > 0
        
        # If no incoming/outgoing, we can't align
        # We can implement sophisticated logic here: disable specific items or reset selection
        # For simplicity, if not available, selecting it will just behave like None or be ignored in calc
        
        self.choice_start.Bind(wx.EVT_CHOICE, self._on_param_change)
        hbox_start.Add(self.choice_start, 1, wx.EXPAND)
        sizer_tangency.Add(hbox_start, 0, wx.ALL | wx.EXPAND, 5)

        # End Tangency
        hbox_end = wx.BoxSizer(wx.HORIZONTAL)
        hbox_end.Add(wx.StaticText(self, label=_("End (to selected):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        end_choices = [_("None"), _("Align with Incoming"), _("Align with Outgoing")]
        self.choice_end = wx.Choice(self, choices=end_choices)
        self.choice_end.SetSelection(0)
        self.choice_end.Bind(wx.EVT_CHOICE, self._on_param_change)
        hbox_end.Add(self.choice_end, 1, wx.EXPAND)
        sizer_tangency.Add(hbox_end, 0, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(sizer_tangency, 0, wx.ALL | wx.EXPAND, 10)
        
        # 3. Direction
        directions = [
            _("One Way (Start -> End)"), 
            _("One Way (End -> Start)"),
            _("Dual Way"),
            _("Reverse (Start -> End)")
        ]
        self.radio_dir = wx.RadioBox(self, label=_("Route Direction"), choices=directions, majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.radio_dir.SetSelection(0)
        self.radio_dir.Bind(wx.EVT_RADIOBOX, self._on_param_change)
        main_sizer.Add(self.radio_dir, 0, wx.ALL | wx.EXPAND, 10)
        
        # Buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        self.SetSizer(main_sizer)
        self.Fit()
        self.CenterOnParent()

    def _on_param_change(self, event):
        self._num_points = self.spin_points.GetValue()
        self._tangent_start_mode = self.choice_start.GetSelection()
        self._tangent_end_mode = self.choice_end.GetSelection()
        self._direction_mode = self.radio_dir.GetSelection()
        
        self._update_preview()
        
    def _update_preview(self):
        """Calculate curve points and call callback."""
        if not self.preview_callback:
            return
            
        points = self._calculate_bezier_points()
        
        # Generate connections based on direction
        connections = []
        count = len(points)
        if count < 2:
            pass # Should be at least start and end
        
        # 0=OneWay(S->E), 1=OneWay(E->S), 2=Dual, 3=Reverse
        # Points list includes [Start, p1, p2, ... End]
        
        for i in range(count - 1):
            u, v = i, i + 1
            if self._direction_mode == 0: # S->E
                connections.append((u, v))
            elif self._direction_mode == 1: # E->S
                connections.append((v, u))
            elif self._direction_mode == 2: # Dual
                connections.append((u, v))
                connections.append((v, u))
            elif self._direction_mode == 3: # Reverse (Start -> End geometry, but reverse logic)
                # Visualized as forward connection usually, or blue if fully implemented in preview
                connections.append((u, v))

        self.preview_callback(points, connections)

    def GetCurveData(self):
        """Return (points, direction_mode)."""
        return self._calculate_bezier_points(), self._direction_mode

    def _calculate_bezier_points(self):
        """
        Calculate cubic Bezier curve points.
        Returns list of (x, y, z) tuples including start and end.
        """
        p0 = (self.start_wp.x, self.start_wp.y, self.start_wp.z)
        p3 = (self.end_wp.x, self.end_wp.y, self.end_wp.z)
        
        # Distance between P0 and P3
        dx = p3[0] - p0[0]
        dy = p3[1] - p0[1]
        dz = p3[2] - p0[2]
        dist = math.sqrt(dx*dx + dz*dz) # Planar distance for control length
        if dist < 0.1: dist = 0.1
        
        ctrl_len = dist / 3.0
        
        # Determine forward tangent directions (normalized)
        dir_start = self._get_forward_tangent(self.start_wp, self._tangent_start_mode, p0, p3, is_start=True)
        dir_end   = self._get_forward_tangent(self.end_wp,   self._tangent_end_mode,   p0, p3, is_start=False)
        
        # Calculate Control Points
        # P1 = P0 + dir_start * len
        p1 = (
            p0[0] + dir_start[0] * ctrl_len,
            p0[1] + dir_start[1] * ctrl_len, # Full 3D Bezier
            p0[2] + dir_start[2] * ctrl_len
        )

        # P2 = P3 - dir_end * len (Backwards from destination)
        p2 = (
            p3[0] - dir_end[0] * ctrl_len,
            p3[1] - dir_end[1] * ctrl_len,
            p3[2] - dir_end[2] * ctrl_len
        )
        
        # Generate intermediate points
        n_steps = self._num_points + 1
        
        result_points = []
        for i in range(n_steps + 1):
            t = i / float(n_steps)
            mt = 1 - t
            
            # Cubic Bezier explicit formula
            # P(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t)t^2 P2 + t^3 P3
            
            c0 = mt**3
            c1 = 3 * mt**2 * t
            c2 = 3 * mt * t**2
            c3 = t**3
            
            x = c0*p0[0] + c1*p1[0] + c2*p2[0] + c3*p3[0]
            y = c0*p0[1] + c1*p1[1] + c2*p2[1] + c3*p3[1]
            z = c0*p0[2] + c1*p1[2] + c2*p2[2] + c3*p3[2]
            
            result_points.append((x, y, z))
            
        return result_points

    def _get_forward_tangent(self, wp, mode, p_start, p_end, is_start):
        """
        Get normalized FORWARD vector (x, y, z) representing the flow direction at this point.
        """
        # Default: straight line P0 -> P3
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        dz = p_end[2] - p_start[2]
        
        base_len = math.sqrt(dx*dx + dy*dy + dz*dz)
        if base_len > 0:
            default_dir = (dx/base_len, dy/base_len, dz/base_len)
        else:
            default_dir = (1, 0, 0) # Arbitrary
            
        if mode == 0: # None
            return default_dir
            
        # 1 = Align with Incoming (Prev -> WP)
        # 2 = Align with Outgoing (WP -> Next)
        
        target_vec = None
        
        if mode == 1: # Incoming
            if wp.incoming:
                prev_id = wp.incoming[0]
                prev_wp = self.network.get_waypoint(prev_id)
                if prev_wp:
                    # Flow is Prev -> WP.
                    # User wants to align with Incoming *Link*.
                    # Interpretation: Vector pointing BACK to where we came from?
                    # Or Vector pointing FORWARD following the flow?
                    # User request: "One option should be the inverse of the other".
                    # Outgoing is usually Forward (WP->Next).
                    # So Incoming should be Backward (WP->Prev).
                    vx = prev_wp.x - wp.x
                    vy = prev_wp.y - wp.y
                    vz = prev_wp.z - wp.z
                    target_vec = (vx, vy, vz)
        
        elif mode == 2: # Outgoing
            if wp.outgoing:
                next_id = wp.outgoing[0]
                next_wp = self.network.get_waypoint(next_id)
                if next_wp:
                    # Flow is WP -> Next
                    vx = next_wp.x - wp.x
                    vy = next_wp.y - wp.y
                    vz = next_wp.z - wp.z
                    target_vec = (vx, vy, vz)

                    
        if target_vec:
            vx, vy, vz = target_vec
            length = math.sqrt(vx*vx + vy*vy + vz*vz)
            if length > 0:
                return (vx/length, vy/length, vz/length)
                
        return default_dir

