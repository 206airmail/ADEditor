import os
from xml.etree.ElementTree import ElementTree, Element, SubElement
import xml.etree.ElementTree as ETree
import wx

Main_Frame_Min_Size = wx.Size(1024, 800)

def startupStringToPos(value):
    if value == "CenterScreen":
        return wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL
    if value == "LastKnownPos":
        return wx.ALIGN_NOT
    iHPos, iVPos = 0, 0
    if "Left" in value:
        iHPos = wx.LEFT
    elif "Right" in value:
        iHPos = wx.RIGHT
    else:
        iHPos = wx.ALIGN_CENTER_HORIZONTAL
    if "Top" in value:
        iVPos = wx.TOP
    elif "Bottom" in value:
        iVPos = wx.BOTTOM
    else:
        iVPos = wx.ALIGN_CENTER_VERTICAL

    return iHPos|iVPos

def startupPosToString(value):
    if value == (wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL):
        return "CenterScreen"
    if value == wx.ALIGN_NOT:
        return "LastKnownPos"
    sHPos, sVPos = "", ""
    if (value&wx.LEFT) == wx.LEFT:
        sHPos = "Left"
    elif (value&wx.RIGHT) == wx.RIGHT:
        sHPos = "Right"
    else:
        sHPos = "Center"
    if (value&wx.TOP) == wx.TOP:
        sVPos = "Top"
    elif (value&wx.BOTTOM) == wx.BOTTOM:
        sVPos = "Bottom"
    else:
        sVPos = "Center"
    return sVPos + sHPos

