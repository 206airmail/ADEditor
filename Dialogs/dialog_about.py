import sys
import wx
from Graphx import mainImages
from Core import AppVersion

_ = wx.GetTranslation

class AboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title=wx.GetStockLabel(wx.ID_ABOUT, wx.STOCK_NOFLAGS))

        self._createInterface()

        self.CenterOnParent()

    def _createInterface(self):

        v = AppVersion()
        sTitle = wx.GetApp().GetAppName() + ' (v' + v.getVersion(True) + ')'

        sMsg = wx.version()
        pos = sMsg.find('wxWidgets')
        if pos != -1:
            sMsg = sMsg[:pos-1]
        sMsg = _('Made with') + ' wxPython ' + sMsg + '\n' + _('Based on') + ' Python ' + sys.version.split()[0] + ' ' + _('and') + ' ' + wx.GetLibraryVersionInfo().VersionString
        szrMain = wx.BoxSizer(wx.VERTICAL)

        szrTop = wx.BoxSizer(wx.HORIZONTAL)

        bmpCtrl = wx.StaticBitmap(self, wx.ID_ANY, wx.BitmapBundle.FromSVG(mainImages['appIcon.svg'], (150, 150)))
        szrTop.Add(bmpCtrl, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        szrRight = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, wx.ID_STATIC, sTitle)
        fntTitle = label.GetFont()
        fntTitle.MakeLarger()
        fntTitle.MakeBold()
        label.SetFont(fntTitle)
        szrRight.Add(label, 0, wx.ALL|wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC, v.getCopyright())
        szrRight.Add(label, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC, v.getAppDescription())
        szrRight.Add(label, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC, sMsg, style=wx.ST_NO_AUTORESIZE|wx.ALIGN_CENTER)
        szrRight.Add(label, 0, wx.ALL|wx.EXPAND, 5)

        szrTop.Add(szrRight, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        szrMain.Add(szrTop, 0, wx.ALL, 5)

        btnSzr = self.CreateSeparatedButtonSizer(wx.CLOSE)
        szrMain.Add(btnSzr, 0, wx.ALL|wx.EXPAND, 5)

        self.SetSizer(szrMain)

        szrMain.SetSizeHints(self)
