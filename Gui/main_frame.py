import wx
import os
from datetime import datetime
from xml.etree import ElementTree as ETree
import shutil
from Core import RoadNetwork, Waypoint, MapMarker, SettingsManager, AppVersion, DatasManager, FarmSimHelper
from Graphx import mainImages, getToolbarBitmaps
from Gui import MapCanvas
from Dialogs import NewProjectDialog, AboutDialog, SettingsDialog, MarkerDialog

_ = wx.GetTranslation

class MainFrame(wx.Frame):
    def __init__(self):
        v = AppVersion()
        self._sBaseTitle = v.getMainWindowTitle()

        self._optMngr = SettingsManager()
        self._dataMngr = DatasManager()

        self._fileHistory = wx.FileHistory()

        super().__init__(None, title=self._sBaseTitle, size=self._optMngr.MainWndStartupSize,)

        appIcon = wx.BitmapBundle.FromSVG(mainImages['appIcon.svg'], (32, 32)).GetIconFor(self)
        self.SetIcon(appIcon)

        self.CreateStatusBar(3) # A Statusbar in the bottom of the window

        # Needed but unexisting IDs
        self.ID_ZOOM_RECT = wx.NewIdRef()
        self.ID_ROUTE_SWAPDIR = wx.NewIdRef()
        self.ID_ROUTE_ADD = wx.NewIdRef()
        self.ID_MARKER_ADD = wx.NewIdRef()
        self.ID_MARKER_EDIT = wx.NewIdRef()
        self.ID_MARKER_DEL = wx.NewIdRef()
        self.ID_SAVE_TO_FS = wx.NewIdRef()
        self.ID_RESTORE_FS = wx.NewIdRef()

        self._CreateToolsAndMenuBars()
        
        list = self._optMngr.RecentFiles
        if len(list):
            for f in list:
                self._fileHistory.AddFileToHistory(f)
        
        self._CreateInterface()

        mode, pos = self._optMngr.MainWndStartupPos
        sz = self._optMngr.MainWndStartupSize
        self.SetMinSize(self._optMngr.MainWndMinimalSize)

    def _CreateInterface(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
            
        # Pass data manager to MapCanvas
        self.mapCanvas = MapCanvas(self, self._dataMngr)
        sizer.Add(self.mapCanvas, 1, wx.EXPAND)
        
        self.SetSizer(sizer)
        self.Layout()

        mode, pos = self._optMngr.MainWndStartupPos
        sz = self._optMngr.MainWndStartupSize
        self.SetMinSize(self._optMngr.MainWndMinimalSize)

        if mode == wx.ALIGN_NOT:
            if sz == wx.DefaultSize:
                if pos == wx.DefaultPosition:
                    self.Maximize()
                else:
                    self.CenterOnScreen()
            else:
                self.Move(pos)
                self.SetSize(sz)
        else:
            iWScr, iHScr = wx.GetDisplaySize()
            if sz == wx.DefaultSize:
                sz = self.GetSize()
            pt = wx.DefaultPosition
            if (mode & wx.LEFT) == wx.LEFT:
                pt.x = 0
            elif (mode & wx.RIGHT) == wx.RIGHT:
                pt.x = iWScr - sz.GetWidth()
            else:
                pt.x = (iWScr - sz.GetWidth()) // 2
            if (mode & wx.TOP) == wx.TOP:
                pt.y = 0
            elif (mode & wx.BOTTOM) == wx.BOTTOM:
                pt.y = iHScr - sz.GetHeight()
            else:
                pt.y = (iHScr - sz.GetHeight()) // 2
            self.Move(pt)
            self.SetSize(sz)

        self._BindEvents()

    def _CreateToolsAndMenuBars(self):
        """Create the toolbar and the menubar for the main frame."""
        # Create the menubar
        menuBar = wx.MenuBar()
        # File menu
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_NEW)
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_OPEN)
        file_menu.Append(wx.ID_SAVE)
        file_menu.Append(wx.ID_SAVEAS)
        file_menu.AppendSeparator()
        file_menu.Append(self.ID_SAVE_TO_FS, _("Export to FS Savegame"), helpString=_("Export Autodrive datas to a Farming Simulator savegame"))
        file_menu.Append(self.ID_RESTORE_FS, _("Restore to FS Savegame"), helpString=_("Restore original datas to the Farming Simulator savegame"))
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_PREFERENCES)
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT)
        menuBar.Append(file_menu, wx.GetStockLabel(wx.ID_FILE))
        self._fileHistory.UseMenu(file_menu)
        # Edit menu
        edit_menu = wx.Menu()
        edit_menu.Append(wx.ID_UNDO)
        edit_menu.Append(wx.ID_REDO)
        edit_menu.AppendSeparator()
        edit_menu.Append(wx.ID_DELETE, helpString=_("Delete selected item(s)"))
        menuBar.Append(edit_menu, wx.GetStockLabel(wx.ID_EDIT))
        # Help menu
        menu = wx.Menu()
        menu.Append(wx.ID_ABOUT)
        menuBar.Append(menu, wx.GetStockLabel(wx.ID_HELP))
        
        self.SetMenuBar(menuBar)

        #--- Create the toolbar ---
        tb = self.CreateToolBar()
        bmpSize = (32, 32)
        tb.SetToolBitmapSize(bmpSize)

        def _add_tool(tool_id, label, icon_id, short_help):
            bmp, bmp_disabled = getToolbarBitmaps(icon_id, bmpSize)
            tb.AddTool(tool_id, label, bmp, bmpDisabled=bmp_disabled, shortHelp=short_help)

        # Project-related tools
        _add_tool(wx.ID_NEW, wx.GetStockLabel(wx.ID_NEW), "ID_NEW", _("Create a new project"))
        _add_tool(wx.ID_OPEN, wx.GetStockLabel(wx.ID_OPEN), "ID_OPEN", _("Open an existing project"))
        _add_tool(wx.ID_SAVE, wx.GetStockLabel(wx.ID_SAVE), "ID_SAVE", _("Save the current project"))
        _add_tool(wx.ID_SAVEAS, wx.GetStockLabel(wx.ID_SAVEAS), "ID_SAVEAS", _("Save the current project with a new name"))
        tb.AddSeparator()
        # Undo/Redo tools
        _add_tool(wx.ID_UNDO, wx.GetStockLabel(wx.ID_UNDO), "ID_UNDO", _("Undo last action"))
        _add_tool(wx.ID_REDO, wx.GetStockLabel(wx.ID_REDO), "ID_REDO", _("Redo last action"))
        # View-related tools
        _add_tool(wx.ID_ZOOM_IN, wx.GetStockLabel(wx.ID_ZOOM_IN), "ID_ZOOM_IN", _("Zoom In"))
        _add_tool(wx.ID_ZOOM_OUT, wx.GetStockLabel(wx.ID_ZOOM_OUT), "ID_ZOOM_OUT", _("Zoom Out"))
        _add_tool(wx.ID_ZOOM_FIT, wx.GetStockLabel(wx.ID_ZOOM_FIT), "ID_ZOOM_AUTO", _("Reset Zoom"))
        _add_tool(self.ID_ZOOM_RECT, _("Window zoom"), "ID_ZOOM_RECT", _("Zoom to Rectangle"))
        tb.AddSeparator()
        # Edition tools
        _add_tool(wx.ID_DELETE, wx.GetStockLabel(wx.ID_DELETE), "ID_DELETE", _("Delete selected item(s)"))
        _add_tool(self.ID_ROUTE_SWAPDIR, _("Direction"), "ID_ROUTE_SWAPDIR", _("Swap Route Direction"))
        _add_tool(self.ID_ROUTE_ADD, _("Connect"), "ID_ROUTE_ADD", _("Connect 2 waypoints"))
        _add_tool(self.ID_MARKER_ADD, _("Add Marker"), "ID_MARKER_ADD", _("Create Map Marker"))
        _add_tool(self.ID_MARKER_EDIT, _("Edit Marker"), "ID_MARKER_EDIT", _("Edit selected Map Marker"))
        _add_tool(self.ID_MARKER_DEL, _("Del Marker"), "ID_MARKER_DEL", _("Delete Map Marker"))
        tb.AddStretchableSpace()
        _add_tool(wx.ID_PREFERENCES, wx.GetStockLabel(wx.ID_PREFERENCES), "ID_PREFERENCES", _("Open settings dialog"))
        _add_tool(wx.ID_ABOUT, wx.GetStockLabel(wx.ID_ABOUT), "ID_ABOUT", _("Show about dialog"))
        tb.Realize()

    def _BindEvents(self):
        # General events
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Menus and toolbar items
        self.Bind(wx.EVT_MENU, self.OnNewClicked, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.OnOpenClicked, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnSaveClicked, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.OnSaveAsClicked, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnExportToFSClicked, id=self.ID_SAVE_TO_FS)
        self.Bind(wx.EVT_MENU, self.OnRestoreFSClicked, id=self.ID_RESTORE_FS)
        self.Bind(wx.EVT_MENU, self.OnUndoClicked, id=wx.ID_UNDO)
        self.Bind(wx.EVT_MENU, self.OnRedoClicked, id=wx.ID_REDO)
        self.Bind(wx.EVT_MENU, self.OnPrefsClicked, id=wx.ID_PREFERENCES)
        self.Bind(wx.EVT_MENU, self.OnExitClicked, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAboutClicked, id=wx.ID_ABOUT)
        id1 = self._fileHistory.GetBaseId()
        id2 = id1 + self._fileHistory.GetMaxFiles()-1
        self.Bind(wx.EVT_MENU_RANGE, self.OnReopenClicked, id=id1, id2=id2)
        self.Bind(wx.EVT_MENU, self.OnZoomIn, id=wx.ID_ZOOM_IN)
        self.Bind(wx.EVT_MENU, self.OnZoomOut, id=wx.ID_ZOOM_OUT)
        self.Bind(wx.EVT_MENU, self.OnZoomReset, id=wx.ID_ZOOM_FIT)
        self.Bind(wx.EVT_MENU, self.OnZoomWindow, id=self.ID_ZOOM_RECT)
        self.Bind(wx.EVT_MENU, self.OnDeleteSelection, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnSwapRouteDirection, id=self.ID_ROUTE_SWAPDIR)
        # Update UI events
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_Save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_SaveAs, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_ExportFS, id=self.ID_SAVE_TO_FS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_RestoreFS, id=self.ID_RESTORE_FS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_Undo, id=wx.ID_UNDO)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_Redo, id=wx.ID_REDO)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_Delete, id=wx.ID_DELETE)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_SwapDir, id=self.ID_ROUTE_SWAPDIR)
        self.Bind(wx.EVT_MENU, self.OnAddRoute, id=self.ID_ROUTE_ADD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_AddRoute, id=self.ID_ROUTE_ADD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_AddMark, id=self.ID_MARKER_ADD)
        self.Bind(wx.EVT_MENU, self.OnAddMarker, id=self.ID_MARKER_ADD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_EditMark, id=self.ID_MARKER_EDIT)
        self.Bind(wx.EVT_MENU, self.OnEditMarker, id=self.ID_MARKER_EDIT)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI_DelMark, id=self.ID_MARKER_DEL)
        self.Bind(wx.EVT_MENU, self.OnDelMarker, id=self.ID_MARKER_DEL)

    def OnClose(self, event):
        nb = self._fileHistory.Count
        flist = []
        if nb:
            for index in range(nb):
                flist.append(self._fileHistory.GetHistoryFile(index))
            self._optMngr.RecentFiles = flist
        event.Skip()

    def OnNewClicked(self, event):
        dlg = NewProjectDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._updateMainTitle()
            if self._dataMngr.getProjectFilePath():
                self._fileHistory.AddFileToHistory(self._dataMngr.getProjectFilePath())
            # Update map canvas with new project data
            self.mapCanvas.RefreshMapData()
            self.mapCanvas.FitToWindow()
        dlg.Destroy()

    def _updateMainTitle(self):
        title = self._sBaseTitle
        if self._dataMngr.isOk():
            v = AppVersion()
            title = v.getAppName(short=False) + " : " + self._dataMngr.getProjectName()
            if self._dataMngr.isModified():
                title += " *"
        self.SetTitle(title)
    
    def OnOpenClicked(self, event):
        sWildcard = _("AutoDrive Project (*.adproject)|*.adproject|All Files (*.*)|*.*")
        with wx.FileDialog(self, _("Open AutoDrive Editor Project"), 
                           wildcard=sWildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            self._doLoadProject(pathname)

    def OnReopenClicked(self, event):
        id = event.GetId()
        index = id - self._fileHistory.GetBaseId()
        filename = self._fileHistory.GetHistoryFile(index)
        if os.path.isfile(filename):
            self._doLoadProject(filename)
        else:
            wx.MessageBox(_("File not found:") + f" {filename}", 
                         _("Error"), wx.OK | wx.ICON_ERROR)
            self._fileHistory.RemoveFileFromHistory(index)

    def _doLoadProject(self, filename):
        if self._dataMngr.loadProjectFile(filename):
            self._updateMainTitle()
            self._fileHistory.AddFileToHistory(filename)
            # Update map canvas with new project data
            self.mapCanvas.RefreshMapData()
            self.mapCanvas.FitToWindow()
            return True
        else:
            wx.MessageBox(_("Failed to load project file."), 
                         _("Error"), wx.OK | wx.ICON_ERROR)
            return False

    def OnSaveClicked(self, event):
        path = self._dataMngr.getProjectFilePath()
        if not path:
            self.OnSaveAsClicked(event)
        else:
            self._doSaveProject(path)

    def OnSaveAsClicked(self, event):
        sWildcard = _("AutoDrive Project (*.adproject)|*.adproject|All Files (*.*)|*.*")
        with wx.FileDialog(self, _("Save AutoDrive Editor Project"), 
                           wildcard=sWildcard,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            self._doSaveProject(pathname)

    def _doSaveProject(self, filename):
        if self._dataMngr.saveProjectFile(filename):
            self._updateMainTitle()
            self._fileHistory.AddFileToHistory(filename)
            return True
        else:
            wx.MessageBox(_("Failed to save project file."), 
                         _("Error"), wx.OK | wx.ICON_ERROR)
            return False
    
    def OnExportToFSClicked(self, event):
        if not self._dataMngr.isOk():
            wx.MessageBox(_("No project loaded."), _("Export"), wx.OK | wx.ICON_INFORMATION)
            return

        default_dir = self._dataMngr.getSavegamePath()
        if not default_dir or not os.path.isdir(default_dir):
            default_dir = FarmSimHelper().getFsUserPath()

        with wx.DirDialog(
            self,
            _("Select Farming Simulator savegame folder"),
            defaultPath=default_dir,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        ) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            savegame_dir = dirDialog.GetPath()

        fs_helper = FarmSimHelper()
        if not fs_helper.isFS_Savegame(savegame_dir):
            wx.MessageBox(
                _("The selected folder is not a valid Farming Simulator savegame.\nMissing 'careerSavegame.xml'."),
                _("Export"), wx.OK | wx.ICON_ERROR
            )
            return

        selected_map_id = self._get_savegame_map_id(savegame_dir)
        if not selected_map_id:
            wx.MessageBox(
                _("Failed to read map information from selected savegame."),
                _("Export"), wx.OK | wx.ICON_ERROR
            )
            return

        project_savegame = self._dataMngr.getSavegamePath()
        project_map_id = self._get_savegame_map_id(project_savegame) if project_savegame else None
        if not project_map_id:
            wx.MessageBox(
                _("Failed to read map information from the project's original savegame.\nCannot verify map compatibility."),
                _("Export"), wx.OK | wx.ICON_ERROR
            )
            return

        if selected_map_id != project_map_id:
            wx.MessageBox(
                _("Map mismatch:\nProject map: {0}\nSelected savegame map: {1}").format(project_map_id, selected_map_id),
                _("Export"), wx.OK | wx.ICON_ERROR
            )
            return

        ad_target_path = os.path.join(savegame_dir, "AutoDrive_config.xml")
        backup_path = None

        try:
            from Core.autodrive_parser import parse_autodrive_xml, save_autodrive_xml, save_autodrive_xml_with_template

            network = self._dataMngr.getRoadNetwork()
            export_network, ids_renumbered = self._prepare_network_for_fs_export(network)

            validation_errors = self._validate_network_for_export(export_network)
            if validation_errors:
                lines = "\n".join(f"- {err}" for err in validation_errors[:20])
                if len(validation_errors) > 20:
                    lines += _("\n- ... and {0} more issue(s)").format(len(validation_errors) - 20)
                wx.MessageBox(
                    _("Export blocked: invalid network data detected.\n\n{0}").format(lines),
                    _("Export"), wx.OK | wx.ICON_ERROR
                )
                return

            before_network = None
            if os.path.isfile(ad_target_path):
                before_network = parse_autodrive_xml(ad_target_path)

            if os.path.isfile(ad_target_path):
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_name = f"AutoDrive_config.xml.{timestamp}.bak"
                backup_path = os.path.join(savegame_dir, backup_name)
                shutil.copy2(ad_target_path, backup_path)
                if before_network is None:
                    before_network = parse_autodrive_xml(backup_path)

            if os.path.isfile(ad_target_path):
                ok = save_autodrive_xml_with_template(export_network, ad_target_path, ad_target_path)
            else:
                ok = save_autodrive_xml(export_network, ad_target_path)

            if not ok:
                wx.MessageBox(_("Failed to export AutoDrive data."), _("Export"), wx.OK | wx.ICON_ERROR)
                return

            report = self._build_export_report(before_network, export_network, ad_target_path, backup_path, ids_renumbered)
            msg = _("AutoDrive data exported successfully.\n\n{0}").format(report)
            wx.MessageBox(msg, _("Export"), wx.OK | wx.ICON_INFORMATION)
        except Exception as ex:
            wx.MessageBox(
                _("Export failed:\n{0}").format(str(ex)),
                _("Export"), wx.OK | wx.ICON_ERROR
            )
    
    def OnRestoreFSClicked(self, event):
        if not self._dataMngr.isOk():
            wx.MessageBox(_("No project loaded."), _("Restore"), wx.OK | wx.ICON_INFORMATION)
            return

        original_xml = self._dataMngr.getOriginalADConfigBytes()
        if not original_xml:
            wx.MessageBox(
                _("Original AutoDrive data not found in project or source path."),
                _("Restore"), wx.OK | wx.ICON_ERROR
            )
            return

        default_dir = self._dataMngr.getSavegamePath()
        if not default_dir or not os.path.isdir(default_dir):
            default_dir = FarmSimHelper().getFsUserPath()

        with wx.DirDialog(
            self,
            _("Select Farming Simulator savegame folder"),
            defaultPath=default_dir,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        ) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            savegame_dir = dirDialog.GetPath()

        fs_helper = FarmSimHelper()
        if not fs_helper.isFS_Savegame(savegame_dir):
            wx.MessageBox(
                _("The selected folder is not a valid Farming Simulator savegame.\nMissing 'careerSavegame.xml'."),
                _("Restore"), wx.OK | wx.ICON_ERROR
            )
            return

        selected_map_id = self._get_savegame_map_id(savegame_dir)
        if not selected_map_id:
            wx.MessageBox(
                _("Failed to read map information from selected savegame."),
                _("Restore"), wx.OK | wx.ICON_ERROR
            )
            return

        project_savegame = self._dataMngr.getSavegamePath()
        project_map_id = self._get_savegame_map_id(project_savegame) if project_savegame else None
        if not project_map_id:
            wx.MessageBox(
                _("Failed to read map information from the project's original savegame.\nCannot verify map compatibility."),
                _("Restore"), wx.OK | wx.ICON_ERROR
            )
            return

        if selected_map_id != project_map_id:
            wx.MessageBox(
                _("Map mismatch:\nProject map: {0}\nSelected savegame map: {1}").format(project_map_id, selected_map_id),
                _("Restore"), wx.OK | wx.ICON_ERROR
            )
            return

        ad_target_path = os.path.join(savegame_dir, "AutoDrive_config.xml")

        if wx.MessageBox(
            _("Restore original AutoDrive data into this savegame?\nThis will overwrite current AutoDrive_config.xml."),
            _("Confirm Restore"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        ) != wx.YES:
            return

        try:
            backup_path = None
            if os.path.isfile(ad_target_path):
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_name = f"AutoDrive_config.xml.{timestamp}.bak"
                backup_path = os.path.join(savegame_dir, backup_name)
                shutil.copy2(ad_target_path, backup_path)

            with open(ad_target_path, "wb") as f:
                f.write(original_xml)

            msg = _("Original AutoDrive data restored successfully:\n{0}").format(ad_target_path)
            if backup_path:
                msg += _("\nBackup created:\n{0}").format(backup_path)
            wx.MessageBox(msg, _("Restore"), wx.OK | wx.ICON_INFORMATION)
        except Exception as ex:
            wx.MessageBox(
                _("Restore failed:\n{0}").format(str(ex)),
                _("Restore"), wx.OK | wx.ICON_ERROR
            )

    def _validate_network_for_export(self, network):
        errors = []
        if not network:
            return [_("No network loaded.")]

        for wp_id, wp in network.waypoints.items():
            if wp.id != wp_id:
                errors.append(_("Waypoint key/id mismatch for waypoint {0}.").format(wp_id))

            for out_id in wp.outgoing:
                target = network.get_waypoint(out_id)
                if target is None:
                    errors.append(_("Waypoint {0}: outgoing reference to missing waypoint {1}.").format(wp_id, out_id))
                    continue
                if wp_id not in target.incoming:
                    errors.append(_("Waypoint {0}->{1}: missing reciprocal incoming reference.").format(wp_id, out_id))

            for in_id in wp.incoming:
                src = network.get_waypoint(in_id)
                if src is None:
                    errors.append(_("Waypoint {0}: incoming reference from missing waypoint {1}.").format(wp_id, in_id))
                    continue
                if wp_id not in src.outgoing:
                    errors.append(_("Waypoint {0}<-{1}: missing reciprocal outgoing reference.").format(wp_id, in_id))

        for marker in network.markers:
            if network.get_waypoint(marker.waypoint_id) is None:
                errors.append(_("Marker '{0}' points to missing waypoint {1}.").format(marker.name, marker.waypoint_id))

        return errors

    def _build_export_report(self, before_network, after_network, ad_target_path, backup_path, ids_renumbered=False):
        wp_total = len(after_network.waypoints) if after_network else 0
        rt_total = self._count_routes(after_network)
        mk_total = len(after_network.markers) if after_network else 0

        lines = [
            _("File: {0}").format(ad_target_path),
            _("Totals - Waypoints: {0}, Routes: {1}, Markers: {2}").format(wp_total, rt_total, mk_total),
        ]

        if before_network and after_network:
            delta = self._compute_network_delta(before_network, after_network)
            lines.append(
                _("Changes - Waypoints: +{0} / -{1} / ~{2}").format(
                    delta["waypoints_added"], delta["waypoints_removed"], delta["waypoints_changed"]
                )
            )
            lines.append(
                _("Changes - Routes: +{0} / -{1}").format(
                    delta["routes_added"], delta["routes_removed"]
                )
            )
            lines.append(
                _("Changes - Markers: +{0} / -{1} / ~{2}").format(
                    delta["markers_added"], delta["markers_removed"], delta["markers_changed"]
                )
            )
        else:
            lines.append(_("Changes - baseline unavailable (new file or source read failed)."))

        if ids_renumbered:
            lines.append(_("Note: waypoint IDs were renumbered to a dense 1..N range for FS compatibility."))

        if backup_path:
            lines.append(_("Backup: {0}").format(backup_path))
        return "\n".join(lines)

    def _count_routes(self, network):
        if not network:
            return 0
        return sum(len(wp.outgoing) for wp in network.waypoints.values())

    def _compute_network_delta(self, before, after):
        before_ids = set(before.waypoints.keys())
        after_ids = set(after.waypoints.keys())
        wp_added = len(after_ids - before_ids)
        wp_removed = len(before_ids - after_ids)

        common_ids = before_ids & after_ids
        wp_changed = 0
        for wp_id in common_ids:
            b = before.waypoints[wp_id]
            a = after.waypoints[wp_id]
            if (round(b.x, 3), round(b.y, 3), round(b.z, 3), int(b.flag), tuple(b.outgoing), tuple(b.incoming)) != \
               (round(a.x, 3), round(a.y, 3), round(a.z, 3), int(a.flag), tuple(a.outgoing), tuple(a.incoming)):
                wp_changed += 1

        before_routes = {(wp_id, out_id) for wp_id, wp in before.waypoints.items() for out_id in wp.outgoing}
        after_routes = {(wp_id, out_id) for wp_id, wp in after.waypoints.items() for out_id in wp.outgoing}

        before_markers = {m.waypoint_id: (m.name, m.group) for m in before.markers}
        after_markers = {m.waypoint_id: (m.name, m.group) for m in after.markers}
        bm_ids = set(before_markers.keys())
        am_ids = set(after_markers.keys())

        return {
            "waypoints_added": wp_added,
            "waypoints_removed": wp_removed,
            "waypoints_changed": wp_changed,
            "routes_added": len(after_routes - before_routes),
            "routes_removed": len(before_routes - after_routes),
            "markers_added": len(am_ids - bm_ids),
            "markers_removed": len(bm_ids - am_ids),
            "markers_changed": len([wid for wid in (am_ids & bm_ids) if after_markers[wid] != before_markers[wid]]),
        }

    def _prepare_network_for_fs_export(self, network):
        if not network:
            return network, False

        ids_sorted = sorted(network.waypoints.keys())
        expected_ids = list(range(1, len(ids_sorted) + 1))
        if ids_sorted == expected_ids:
            return network, False

        id_map = {old_id: new_id for new_id, old_id in enumerate(ids_sorted, start=1)}
        export_network = RoadNetwork()
        export_network.map_name = network.map_name
        export_network.version = network.version
        export_network.route_version = network.route_version
        export_network.route_author = network.route_author

        for old_id in ids_sorted:
            src = network.waypoints[old_id]
            new_id = id_map[old_id]
            export_network.add_waypoint(
                Waypoint(
                    id=new_id,
                    x=src.x,
                    y=src.y,
                    z=src.z,
                    flag=src.flag,
                    outgoing=[id_map[o] for o in src.outgoing if o in id_map],
                    incoming=[id_map[i] for i in src.incoming if i in id_map],
                )
            )

        for marker in network.markers:
            if marker.waypoint_id in id_map:
                export_network.add_marker(
                    MapMarker(
                        waypoint_id=id_map[marker.waypoint_id],
                        name=marker.name,
                        group=marker.group
                    )
                )

        return export_network, True

    def _get_savegame_map_id(self, savegame_path):
        if not savegame_path or not os.path.isdir(savegame_path):
            return None

        xml_path = os.path.join(savegame_path, "careerSavegame.xml")
        if not os.path.isfile(xml_path):
            return None

        try:
            tree = ETree.parse(xml_path)
            root = tree.getroot()
            map_id_node = root.find(".//settings/mapId")
            if map_id_node is None or not map_id_node.text:
                return None
            return map_id_node.text.strip()
        except Exception:
            return None

    def OnPrefsClicked(self, event):
        dlg = SettingsDialog(self)
        dlg.ShowModal()

    def OnExitClicked(self, event):
        """Exit the application"""
        self.Close()
    
    def OnAddRoute(self, event):
        """Create a route between two selected waypoints."""
        selected_wp = list(self.mapCanvas.GetSelectedWaypoints())
        if len(selected_wp) != 2:
            return
        
        # Determine from -> to based on selection order if tracked, 
        # but here we just take them as they are from the set (unordered).
        # ideally the user selects start then end, but sets are unordered.
        # So we just create one way, and the user can swap direction if needed.
        # Actually, let's try to use the last added to set if we tracked it?
        # But we don't. So we just pick the first two.
        from_id, to_id = selected_wp[0], selected_wp[1]
        
        if self._dataMngr.add_route(from_id, to_id):
            # Select the new route and deselect waypoints
            self.mapCanvas.ClearSelection()
            self.mapCanvas.SelectRoute((from_id, to_id))
            self.mapCanvas.RefreshMapData()
            self._updateMainTitle()
            
            # Show status message
            self.SetStatusText(_("Created route: {0} -> {1}").format(from_id, to_id), 0)
        else:
            wx.MessageBox(_("Could not create route. Connection might already exist."), 
                         _("Error"), wx.OK | wx.ICON_ERROR)

    def OnAddMarker(self, event):
        """Add a marker to the selected waypoint."""
        selected = list(self.mapCanvas.GetSelectedWaypoints())
        if len(selected) != 1:
            return
            
        wp_id = selected[0]
        network = self._dataMngr.getRoadNetwork()
        if not network:
            return
            
        # Get existing groups
        groups = network.get_all_groups()
        
        # Open dialog
        dlg = MarkerDialog(self, title=_("Add Marker"), groups=groups)
        if dlg.ShowModal() == wx.ID_OK:
            name, group = dlg.GetValues()
            if name:
                self._dataMngr.add_marker(wp_id, name, group)
                self.mapCanvas.RefreshMapData()
                self._updateMainTitle()
        dlg.Destroy()

    def OnEditMarker(self, event):
        """Edit the marker of the selected waypoint."""
        selected = list(self.mapCanvas.GetSelectedWaypoints())
        if len(selected) != 1:
            return
            
        wp_id = selected[0]
        network = self._dataMngr.getRoadNetwork()
        if not network:
            return
            
        marker = network.get_marker_for_waypoint(wp_id)
        if not marker:
            return
            
        # Get existing groups
        groups = network.get_all_groups()
        
        # Open dialog
        dlg = MarkerDialog(self, title=_("Edit Marker"), name=marker.name, group=marker.group, groups=groups)
        if dlg.ShowModal() == wx.ID_OK:
            name, group = dlg.GetValues()
            if name:
                self._dataMngr.edit_marker(wp_id, name, group)
                self.mapCanvas.RefreshMapData()
                self._updateMainTitle()
        dlg.Destroy()

    def OnDelMarker(self, event):
        """Delete the marker of the selected waypoint."""
        selected = list(self.mapCanvas.GetSelectedWaypoints())
        if len(selected) != 1:
            return
            
        wp_id = selected[0]
        
        if wx.MessageBox(_("Are you sure you want to delete this marker?"), 
                        _("Confirm Delete"), wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self._dataMngr.remove_marker(wp_id)
            self.mapCanvas.RefreshMapData()
            self._updateMainTitle()

    def OnAboutClicked(self, event):
        """Handle the event when the about button is clicked."""
        dlg = AboutDialog(self)
        dlg.ShowModal()
    
    def OnUndoClicked(self, event):
        """Handle the event when the undo button is clicked."""
        if self._dataMngr.undo():
            self.mapCanvas.ClearSelection()
            self.mapCanvas.RefreshMapData()
            self._updateMainTitle()

    def OnRedoClicked(self, event):
        """Handle the event when the redo button is clicked."""
        if self._dataMngr.redo():
            self.mapCanvas.ClearSelection()
            self.mapCanvas.RefreshMapData()
            self._updateMainTitle()
    
    def OnDeleteSelection(self, event):
        """Handle deletion of selected items (waypoints and/or routes)."""
        selected_wp = self.mapCanvas.GetSelectedWaypoints()
        selected_rt = self.mapCanvas.GetSelectedRoutes()
        
        if not selected_wp and not selected_rt:
            wx.MessageBox(_("No items selected."), 
                         _("Delete"), wx.OK | wx.ICON_INFORMATION)
            return
        
        # Check if only routes are selected (no waypoints)
        intermediate_wp_to_delete = None
        orphan_wp_to_delete = None
        
        if selected_rt and not selected_wp:
            # Always find orphan endpoints that would have no connections left
            orphan_wp = self.mapCanvas._get_orphan_endpoints_from_routes(selected_rt)
            if orphan_wp:
                orphan_wp_to_delete = orphan_wp
            
            # Get intermediate waypoints from selected routes
            intermediate_wp = self.mapCanvas._get_intermediate_waypoints_from_routes(selected_rt)
            
            if intermediate_wp:
                # Ask user if they want to also delete intermediate waypoints
                msg = _("You are about to delete {0} route(s).\n\n").format(len(selected_rt))
                msg += _("{0} intermediate waypoint(s) are part of these routes.\n").format(len(intermediate_wp))
                
                # Add info about orphan endpoints if any
                if orphan_wp_to_delete:
                    msg += _("{0} endpoint waypoint(s) will become orphaned and will be deleted.\n\n").format(len(orphan_wp_to_delete))
                
                msg += _("Do you want to delete the intermediate waypoints as well?")
                
                dlg = wx.MessageDialog(self, msg, _("Delete Routes"), 
                                     wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                
                result = dlg.ShowModal()
                dlg.Destroy()
                
                if result == wx.ID_YES:
                    intermediate_wp_to_delete = intermediate_wp
            elif orphan_wp_to_delete:
                # No intermediate waypoints, but there are orphans - inform user
                msg = _("You are about to delete {0} route(s).\n\n").format(len(selected_rt))
                msg += _("{0} endpoint waypoint(s) will become orphaned and will be deleted automatically.").format(len(orphan_wp_to_delete))
                
                dlg = wx.MessageDialog(self, msg, _("Delete Routes"), 
                                     wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
        
        # Build confirmation message
        parts = []
        
        # Count waypoints to delete (selected + intermediate + orphan endpoints)
        total_wp = len(selected_wp)
        wp_details = []
        
        if selected_wp:
            wp_details.append(_("{0} selected").format(len(selected_wp)))
        
        if intermediate_wp_to_delete:
            total_wp += len(intermediate_wp_to_delete)
            wp_details.append(_("{0} intermediate").format(len(intermediate_wp_to_delete)))
        
        if orphan_wp_to_delete:
            total_wp += len(orphan_wp_to_delete)
            wp_details.append(_("{0} orphan").format(len(orphan_wp_to_delete)))
        
        if total_wp > 0:
            parts.append(_("{0} waypoint(s)").format(total_wp))
            if len(wp_details) > 1:
                # Add details if we have multiple types
                details_msg = ", ".join(wp_details)
                parts[-1] = _("{0} waypoint(s) ({1})").format(total_wp, details_msg)
        
        if selected_rt:
            parts.append(_("{0} route(s)").format(len(selected_rt)))
        
        msg = _("Delete {0}?").format(", ".join(parts))
        
        dlg = wx.MessageDialog(self, msg, _("Confirm Deletion"), 
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            removed_wp = 0
            removed_rt = 0
            
            # Delete routes first (before waypoints, since deleting waypoints also removes their routes)
            if selected_rt:
                removed_rt = self._dataMngr.remove_routes(list(selected_rt))
            
            # Combine all waypoints to delete: selected + intermediate + orphans
            wp_to_delete = list(selected_wp)
            if intermediate_wp_to_delete is not None:
                wp_to_delete.extend(intermediate_wp_to_delete)
            if orphan_wp_to_delete is not None:
                wp_to_delete.extend(orphan_wp_to_delete)
            
            if wp_to_delete:
                removed_wp = self._dataMngr.remove_waypoints(wp_to_delete)
            
            if removed_wp > 0 or removed_rt > 0:
                # Clear selection and refresh
                self.mapCanvas.ClearSelection()
                self.mapCanvas.RefreshMapData()
                self._updateMainTitle()
                
                # Build result message
                result_parts = []
                if removed_wp > 0:
                    result_parts.append(_("{0} waypoint(s)").format(removed_wp))
                if removed_rt > 0:
                    result_parts.append(_("{0} route(s)").format(removed_rt))
                wx.MessageBox(_("Successfully deleted {0}.").format(", ".join(result_parts)), 
                             _("Delete"), wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(_("Failed to delete selected items."), 
                             _("Error"), wx.OK | wx.ICON_ERROR)
        
        dlg.Destroy()
    
    def OnSwapRouteDirection(self, event):
        """Handle route direction swap from ribbon button."""
        selected = self.mapCanvas.GetSelectedRoutes()
        if not selected:
            wx.MessageBox(_("No routes selected."), 
                         _("Swap Direction"), wx.OK | wx.ICON_INFORMATION)
            return
        
        # selected is a set of tuples (from_id, to_id)
        new_routes = self._dataMngr.swap_selected_routes(list(selected))
        
        if new_routes:
            # Update selection with new valid routes
            self.mapCanvas.ClearSelection()
            for route in new_routes:
                self.mapCanvas.SelectRoute(route, add=True)
            
            # Refresh the map canvas
            self.mapCanvas.RefreshMapData()
            # Update window title to show modified state
            self._updateMainTitle()
            
            # Optional: Show status message instead of popup for better UX on frequent actions
            self.SetStatusText(_("Swapped direction for {0} route(s).").format(len(new_routes)))
        else:
            wx.MessageBox(_("Failed to swap route direction."), 
                         _("Error"), wx.OK | wx.ICON_ERROR)

    def OnZoomIn(self, event):
        """Handle Zoom In."""
        self.mapCanvas.ZoomIn()
        
    def OnZoomOut(self, event):
        """Handle Zoom Out."""
        self.mapCanvas.ZoomOut()
        
    def OnZoomReset(self, event):
        """Handle Reset Zoom."""
        self.mapCanvas.FitToWindow()
        
    def OnZoomWindow(self, event):
        """Handle Zoom Window mode."""
        self.mapCanvas.SetZoomWindowMode(True)
        self.SetStatusText(_("Click and drag to define zoom area"))
    
    def UpdateModifiedState(self):
        """Public method to update the window title and UI based on modified state."""
        self._updateMainTitle()

    def OnUpdateUI_Save(self, event):
        """Update UI state of the Save menu and toolbar item."""
        event.Enable(self._dataMngr.isModified())
    
    def OnUpdateUI_SaveAs(self, event):
        """Update UI state of the Save As menu and toolbar item."""
        event.Enable(self._dataMngr.isOk())
    
    def OnUpdateUI_ExportFS(self, event):
        """Update UI state of the Export to FS Savegame menu item."""
        event.Enable(self._dataMngr.isOk())
    
    def OnUpdateUI_RestoreFS(self, event):
        """Update UI state of the Restore from FS Savegame menu item."""
        event.Enable(self._dataMngr.isOk())
    
    def OnUpdateUI_Undo(self, event):
        """Update UI state of the Undo toolbar item."""
        event.Enable(self._dataMngr.can_undo())

    def OnUpdateUI_Redo(self, event):
        """Update UI state of the Redo toolbar item."""
        event.Enable(self._dataMngr.can_redo())
    
    def OnUpdateUI_Delete(self, event):
        """Update UI state of the Delete toolbar item."""
        event.Enable(self.mapCanvas.GetSelectionCount() > 0)
    
    def OnUpdateUI_SwapDir(self, event):
        """Update UI state of the Swap Direction toolbar item."""
        infos = self.mapCanvas.GetSelectionInfo()
        bEnable = (infos['total'] > 0) and (infos['routes'] > 0)
        event.Enable(bEnable)
    
    def OnUpdateUI_AddRoute(self, event):
        """Update UI state of the Add Route toolbar item."""
        infos = self.mapCanvas.GetSelectionInfo()
        bEnable = (infos['total'] == 2) and (infos['waypoints'] == 2)
        
        # If enabled so far, check if connection already exists
        if bEnable:
            selected = list(self.mapCanvas.GetSelectedWaypoints())
            network = self._dataMngr.getRoadNetwork()
            if network and len(selected) == 2:
                if network.has_any_connection(selected[0], selected[1]):
                    bEnable = False
        
        event.Enable(bEnable)
    
    def OnUpdateUI_AddMark(self, event):
        """Update UI state of the Add Marker toolbar item."""
        infos = self.mapCanvas.GetSelectionInfo()
        bEnable = (infos['total'] == 1) and (infos['waypoints'] == 1) and (infos['markers'] == 0)
        event.Enable(bEnable)
    
    def OnUpdateUI_EditMark(self, event):
        """Update UI state of the Edit Marker toolbar item."""
        infos = self.mapCanvas.GetSelectionInfo()
        bEnable = (infos['total'] == 1) and (infos['markers'] == 1)
        event.Enable(bEnable)
    
    def OnUpdateUI_DelMark(self, event):
        """Update UI state of the Del Marker toolbar item."""
        infos = self.mapCanvas.GetSelectionInfo()
        event.Enable(infos['markers'] > 0)
