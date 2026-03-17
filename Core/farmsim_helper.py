import os
import posixpath
from xml.etree.ElementTree import ElementTree, Element, SubElement
import xml.etree.ElementTree as ETree
import wx
import ctypes.wintypes
import zipfile
import tempfile
from Core.dds_reader import DDSReader
import io
import re
import winreg

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
        Try to find the Farming Simulator installation path for Steam and non-Steam installs.
        Returns a validated path or an empty string.
        """
        version = self._fs_version
        candidates = []

        # 1. Steam library candidates
        for library in self._getSteamLibraryPaths():
            candidates.append(os.path.join(library, "steamapps", "common", f"Farming Simulator {version}"))
            candidates.append(os.path.join(library, "steamapps", "common", f"FarmingSimulator{version}"))

        # 2. Registry uninstall candidates
        candidates.extend(self._getRegistryInstallCandidates())

        # 3. Common standalone install folders
        common_locations = [
            fr"C:\Program Files\Farming Simulator {version}",
            fr"C:\Program Files (x86)\Farming Simulator {version}",
            fr"C:\Games\Farming Simulator {version}",
            fr"D:\Games\Farming Simulator {version}",
            fr"E:\Games\Farming Simulator {version}",
            fr"F:\Games\Farming Simulator {version}",
            fr"G:\Games\Farming Simulator {version}",
        ]
        candidates.extend(common_locations)

        # Deduplicate while preserving order
        seen = set()
        unique_candidates = []
        for path in candidates:
            norm = os.path.normpath(path)
            if norm not in seen:
                seen.add(norm)
                unique_candidates.append(norm)

        for candidate in unique_candidates:
            if self._isValidFsInstall(candidate):
                return candidate

        return ""

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
        install_path = self.getFsBasePath()

        if "." not in map_id and install_path:
            base_maps_root = os.path.join(install_path, "data", "maps")

            candidates = [
                os.path.join(base_maps_root, map_id),
                os.path.join(base_maps_root, map_id[0].lower() + map_id[1:]) if map_id else None,
            ]

            for candidate in candidates:
                if candidate and os.path.isdir(candidate):
                    return candidate, False

        mod_zip_name = map_id.split('.')[0]

        zip_candidate = os.path.join(self.mods_path, f"{mod_zip_name}.zip")
        if os.path.isfile(zip_candidate):
            return zip_candidate, True

        folder_candidate = os.path.join(self.mods_path, mod_zip_name)
        if os.path.isdir(folder_candidate):
            return folder_candidate, False

        return None, False

    def extractMapImagesLocations(self, map_path, is_zip, log_func=None):
        try:
            self.overviewPath = None
            self.demPath = None

            if is_zip:
                with zipfile.ZipFile(map_path, "r") as zf:
                    # mod maps in zip always use modDesc.xml
                    with zf.open("modDesc.xml") as modDesc:
                        modDesctree = ETree.parse(modDesc)
                        modDescroot = modDesctree.getroot()

                    map_node = modDescroot.find(".//maps/map")
                    if map_node is None:
                        raise ValueError("Could not find <maps><map> in modDesc.xml")

                    mapxmlpath = map_node.get("configFilename")
                    if not mapxmlpath:
                        raise ValueError("configFilename missing in modDesc.xml")

                    mapxmlpath = mapxmlpath.replace("\\", "/")

                    with zf.open(mapxmlpath) as mapXML:
                        mapXMLtree = ETree.parse(mapXML)
                        mapXMLroot = mapXMLtree.getroot()

                    # root is usually already <map>
                    map_elem = mapXMLroot if mapXMLroot.tag == "map" else mapXMLroot.find(".//map")
                    if map_elem is None:
                        raise ValueError("Could not find <map> element in map XML")

                    filename_elem = map_elem.find("./filename")
                    mapi3dPath = filename_elem.text.strip() if filename_elem is not None and filename_elem.text else None
                    overview_raw = map_elem.get("imageFilename")

                    if not mapi3dPath:
                        raise ValueError("Could not find map i3d path in <map><filename>")

                    # In these map xml files, paths like maps/mapUS.i3d are already zip-root relative
                    mapi3dPath = mapi3dPath.replace("\\", "/")
                    self.overviewPath = overview_raw.replace("\\", "/") if overview_raw else None

                    with zf.open(mapi3dPath) as mapi3d:
                        mapi3dtree = ETree.parse(mapi3d)
                        mapi3droot = mapi3dtree.getroot()

                    dem_elem = mapi3droot.find('.//File[@fileId="1"]')
                    if dem_elem is None:
                        raise ValueError('No <File> element found with fileId="1"')

                    dem_relative_path = dem_elem.get("filename")
                    if not dem_relative_path:
                        raise ValueError('fileId="1" exists, but filename attribute is missing')

                    dem_relative_path = dem_relative_path.replace("\\", "/")
                    i3d_dir = posixpath.dirname(mapi3dPath)
                    self.demPath = posixpath.normpath(posixpath.join(i3d_dir, dem_relative_path))

            else:
                moddesc_path = os.path.join(map_path, "modDesc.xml")

                if os.path.isfile(moddesc_path):
                    # Unpacked mod map
                    modDesctree = ETree.parse(moddesc_path)
                    modDescroot = modDesctree.getroot()

                    map_node = modDescroot.find(".//maps/map")
                    if map_node is None:
                        raise ValueError("Could not find <maps><map> in modDesc.xml")

                    mapxml_rel = map_node.get("configFilename")
                    if not mapxml_rel:
                        raise ValueError("configFilename missing in modDesc.xml")

                    mapxml_full = os.path.normpath(os.path.join(map_path, mapxml_rel))

                else:
                    # Base-game map folder: go directly to the map XML inside the folder
                    xml_candidates = [
                        os.path.join(map_path, "map.xml"),
                        os.path.join(map_path, os.path.basename(map_path) + ".xml"),
                    ]

                    mapxml_full = None

                    for candidate in xml_candidates:
                        if os.path.isfile(candidate):
                            mapxml_full = candidate
                            break

                    if mapxml_full is None:
                        # fallback: scan xml files in folder and pick one whose root tag is <map>
                        for name in os.listdir(map_path):
                            if name.lower().endswith(".xml"):
                                candidate = os.path.join(map_path, name)
                                try:
                                    test_tree = ETree.parse(candidate)
                                    test_root = test_tree.getroot()
                                    if test_root.tag == "map":
                                        mapxml_full = candidate
                                        break
                                except Exception:
                                    continue

                    if mapxml_full is None:
                        raise ValueError("Could not find base-game map XML in map folder")

                mapXMLtree = ETree.parse(mapxml_full)
                mapXMLroot = mapXMLtree.getroot()

                map_elem = mapXMLroot if mapXMLroot.tag == "map" else mapXMLroot.find(".//map")
                if map_elem is None:
                    raise ValueError("Could not find <map> element in map XML")

                filename_elem = map_elem.find("./filename")
                mapi3d_rel = filename_elem.text.strip() if filename_elem is not None and filename_elem.text else None
                overview_rel = map_elem.get("imageFilename")

                if not mapi3d_rel:
                    raise ValueError("Could not find map i3d path in <map><filename>")

                # For folder maps, paths in map xml are relative to the map folder
                def resolve_game_path(path_value, base_folder, fs_data_path):
                    if not path_value:
                        return None

                    path_value = path_value.replace("/", os.sep).replace("\\", os.sep)

                    if path_value.startswith("$data" + os.sep):
                        return os.path.normpath(os.path.join(fs_data_path, path_value[len("$data" + os.sep):]))

                    if path_value.startswith("$data"):
                        return os.path.normpath(os.path.join(fs_data_path, path_value[len("$data"):].lstrip("\\/")))

                    return os.path.normpath(os.path.join(base_folder, path_value))

                mapi3d_full = resolve_game_path(mapi3d_rel, map_path, self.getFsDataPath())

                if overview_rel:
                    self.overviewPath = resolve_game_path(overview_rel, map_path, self.getFsDataPath())

                mapi3dtree = ETree.parse(mapi3d_full)
                mapi3droot = mapi3dtree.getroot()

                dem_elem = mapi3droot.find('.//File[@fileId="1"]')
                if dem_elem is None:
                    raise ValueError('No <File> element found with fileId="1"')

                dem_relative_path = dem_elem.get("filename")
                if not dem_relative_path:
                    raise ValueError('fileId="1" exists, but filename attribute is missing')

                i3d_dir = os.path.dirname(mapi3d_full)
                self.demPath = resolve_game_path(dem_relative_path, i3d_dir, self.getFsDataPath())

            return True

        except Exception as e:
            if log_func:
                log_func(f"Error parsing XML: {e}")
            else:
                print(f"Error parsing XML: {e}")
            return None
    # handle edge cases where one file extension is used in the xml but the actual file is a diff extention
    def resolve_zip_member_path(self, zf, xml_path, fallback_exts=(".dds", ".png", ".jpg")):
        """
        Return the first matching file inside the zip.

        Tries:
        1. exact path from XML
        2. same base name with fallback extensions

        Uses case-insensitive matching but returns the real zip member name.
        """
        if not xml_path:
            return None

        name_map = {name.lower(): name for name in zf.namelist()}

        # Try exact path first
        exact = name_map.get(xml_path.lower())
        if exact:
            return exact

        # Try alternate extensions
        base, _ = posixpath.splitext(xml_path)
        for ext in fallback_exts:
            candidate = base + ext
            match = name_map.get(candidate.lower())
            if match:
                return match

        return None

    def _load_image_size_from_bytes(self, file_path, file_data):
        """
        Return (width, height) for image bytes, or (None, None) on failure.
        Supports DDS and regular images.
        """
        try:
            if not file_path or not file_data:
                return None, None

            if file_path.lower().endswith(".dds"):
                with tempfile.NamedTemporaryFile(suffix=".dds", delete=False) as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name
                try:
                    wx_img = DDSReader.read_dds(tmp_path)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            else:
                stream = io.BytesIO(file_data)
                wx_img = wx.Image(stream)

            if wx_img and wx_img.IsOk():
                return wx_img.GetWidth(), wx_img.GetHeight()
        except Exception:
            pass

        return None, None

        def _choose_target_size(self, overview_size, dem_size, grass_size):
            """
            Use the size shared by any two of:
            - overview size
            - grass size
            - DEM size adjusted by -1 px in each dimension

            Fallback to adjusted DEM size if no pair matches.
            """
            adjusted_dem_size = None
            if dem_size and dem_size != (None, None):
                dem_w, dem_h = dem_size
                if dem_w and dem_h and dem_w > 1 and dem_h > 1:
                    adjusted_dem_size = (dem_w - 1, dem_h - 1)
                else:
                    adjusted_dem_size = dem_size

            sizes = [overview_size, adjusted_dem_size, grass_size]
            valid_sizes = [s for s in sizes if s and s != (None, None)]

            if len(valid_sizes) >= 2:
                counts = {}
                for s in valid_sizes:
                    counts[s] = counts.get(s, 0) + 1

                for size, count in counts.items():
                    if count >= 2:
                        return size

            return adjusted_dem_size if adjusted_dem_size and adjusted_dem_size != (None, None) else overview_size

    def _get_reference_image_size(self, is_zip, map_path, resolved_overview_path, overview_data, resolved_dem_path, dem_data):
        """
        Determine final target size by comparing overview, DEM, and grass01_weight.png.

        Rules:
        - if any 2 match, use that size
        - otherwise fallback to DEM size
        """
        overview_size = self._load_image_size_from_bytes(resolved_overview_path, overview_data)
        dem_size = self._load_image_size_from_bytes(resolved_dem_path, dem_data)
        grass_size = (None, None)

        try:
            if is_zip:
                with zipfile.ZipFile(map_path, "r") as zf:
                    dem_zip_path = resolved_dem_path.replace("\\", "/")
                    dem_dir = posixpath.dirname(dem_zip_path)
                    grass_path = posixpath.normpath(posixpath.join(dem_dir, "grass01_weight.png"))

                    grass_match = self.resolve_zip_member_path(
                        zf,
                        grass_path,
                        fallback_exts=(".png",)
                    )

                    if grass_match:
                        grass_data = zf.read(grass_match)
                        grass_size = self._load_image_size_from_bytes(grass_match, grass_data)

            else:
                dem_dir = os.path.dirname(resolved_dem_path)
                grass_path = os.path.join(dem_dir, "grass01_weight.png")

                if os.path.exists(grass_path):
                    with open(grass_path, "rb") as f:
                        grass_data = f.read()
                    grass_size = self._load_image_size_from_bytes(grass_path, grass_data)

        except Exception:
            pass

        return self._choose_target_size(overview_size, dem_size, grass_size)

    def _extractMapImages(self, map_path, is_zip, log_func=None):
        """
        Extract overview and heightmap images from map.
        Returns dictionary of wx.Image/wx.Bitmap
        """

        images = {
            "overview": None,
            "heightmap": None
        }

        overview_data = None
        heightmap_data = None
        resolved_overview_path = None
        resolved_dem_path = None
        target_w = None
        target_h = None

        locations_ok = self.extractMapImagesLocations(map_path, is_zip, log_func)
        if locations_ok is None:
            return {
                "overview": None,
                "heightmap": None
            }

        try:
            if is_zip:
                with zipfile.ZipFile(map_path, 'r') as zf:
                    # Resolve overview path from XML, with extension fallback
                    resolved_overview_path = self.resolve_zip_member_path(
                        zf,
                        self.overviewPath,
                        fallback_exts=(".dds", ".png", ".jpg")
                    )

                    if resolved_overview_path:
                        if log_func:
                            log_func(_("Found overview:") + f" {resolved_overview_path}")
                        overview_data = zf.read(resolved_overview_path)
                    else:
                        if log_func:
                            log_func(_("Overview file not found:") + f" {self.overviewPath}")

                    # Resolve DEM/heightmap path from i3d, with extension fallback
                    resolved_dem_path = self.resolve_zip_member_path(
                        zf,
                        self.demPath,
                        fallback_exts=(".png", ".dds", ".jpg")
                    )

                    if resolved_dem_path:
                        if log_func:
                            log_func(_("Found heightmap:") + f" {resolved_dem_path}")
                        heightmap_data = zf.read(resolved_dem_path)
                    else:
                        if log_func:
                            log_func(_("Heightmap file not found:") + f" {self.demPath}")

            else:
                # Folder structure
                overview_full_path = self.overviewPath if self.overviewPath else None
                dem_full_path = self.demPath if self.demPath else None

                def resolve_disk_path(path, fallback_exts):
                    if not path:
                        return None
                    if os.path.exists(path):
                        return path
                    base, _ = os.path.splitext(path)
                    for ext in fallback_exts:
                        candidate = base + ext
                        if os.path.exists(candidate):
                            return candidate
                    return None

                resolved_overview_path = resolve_disk_path(overview_full_path, (".dds", ".png", ".jpg"))
                resolved_dem_path = resolve_disk_path(dem_full_path, (".png", ".dds", ".jpg"))

                if resolved_overview_path:
                    if log_func:
                        log_func(_("Found overview:") + f" {resolved_overview_path}")
                    with open(resolved_overview_path, "rb") as f:
                        overview_data = f.read()

                if resolved_dem_path:
                    if log_func:
                        log_func(_("Found heightmap:") + f" {resolved_dem_path}")
                    with open(resolved_dem_path, "rb") as f:
                        heightmap_data = f.read()

            target_w, target_h = self._get_reference_image_size(
                is_zip,
                map_path,
                resolved_overview_path,
                overview_data,
                resolved_dem_path,
                heightmap_data
            )

            # Convert overview image
            if overview_data:
                is_dds = False
                if is_zip and resolved_overview_path.lower().endswith(".dds"):
                    is_dds = True
                elif not is_zip and resolved_overview_path.lower().endswith(".dds"):
                    is_dds = True

                if is_dds:
                    with tempfile.NamedTemporaryFile(suffix='.dds', delete=False) as tmp:
                        tmp.write(overview_data)
                        tmp_path = tmp.name

                    try:
                        wx_img = DDSReader.read_dds(tmp_path)
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                else:
                    stream = io.BytesIO(overview_data)
                    wx_img = wx.Image(stream)

                if wx_img and wx_img.IsOk():
                    w = wx_img.GetWidth()
                    h = wx_img.GetHeight()

                    self.overview_img_w = target_w if target_w else w
                    self.overview_img_h = target_h if target_h else h

                    crop_x = w // 4
                    crop_y = h // 4
                    crop_w = w // 2
                    crop_h = h // 2

                    cropped = wx_img.GetSubImage(wx.Rect(crop_x, crop_y, crop_w, crop_h))
                    if cropped.IsOk():
                        final_w = self.overview_img_w
                        final_h = self.overview_img_h
                        resized = cropped.Scale(final_w, final_h, wx.IMAGE_QUALITY_HIGH)
                        images["overview"] = resized
                        if log_func:
                            log_func(_("Overview cropped and resized"))
                    else:
                        images["overview"] = wx_img

            # Convert heightmap image
            if heightmap_data:
                is_dds = False
                if is_zip and resolved_dem_path.lower().endswith(".dds"):
                    is_dds = True
                elif not is_zip and resolved_dem_path.lower().endswith(".dds"):
                    is_dds = True

                if is_dds:
                    with tempfile.NamedTemporaryFile(suffix='.dds', delete=False) as tmp:
                        tmp.write(heightmap_data)
                        tmp_path = tmp.name

                    try:
                        wx_img = DDSReader.read_dds(tmp_path)
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                else:
                    stream = io.BytesIO(heightmap_data)
                    wx_img = wx.Image(stream)

                if wx_img and wx_img.IsOk():
                    w = wx_img.GetWidth()
                    h = wx_img.GetHeight()

                    crop_x = w // 4
                    crop_y = h // 4
                    crop_w = w // 2
                    crop_h = h // 2

                    cropped = wx_img.GetSubImage(wx.Rect(crop_x, crop_y, crop_w, crop_h))
                    if cropped.IsOk():
                        final_w = getattr(self, "overview_img_w", target_w if target_w else w)
                        final_h = getattr(self, "overview_img_h", target_h if target_h else h)
                        resized = cropped.Scale(final_w, final_h, wx.IMAGE_QUALITY_HIGH)
                        images["heightmap"] = resized
                        if log_func:
                            log_func(_("Heightmap was cropped and resized"))
                    else:
                        images["heightmap"] = wx_img

        except Exception as e:
            if log_func: log_func(f"Error extracting images: {e}")
            
        return images
