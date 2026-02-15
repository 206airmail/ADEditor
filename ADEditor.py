import os
import sys
import wx
from Core import ADEditorApp

if sys.platform == 'darwin':
    def MyGetSystemLanguage():
        import locale
        loc, _ = locale.getlocale()
        return loc

if __name__ == "__main__":
    # Are we in a dev version (n ot frozen) ?
    isDev = getattr(sys, "frozen", False) is False
    #Check command line arguments
    args = sys.argv[1:]

    if isDev:
        # Be sure that the current directory is the one containing this script
        basePath, _ = os.path.split(__file__)
        os.chdir(basePath)
        if args:
            if args[0] == '--build':
                # Start building the Windows package with cx_Freeze
                from Tools.BuildPackage import BuildPackage
                sys.argv[1] = "build"
                BuildPackage()
                sys.exit(0)

    iLng = wx.LANGUAGE_DEFAULT
    if sys.platform == 'darwin':
        sLng = MyGetSystemLanguage()
        if not sLng is None:
            lInfo = wx.Locale.FindLanguageInfo(sLng)
            iLng = lInfo.Language

    app = ADEditorApp(forcedLng=iLng)

    app.MainLoop()
