import wx

_ = wx.GetTranslation


class DialogCheckResults(wx.Dialog):
    """Dialog displaying data validation results with click-to-navigate."""

    def __init__(self, parent, errors, on_select_callback):
        """
        Args:
            parent: Parent window.
            errors: list of (waypoint_id, message) tuples.
            on_select_callback: callable(wp_id) invoked when an entry is selected.
        """
        super().__init__(parent, title=_("Check Data"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self._errors = errors
        self._on_select = on_select_callback

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Header label
        header = wx.StaticText(
            self,
            label=_("{0} issue(s) detected:").format(len(errors))
        )
        sizer.Add(header, 0, wx.ALL, 10)

        # List of issues
        messages = [msg for _, msg in errors]
        self._listbox = wx.ListBox(self, choices=messages, style=wx.LB_SINGLE)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Close button
        btn_sizer = self.CreateButtonSizer(wx.CLOSE)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        self.SetSize(550, 350)
        self.CenterOnParent()

        # Bind events
        self._listbox.Bind(wx.EVT_LISTBOX, self._on_listbox_select)
        self.Bind(wx.EVT_BUTTON, self._on_close, id=wx.ID_CLOSE)

    def _on_listbox_select(self, event):
        """Handle selection of an issue in the list."""
        idx = self._listbox.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        wp_id, _ = self._errors[idx]
        if self._on_select:
            self._on_select(wp_id)

    def _on_close(self, event):
        """Close the dialog."""
        self.EndModal(wx.ID_CLOSE)
