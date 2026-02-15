import sys
import os
import wx
from wx.svg import SVGimage
from Graphx import mainImages
from Core import FarmSimHelper, DatasManager

_ = wx.GetTranslation

class NewProjectDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title=wx.GetStockLabel(wx.ID_NEW, wx.STOCK_NOFLAGS))

        self._fsHelper = FarmSimHelper(25)

        self._noThumbSvg = SVGimage.CreateFromBytes(mainImages["noThumb.svg"])

        self._createInterface()
        sz = self.stBmpThumb.GetSize()
        imgSz = max(sz.width, sz.height)
        self.stBmpThumb.SetBitmap(self._noThumbSvg.ConvertToScaledBitmap(wx.Size(imgSz, imgSz), self))
        self.GetSizer().SetSizeHints(self)

        self._bindEvents()

        self.CenterOnParent()

    def _createInterface(self):
        szrMain = wx.BoxSizer(wx.VERTICAL)

        hszr = wx.BoxSizer(wx.HORIZONTAL)
        self.stBmpThumb = wx.StaticBitmap(self, bitmap=wx.NullBitmap)
        hszr.Add(self.stBmpThumb, 0, wx.ALL|wx.EXPAND, 5)

        colszr = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label=_("Reference FS25 Savegame:"))
        colszr.Add(label, 0, wx.BOTTOM, 1)
        lnszr = wx.BoxSizer(wx.HORIZONTAL)
        self.txtSavegame = wx.TextCtrl(self, size=(300, -1), style=wx.TE_READONLY)
        lnszr.Add(self.txtSavegame, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.btnBrwseSvGm = wx.Button(self, label=_("..."), style=wx.BU_EXACTFIT)
        lnszr.Add(self.btnBrwseSvGm, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        colszr.Add(lnszr, 0, wx.BOTTOM|wx.EXPAND, 5)

        label = wx.StaticText(self, label=_("Related FS25 map file:"))
        colszr.Add(label, 0, wx.BOTTOM, 1)
        lnszr = wx.BoxSizer(wx.HORIZONTAL)
        self.txtMapFile = wx.TextCtrl(self, style=wx.TE_READONLY)
        lnszr.Add(self.txtMapFile, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.btnBrwseMap = wx.Button(self, label=_("..."), style=wx.BU_EXACTFIT)
        lnszr.Add(self.btnBrwseMap, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        colszr.Add(lnszr, 0, wx.BOTTOM|wx.EXPAND, 5)

        label = wx.StaticText(self, label=_("AutoDrive datas file:"))
        colszr.Add(label, 0, wx.BOTTOM, 1)
        lnszr = wx.BoxSizer(wx.HORIZONTAL)
        self.txtADDatas = wx.TextCtrl(self, style=wx.TE_READONLY)
        lnszr.Add(self.txtADDatas, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.btnBrwseADDatas = wx.Button(self, label=_("..."), style=wx.BU_EXACTFIT)
        lnszr.Add(self.btnBrwseADDatas, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        colszr.Add(lnszr, 0, wx.BOTTOM|wx.EXPAND, 5)

        hszr.Add(colszr, 1, wx.ALL, 5)

        szrMain.Add(hszr, 0, wx.ALL|wx.EXPAND, 5)

        label = wx.StaticText(self, label=_("Savegame read results:"))
        szrMain.Add(label, 0, wx.LEFT|wx.RIGHT, 10)
        szrMain.AddSpacer(1)
        self.txtResults = wx.TextCtrl(self, size=(-1, 100), style=wx.TE_MULTILINE|wx.TE_READONLY)
        szrMain.Add(self.txtResults, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 10)
        #fnt = self.txtResults.GetFont()
        #fnt.SetFamily(wx.FONTFAMILY_TELETYPE)
        #self.txtResults.SetFont(fnt)

        btnSzr = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        szrMain.Add(btnSzr, 0, wx.ALL|wx.EXPAND, 5)

        self.SetSizer(szrMain)

        szrMain.SetSizeHints(self)

    def _bindEvents(self):
        self.btnBrwseSvGm.Bind(wx.EVT_BUTTON, self.OnBrowseSavegame)
        
        # Bind OK button (ID_OK is standard for Affirmative button in CreateSeparatedButtonSizer)
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=wx.ID_OK)
        
    def OnBrowseSavegame(self, event):
        bIsSavegame = False
        sStartPath = self._fsHelper.getFsUserPath()
        while bIsSavegame is not True:
            ddlg = wx.DirDialog(self, message=_("Select FS25 Savegame folder"), style=wx.DD_DEFAULT_STYLE|wx.DD_DIR_MUST_EXIST)
            ddlg.SetPath(sStartPath)
            if ddlg.ShowModal() == wx.ID_CANCEL:
                return
            savegamePath = ddlg.GetPath()
            
            if self._fsHelper.isFS_Savegame(savegamePath):
                bIsSavegame = True
                self.txtSavegame.SetValue(savegamePath)
                self.txtResults.AppendText(_("Valid FS25 savegame folder selected: %s\n") % savegamePath)
                
                # Start processing map data
                self.txtResults.AppendText(_("Analyzing savegame data...\n"))
                # Force UI update
                wx.GetApp().Yield()
                
                def update_results(msg):
                    self.txtResults.AppendText(f"  {msg}\n")
                    self.txtResults.ShowPosition(self.txtResults.GetLastPosition())
                    wx.GetApp().Yield()

                try:
                    busy = wx.BusyInfo(_("Analyzing savegame and converting map images...\nPlease wait, this may take a few moments."))
                    wx.BeginBusyCursor()
                    
                    self.map_info = self._fsHelper.getMapFromSavegame(savegamePath, result_callback=update_results)
                    
                    del busy
                finally:
                    wx.EndBusyCursor()
                
                if self.map_info:
                    self.txtResults.AppendText(_("Map analysis completed successfully!\n"))
                    self.txtMapFile.SetValue(self.map_info['path'])
                    
                    if self.map_info['images']['overview']:
                        img = self.map_info['images']['overview']
                        sz = self.stBmpThumb.GetSize()
                        imgSz = max(sz.width, sz.height)
                        if imgSz < 32: imgSz = 256
                        
                        w = img.GetWidth()
                        h = img.GetHeight()
                        aspect = w / h
                        
                        if w > h:
                            new_w = imgSz
                            new_h = int(imgSz / aspect)
                        else:
                            new_h = imgSz
                            new_w = int(imgSz * aspect)
                            
                        scaled_img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
                        self.stBmpThumb.SetBitmap(wx.Bitmap(scaled_img))
                        self.stBmpThumb.Refresh()
                    
                    ad_config_path = os.path.join(savegamePath, "AutoDrive_config.xml")
                    if os.path.exists(ad_config_path):
                        self.txtResults.AppendText(_("Found AutoDrive configuration file: %s\n") % "AutoDrive_config.xml")
                        self.txtADDatas.SetValue(ad_config_path)
                    else:
                        self.txtResults.AppendText(_("No AutoDrive configuration found (clean start).\n"))
                        self.txtADDatas.SetValue("")
                    
                else:
                    self.txtResults.AppendText(_("Failed to locate relevant map file.\n"))
                    wx.MessageBox(_("Could not locate the map file associated with this savegame.\nPlease check the mods folder or game installation."), 
                                 _("Map Not Found"), wx.OK | wx.ICON_ERROR)
            else:
                wx.MessageBox(_("The selected folder is not a valid FS25 savegame folder.\nMissing 'careerSavegame.xml'."), 
                             _("Invalid Savegame Folder"), wx.OK | wx.ICON_ERROR)

    def OnOK(self, event):
        # Validate data
        if not self.txtSavegame.GetValue() or not self.txtMapFile.GetValue():
            wx.MessageBox(_("Please select a valid savegame and ensure the map is loaded."), 
                         _("Incomplete Data"), wx.OK | wx.ICON_WARNING)
            return

        # Prepare DatasManager
        dm = DatasManager()
        
        # Set project name from map title (stored in helper or we can pass it via UI if we had a field)
        # Using a generic name + map name logic or prompting user
        # Requirement: "Ask user where to save project file, and its name"
        
        default_filename = "MyAutoDriveProject.adproject"
        if self.map_info['mapTitle']:
            default_filename = self.map_info['mapTitle'] + ".adproject"
        
        with wx.FileDialog(self, _("Save AutoDrive Editor Project"), wildcard="AutoDrive Project (*.adproject)|*.adproject",
                           defaultFile=default_filename,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # Return to dialog

            pathname = fileDialog.GetPath()
            
            # Setup DatasManager with current data before saving
            dm.setSavegamePath(self.txtSavegame.GetValue())
            dm.setMapPath(self.txtMapFile.GetValue())
            dm.setADConfigPath(self.txtADDatas.GetValue())
            
            # We need to transfer images from our internal logic to DatasManager.
            # Currently they are inside self._fsHelper internal state or we can grab them from stBmpThumb (scaled) or re-extract?
            # Better: getMapFromSavegame returned them in 'map_info'. We should have stored map_info.
            # I will assume we should store map_info in the class instance in OnBrowseSavegame
            
            if self.map_info:
                dm.setProjectName(self.map_info['mapTitle'])
                dm.setMapImages(self.map_info['images'])
            
            # Save the project
            if dm.saveProjectFile(pathname):
                wx.MessageBox(_("Project created and saved successfully!"), _("Success"), wx.OK | wx.ICON_INFORMATION)
                event.Skip() # Allow dialog to close normally
            else:
                wx.MessageBox(_("Failed to save project file."), _("Error"), wx.OK | wx.ICON_ERROR)
                # Do not close dialog
