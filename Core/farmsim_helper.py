import os
from xml.etree.ElementTree import ElementTree, Element, SubElement
import xml.etree.ElementTree as ETree
import wx

_ = wx.GetTranslation

class FarmSimHelper(object):
    """
    Singleton class to help with Farming Simulator related tasks
    Only one instance of this class is created, and every one can access it
    """
    _instance = None
    # Farming Simulator related settings
    _known_fs_versions = [22, 25]
    _fs_version = 25
    _fs_base_path = ""
    _fs_data_path = ""
    _fs_user_path = ""

    def __new__(cls, version=25):
        if cls._instance is None:
            cls._instance = super(FarmSimHelper, cls).__new__(cls)
            cls._instance.Initialize(version)
            if version not in cls._known_fs_versions:
                print("⚠️ Warning: Unknown Farming Simulator version %d" % version)
            else:
                print("FarmSimHelper initialized with version %d" % version)
        return cls._instance

    def Initialize(self, version):
        """
        Singleton instance initialization
        """
        # Farming Simulator version
        self._fs_version = version
        # Default install directory based on version
        self._fs_base_path = self._findFsInstallPath()
        # Default data path
        self._fs_data_path = os.path.join(self._fs_base_path, "data")
        # Default user path
        self._fs_user_path = os.path.join(os.path.expanduser("~"), "Documents", "My Games", f"FarmingSimulator20{self._fs_version}")
        
    def _findFsInstallPath(self):
        """
        Try to find the Farming Simulator installation path based on the version
        """
        # For now, we just return the known path
        return f"G:/SteamLibrary/steamapps/common/Farming Simulator {self._fs_version}"
    
    def getFsVersion(self):
        """
        Return the Farming Simulator version actually used
        """
        return self._fs_version
    
    def getFsBasePath(self):
        """
        Return the Farming Simulator base installation path
        """
        return self._fs_base_path
    
    def getFsDataPath(self):
        """ 
        Return the Farming Simulator data path
        """
        return self._fs_data_path

    def getFsUserPath(self):
        """ 
        Return the Farming Simulator user path
        """
        return self._fs_user_path
    
    def isFS_Savegame(self, path):
        """
        Check if the given path is a valid Farming Simulator savegame folder
        """
        # A valid savegame folder should contain 'careerSavegame.xml' file
        savegame_file = os.path.join(path, "careerSavegame.xml")
        return os.path.isfile(savegame_file)

    def getMapFromSavegame(self, savegame_path, result_callback=None):
        """
        Extract map information from a savegame folder.
        
        Args:
            savegame_path: Path to the savegame folder
            result_callback: Optional callable to report progress/logs
            
        Returns:
            Dictionary with map info or None on failure
        """
        def log(msg):
            if result_callback:
                result_callback(msg)
            else:
                print(msg)

        log(_("Reading savegame data from:") + f" {savegame_path}")
        
        # 1. Parse careerSavegame.xml
        xml_path = os.path.join(savegame_path, "careerSavegame.xml")
        if not os.path.exists(xml_path):
            log(_("Error: careerSavegame.xml not found"))
            return None
            
        try:
            tree = ETree.parse(xml_path)
            root = tree.getroot()
            
            # Extract mapId (e.g., "FS25_New_American.SampleModMap" or "MapEU")
            map_id_node = root.find(".//settings/mapId")
            if map_id_node is None:
                log(_("Error: <mapId> tag not found in XML"))
                return None
                
            map_id = map_id_node.text
            map_title = root.find(".//settings/mapTitle").text if root.find(".//settings/mapTitle") is not None else "Unknown Map"
            
            log(_("Found Map ID:") + f" {map_id}")
            log(_("Map Title:") + f" {map_title}")
            
        except Exception as e:
            log(f"Error parsing XML: {e}")
            return None

        # 2. Locate the map
        map_path, is_zip = self._findMapPath(map_id)
        
        if not map_path:
            log(_("Error: Map not found in game data or mods folder:") + f" {map_id}")
            return None
            
        log(_("Map found at:") + f" {map_path} ({'ZIP' if is_zip else 'Folder'})")
        
        # 3. Extract images
        log(_("Extracting map images (this may take a while)..."))
        images = self._extractMapImages(map_path, is_zip, log)
        
        return {
            "mapId": map_id,
            "mapTitle": map_title,
            "path": map_path,
            "isZip": is_zip,
            "images": images
        }

    def _findMapPath(self, map_id):
        """
        Find the map path (folder or zip) based on mapId
        
        Returns:
            Tuple (path, is_zip) or (None, False)
        """
        # Case 1: Base game map (e.g., "MapEU")
        # Check in game install directory / data / maps
        if "." not in map_id:
            install_path = self.getFsBasePath()
            candidate = os.path.join(install_path, "data", "maps", map_id)
            if os.path.isdir(candidate):
                return candidate, False
            
            # Some base maps might be named differently in folder structure, 
            # but usually mapId matches folder name for base maps or it's standardized.
            # Let's try direct match first.
        
        # Case 2: Mod map (e.g., "FS25_Name.MapClass") -> FS25_Name.zip
        # The zip name is usually the first part before the dot
        mod_zip_name = map_id.split('.')[0]
        
        user_path = self.getFsUserPath()
        mods_path = os.path.join(user_path, "mods")
        
        # Check for ZIP file
        zip_candidate = os.path.join(mods_path, f"{mod_zip_name}.zip")
        if os.path.isfile(zip_candidate):
            return zip_candidate, True
            
        # Check for unpacked mod folder
        folder_candidate = os.path.join(mods_path, mod_zip_name)
        if os.path.isdir(folder_candidate):
            return folder_candidate, False
            
        return None, False

    def _extractMapImages(self, map_path, is_zip, log_func=None):
        """
        Extract overview and heightmap images from map.
        Returns dictionary of wx.Image/wx.Bitmap
        """
        from Core.dds_reader import DDSReader
        import zipfile
        
        images = {
            "overview": None,
            "heightmap": None
        }
        
        overview_data = None
        heightmap_data = None
        
        try:
            if is_zip:
                with zipfile.ZipFile(map_path, 'r') as zf:
                    # Search for overview.dds
                    for name in zf.namelist():
                        if name.lower().endswith("overview.dds"):
                            if log_func: log_func(_("Found overview:") + f" {name}")
                            # Extract to temporary buffer
                            overview_data = zf.read(name)
                            break
                            
                    # Search for heightmap
                    # Priority: infoLayer_dem.png > dem.png > heightmap.png
                    candidates = ["infolayer_dem.png", "dem.png", "heightmap.png"]
                    all_files = zf.namelist()
                    
                    for candidate in candidates:
                        for name in all_files:
                            if name.lower().endswith(candidate):
                                if log_func: log_func(_("Found heightmap:") + f" {name}")
                                heightmap_data = zf.read(name)
                                break
                        if heightmap_data: break
            else:
                # Folder structure
                # Recursive search for overview.dds
                for root, dirs, files in os.walk(map_path):
                    for file in files:
                        if file.lower() == "overview.dds":
                            full_path = os.path.join(root, file)
                            if log_func: log_func(_("Found overview:") + f" {full_path}")
                            with open(full_path, 'rb') as f:
                                overview_data = f.read()
                            break
                    if overview_data: break
                
                # Search for heightmap
                candidates = ["infoLayer_dem.png", "dem.png", "heightmap.png"]
                for candidate in candidates:
                    for root, dirs, files in os.walk(map_path):
                        for file in files:
                            if file.lower() == candidate:
                                full_path = os.path.join(root, file)
                                if log_func: log_func(_("Found heightmap:") + f" {full_path}")
                                with open(full_path, 'rb') as f:
                                    heightmap_data = f.read()
                                break
                        if heightmap_data: break
                    if heightmap_data: break

            # Convert images
            if overview_data:
                # Save temp file for DDSReader (it expects a path currently)
                # TODO: Update DDSReader to accept bytes stream directly would be better,
                # but for now we write to temp
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix='.dds', delete=False) as tmp:
                    tmp.write(overview_data)
                    tmp_path = tmp.name
                
                try:
                    wx_img = DDSReader.read_dds(tmp_path)
                    if wx_img and wx_img.IsOk():
                        # FS22/FS25: Crop to center 50% and resize to 2048x2048
                        # (Java: getSubimage(w/4, h/4, w/2, h/2) then scale to 2048x2048)
                        w = wx_img.GetWidth()
                        h = wx_img.GetHeight()
                        crop_x = w // 4
                        crop_y = h // 4
                        crop_w = w // 2
                        crop_h = h // 2
                        
                        cropped = wx_img.GetSubImage(wx.Rect(crop_x, crop_y, crop_w, crop_h))
                        if cropped.IsOk():
                            # Resize to 2048x2048
                            resized = cropped.Scale(2048, 2048, wx.IMAGE_QUALITY_HIGH)
                            images["overview"] = resized
                            if log_func: log_func(_("Overview cropped and resized to 2048x2048"))
                        else:
                            images["overview"] = wx_img
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            if heightmap_data:
                import io
                stream = io.BytesIO(heightmap_data)
                wx_img = wx.Image(stream)
                if wx_img.IsOk():
                    images["heightmap"] = wx_img
                    
        except Exception as e:
            if log_func: log_func(f"Error extracting images: {e}")
            
        return images