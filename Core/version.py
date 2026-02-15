import wx

_ = wx.GetTranslation

class AppVersion():
    def __init__(self):
        self.Major = 1
        self.Minor = 0
        self.Revision = 0
        self.Build = 60213

    def getVersion(self, full=False):
        sVers = str(self.Major) + "." + str(self.Minor) + '.' + str(self.Revision)
        if full is True:
            sVers += "." + str(self.Build)

        return sVers

    def getCopyright(self):
        sYear = " 202" + str(self.Build)[:1]
        return _("Copyright (c) X.P.") + " " + sYear

    def getAppName(self, short=False):
        if short:
            return "ADEditor"
        else:
            return _("AutoDriveEditor")

    def getAppDescription(self):
        return _("FS25 AutoDrive Datas Editor")

    def getMainWindowTitle(self):
        return self.getAppName() + " (v" + self.getVersion(False) + ") by X@v'"
