import wx

_ = wx.GetTranslation

class MarkerDialog(wx.Dialog):
    """Dialog for creating or editing a map marker."""
    
    def __init__(self, parent, title="Marker", name="", group="All", groups=None):
        super().__init__(parent, title=title)
        
        self.name = name
        self.group = group
        
        # Sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid sizer for inputs
        grid = wx.FlexGridSizer(2, 2, 10, 10)
        grid.AddGrowableCol(1, 1)
        
        # Name input
        lbl_name = wx.StaticText(self, label=_("Name:"))
        self.txt_name = wx.TextCtrl(self, value=name)
        grid.Add(lbl_name, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.txt_name, 1, wx.EXPAND)
        
        # Group input
        lbl_group = wx.StaticText(self, label=_("Group:"))
        
        choices = groups if groups else ["All"]
        self.cb_group = wx.ComboBox(self, value=group, choices=choices, style=wx.CB_DROPDOWN)
        grid.Add(lbl_group, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.cb_group, 1, wx.EXPAND)
        
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)
        
        # Buttons
        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(sizer)
        self.Fit()
        self.CenterOnParent()
        
    def GetValues(self):
        """Return the (name, group) tuple entered by the user."""
        return self.txt_name.GetValue(), self.cb_group.GetValue()
