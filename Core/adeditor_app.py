import wx
from Core import SettingsManager, AppVersion
from Gui import MainFrame

class ADEditorApp(wx.App):

    def __init__(self, forcedLng=wx.LANGUAGE_DEFAULT):
        self._forcedLang = forcedLng
        self._locale = None
        wx.App.__init__(self)

    def OnInit(self):
        print("Running wxPython " + wx.version())
        v = AppVersion()
        self.SetAppName(v.getAppName(short=True))

        # Initialize the SettingsManager and read the settings file if any
        optMngr = SettingsManager()
        optMngr.ReadSettings()

        # Define the interface language if needed
        bI18N = optMngr.ProhibitI18N is False
        if wx.GetKeyState(wx.WXK_SHIFT) is True:
            bI18N = not bI18N

        if bI18N is True:
            self.InitLanguage()

        frm = MainFrame()
        self.SetTopWindow(frm)
        frm.Show()

        return True

    def OnExit(self):
        # Write the settings file if the options/config has been modified
        optMngr = SettingsManager()
        if optMngr.Modified:
            optMngr.SaveSettings()

        print("Exiting from a wxPython application")
        return wx.App.OnExit(self)
    
    def InitLanguage(self):
        wx.Locale.AddCatalogLookupPathPrefix("./langs")
        self._locale = wx.Locale()
        if self._locale.Init(self._forcedLang, ):
            print("Language initialized to " + self._locale.GetCanonicalName())
            self._locale.AddCatalog("adeditor")
        else:
            print("Unable to initialize language to " + self._locale.GetCanonicalName())