class SettingsManager(object):
    """
    Application settings/config manager
    Only one instance of this class is created, and every one can access it
    """
    _instance = None
    # Default settings
    _iStartPos = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL
    _ptStartPos = wx.DefaultPosition
    _szStartSize = Main_Frame_Min_Size
    _bSingleInstanceOnly = True
    _bProhibI18N = False
    # Other default values
    _bModified = False
    _sSettingsFName = "settings.xml"
    _sSettingsPath = ""
    # Other settings vars
    _lstRecentsFiles = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.Initialize()
            print("SettingsManager initialized ")
        return cls._instance

    def Initialize(self):
        """
        Singleton instance initialization
        All settings defined with their default values
        """
        self._bModified = False
        # Path for the settings file
        sCurrDir = os.getcwd()
        # If the settings file (settings.xml) exists in the base folder, then we use it
        if os.path.isfile(os.path.join(sCurrDir, self._sSettingsFName)):
            self._sSettingsPath = sCurrDir
        else:
            # Otherwise, we use the standard folder for this type of file.
            self._sSettingsPath = wx.StandardPaths.Get().GetUserDataDir()
        
    def _isModified(self):
        return self._bModified

    def SetModified(self):
        self._bModified = True
    
    def _getMainWndStartupPos(self):
        if self._iStartPos == wx.ALIGN_NOT:
            return self._iStartPos, self._ptStartPos

        return self._iStartPos, None
    
    def _setMainWndStartupPos(self, mode, pos=None):
        if mode != self._iStartPos:
            self._iStartPos = mode
            self._bModified = True
        if not pos is None:
            if pos != self._ptStartPos:
                self._ptStartPos = pos
                self._bModified = True
    
    def _getMainWndStartupRect(self):
        return wx.Rect(self._ptStartPos, self._szStartSize)
    
    def _setMainWndStartupRect(self, rect):
        if not rect == wx.Rect(self._ptStartPos, self._szStartSize):
            self._ptStartPos = rect.GetPosition()
            self._szStartSize = rect.GetSize()
            self._bModified = True
    
    def _getMainWndStartupSize(self):
        return self._szStartSize
    
    def _setMainWndStartupSize(self, size):
        if size != self._szStartSize:
            self._szStartSize = size
            self._bModified = True
    
    def _getMainWndMinSize(self):
        return Main_Frame_Min_Size
    
    def _getMultipleInstancesAllowed(self):
        return self._bSingleInstanceOnly is False

    def _setMultipleInstancesAllowed(self, value):
        if self._bSingleInstanceOnly == value:
            self._bSingleInstanceOnly = not value
            self._bModified = True
    
    def _setProhibitI18N(self, value):
        if not self._bProhibI18N == value:
            self._bProhibI18N = value
            self._bModified = True

    def _getProhibitI18N(self):
        return self._bProhibI18N
    
    def _getRecentFilesList(self):
        return self._lstRecentsFiles
    
    def _setRecentFilesList(self, list):
        if not len(list) == len(self._lstRecentsFiles):
            self._lstRecentsFiles = list.copy()
            self._bModified = True
        else:
            changed = False
            for f in list:
                if not f in self._lstRecentsFiles:
                    changed = True
            if not changed:
                for f in self._lstRecentsFiles:
                    if not f in list:
                        changed = True
            if changed:
                self._lstRecentsFiles = list.copy()
                self._bModified = True
    
    def _parseXmlNode(self, rootNode):
        # Read each xml entry
        for childNode in rootNode:
            nodeName = childNode.tag
            if nodeName == "StartupPos":
                self._iStartPos = startupStringToPos(childNode.get("Value", "CenterScreen"))
                iX = int(childNode.get("X", "-1"))
                iY = int(childNode.get("Y", "-1"))
                self._ptStartPos = wx.Point(iX, iY)
                iW = int(childNode.get("W", "-1"))
                iH = int(childNode.get("H", "-1"))
                self._szStartSize = wx.Size(iW, iH)
            elif nodeName == "MultiInstances":
                self._bSingleInstanceOnly = (childNode.text != "Allowed")
            elif nodeName == "Translation":
                self._bProhibI18N = (childNode.get("Allowed", "Yes") != "Yes")
            elif nodeName == "RecentFiles":
                self._lstRecentsFiles = []
                for entry in childNode:
                    if entry.tag == "Entry":
                        self._lstRecentsFiles.append(entry.text)

    def _createXmlNode(self):
        # Create the root node of the xml tree
        rootNode = Element("Settings-file")
        rootNode.set("Version", "1.0")

        # Position of the main window at application startup
        node = SubElement(rootNode, "StartupPos")
        node.set("Value", startupPosToString(self._iStartPos))
        iX, iY = self._ptStartPos.Get()
        iW, iH = self._szStartSize.Get()
        node.set("X", str(iX))
        node.set("Y", str(iY))
        node.set("W", str(iW))
        node.set("H", str(iH))

        # Allowing or not multiple instances of the application
        node = SubElement(rootNode, "MultiInstances")
        if self._bSingleInstanceOnly:
            node.text = "Not-Allowed"
        else:
            node.text = "Allowed"
        
        # Translation of the interface
        node = SubElement(rootNode, "Translation")
        if self._bProhibI18N:
            node.set("Allowed", "No")
        else:
            node.set("Allowed", "Yes")
        
        # Recents files list (if any)
        if len(self._lstRecentsFiles):
            node = SubElement(rootNode, "RecentFiles")
            for f in self._lstRecentsFiles:
                subnode = SubElement(node, "Entry")
                subnode.text = f

        return rootNode

    def ReadSettings(self):
        # Check whether the settings folder exists
        if not os.path.isdir(self._sSettingsPath):
            return
        # Construct the settings file name and check if it exists
        sFName = os.path.join(self._sSettingsPath, self._sSettingsFName)
        if not os.path.isfile(sFName):
            return
        # Try to load the xml settings file and read its content
        try:
            f = open(sFName, "rb")
            datas = f.read()
            f.close()

            tree = ElementTree(ETree.fromstring(datas.decode()))

            rootNode = tree.getroot()
            self._parseXmlNode(rootNode)
        except Exception as e:
            print(f"❌ Settings file read error: {e}")

    def SaveSettings(self):
        rootNode = self._createXmlNode()
        # Check if the settings folder exists
        if not os.path.isdir(self._sSettingsPath):
            os.makedirs(self._sSettingsPath)
        # Construct the settings file name and check if it exists
        sFName = os.path.join(self._sSettingsPath, self._sSettingsFName)
        if os.path.isfile(sFName):
            os.remove(sFName)
        # Save the new xml file
        ETree.indent(rootNode)
        tree = ElementTree(rootNode)
        tree.write(sFName, encoding="UTF-8", xml_declaration=True)

    Modified = property(_isModified)
    MainWndStartupPos = property(_getMainWndStartupPos, _setMainWndStartupPos)
    MainWndStartupSize = property(_getMainWndStartupSize, _setMainWndStartupSize)
    MainWndStartupRect = property(_getMainWndStartupRect, _setMainWndStartupRect)
    MainWndMinimalSize = property(_getMainWndMinSize)
    MultipleInstancesAllowed = property(_getMultipleInstancesAllowed, _setMultipleInstancesAllowed)
    ProhibitI18N = property(_getProhibitI18N, _setProhibitI18N)
    RecentFiles = property(_getRecentFilesList, _setRecentFilesList)
