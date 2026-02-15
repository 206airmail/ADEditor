"""
AutoDrive XML Parser

Parses AutoDrive_config.xml files and creates RoadNetwork objects.
Supports both old format (comma-separated) and new format (semicolon-separated).
"""

import xml.etree.ElementTree as ET
import re
from typing import Optional
from .network_data import Waypoint, MapMarker, RoadNetwork


def parse_autodrive_xml(source) -> Optional[RoadNetwork]:
    """
    Parse an AutoDrive config XML file or file-like object and return a RoadNetwork.
    
    Args:
        source: Path to the AutoDrive_config.xml file or a file-like object
        
    Returns:
        RoadNetwork object or None on error
    """
    try:
        tree = ET.parse(source)
        root = tree.getroot()
        
        network = RoadNetwork()
        
        # Read metadata
        version_elem = root.find('version')
        if version_elem is not None and version_elem.text:
            network.version = version_elem.text
        
        map_name_elem = root.find('MapName')
        if map_name_elem is not None and map_name_elem.text:
            network.map_name = map_name_elem.text
        
        route_version_elem = root.find('ADRouteVersion')
        if route_version_elem is not None and route_version_elem.text:
            network.route_version = route_version_elem.text
        
        route_author_elem = root.find('ADRouteAuthor')
        if route_author_elem is not None and route_author_elem.text:
            network.route_author = route_author_elem.text
        
        # Parse waypoints
        waypoints_elem = root.find('waypoints')
        has_incoming_data = False
        if waypoints_elem is not None:
            incoming_elem = waypoints_elem.find('incoming')
            if incoming_elem is None:
                incoming_elem = waypoints_elem.find('in')
            has_incoming_data = incoming_elem is not None and bool((incoming_elem.text or "").strip())
            _parse_waypoints(waypoints_elem, network)
        
        # Parse markers
        mapmarker_elem = root.find('mapmarker')
        if mapmarker_elem is not None:
            _parse_markers_old_format(mapmarker_elem, network)
        
        # Try new format markers
        markers_elem = root.find('markers')
        if markers_elem is not None:
            _parse_markers_new_format(markers_elem, network)
            
        # Recalculate only when missing from source XML.
        # This preserves original incoming ordering when data already exists.
        if not has_incoming_data:
            _recalculate_incoming(network)
        
        print(f"Loaded {len(network.waypoints)} waypoints and {len(network.markers)} markers")
        return network
        
    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
        return None
    except Exception as e:
        print(f"Error parsing AutoDrive XML: {e}")
        return None


def _parse_waypoints(waypoints_elem: ET.Element, network: RoadNetwork):
    """Parse waypoints from XML element."""
    
    # Check for 'c' attribute (new format with count)
    count_attr = waypoints_elem.get('c')
    
    # Get coordinate data
    id_elem = waypoints_elem.find('id')
    x_elem = waypoints_elem.find('x')
    y_elem = waypoints_elem.find('y')
    z_elem = waypoints_elem.find('z')
    out_elem = waypoints_elem.find('out')
    incoming_elem = waypoints_elem.find('incoming')
    if incoming_elem is None:
        incoming_elem = waypoints_elem.find('in')
    flags_elem = waypoints_elem.find('flags')
    
    if not all([x_elem is not None, y_elem is not None, z_elem is not None]):
        print(f"Warning: Missing coordinate data in waypoints. Found: x={x_elem is not None}, y={y_elem is not None}, z={z_elem is not None}")
        # Try to find case-insensitive or alternative names?
        return
    
    # Detect separator (semicolon for new format, comma for old)
    x_text = x_elem.text or ""
    separator = ';' if ';' in x_text else ','
    
    # Parse coordinates
    try:
        xs = [float(v) for v in x_text.split(separator) if v.strip()]
        ys = [float(v) for v in (y_elem.text or "").split(separator) if v.strip()]
        zs = [float(v) for v in (z_elem.text or "").split(separator) if v.strip()]
    except ValueError as e:
        print(f"Error parsing coordinates: {e}")
        return
    
    # Parse IDs (if present, otherwise generate 1, 2, 3...)
    if id_elem is not None and id_elem.text:
        # Convert to float first to handle "1.000" strings, then to int
        ids = [int(float(v)) for v in id_elem.text.split(separator) if v.strip()]
    else:
        ids = list(range(1, len(xs) + 1))
    
    # Parse flags
    flags = []
    if flags_elem is not None and flags_elem.text:
        flag_separator = ';' if ';' in flags_elem.text else ','
        flags = [int(float(v)) for v in flags_elem.text.split(flag_separator) if v.strip()]
    
    # Parse outgoing connections
    outgoing_lists = []
    if out_elem is not None and out_elem.text:
        for out_str in out_elem.text.split(';'):
            out_str = out_str.strip()
            if out_str == '-1' or not out_str:
                outgoing_lists.append([])
            else:
                outgoing_lists.append([int(float(v)) for v in out_str.split(',') if v.strip() and v.strip() != '-1'])
    
    # Parse incoming connections
    incoming_lists = []
    if incoming_elem is not None and incoming_elem.text:
        for in_str in incoming_elem.text.split(';'):
            in_str = in_str.strip()
            if in_str == '-1' or not in_str:
                incoming_lists.append([])
            else:
                incoming_lists.append([int(float(v)) for v in in_str.split(',') if v.strip() and v.strip() != '-1'])
    
    # Create waypoints
    for i in range(len(xs)):
        wp = Waypoint(
            id=ids[i] if i < len(ids) else i + 1,
            x=xs[i],
            y=ys[i] if i < len(ys) else 0.0,
            z=zs[i] if i < len(zs) else 0.0,
            flag=flags[i] if i < len(flags) else 0,
            outgoing=outgoing_lists[i] if i < len(outgoing_lists) else [],
            incoming=incoming_lists[i] if i < len(incoming_lists) else []
        )
        network.add_waypoint(wp)


def _parse_markers_old_format(mapmarker_elem: ET.Element, network: RoadNetwork):
    """Parse markers in old format (mm1, mm2, ...)."""
    for mm in mapmarker_elem:
        id_elem = mm.find('id')
        name_elem = mm.find('name')
        group_elem = mm.find('group')
        
        if id_elem is not None and id_elem.text and name_elem is not None and name_elem.text:
            try:
                marker = MapMarker(
                    waypoint_id=int(float(id_elem.text)),
                    name=name_elem.text,
                    group=group_elem.text if group_elem is not None and group_elem.text else "All"
                )
                network.add_marker(marker)
            except ValueError as e:
                print(f"Error parsing marker {mm.tag}: {e}")


def _parse_markers_new_format(markers_elem: ET.Element, network: RoadNetwork):
    """Parse markers in new format (<m i="1" n="Farm" g="All"/>)."""
    for m in markers_elem.findall('m'):
        wp_id = m.get('i')
        name = m.get('n')
        group = m.get('g', 'All')
        
        if wp_id and name:
            try:
                marker = MapMarker(
                    waypoint_id=int(float(wp_id)),
                    name=name,
                    group=group
                )
                network.add_marker(marker)
            except ValueError as e:
                print(f"Error parsing marker new format: {e}")


def save_autodrive_xml(network: RoadNetwork, filepath: str) -> bool:
    """
    Save a RoadNetwork to an AutoDrive config XML file.
    
    Args:
        network: The RoadNetwork to save
        filepath: Output file path
        
    Returns:
        True on success, False on error
    """
    try:
        root = ET.Element('AutoDrive')
        
        # Metadata
        ET.SubElement(root, 'version').text = network.version or "3.0.0.8"
        ET.SubElement(root, 'MapName').text = network.map_name
        ET.SubElement(root, 'ADRouteVersion').text = network.route_version or "no version defined"
        ET.SubElement(root, 'ADRouteAuthor').text = network.route_author or "no Author defined"
        
        # Waypoints
        if network.waypoints:
            waypoints_elem = ET.SubElement(root, 'waypoints')
            
            # Sort by ID
            sorted_wps = sorted(network.waypoints.values(), key=lambda wp: wp.id)
            
            ET.SubElement(waypoints_elem, 'id').text = ','.join(str(wp.id) for wp in sorted_wps)
            ET.SubElement(waypoints_elem, 'x').text = ','.join(f'{wp.x:.3f}' for wp in sorted_wps)
            ET.SubElement(waypoints_elem, 'y').text = ','.join(f'{wp.y:.3f}' for wp in sorted_wps)
            ET.SubElement(waypoints_elem, 'z').text = ','.join(f'{wp.z:.3f}' for wp in sorted_wps)
            
            # Outgoing
            out_strings = []
            for wp in sorted_wps:
                if not wp.outgoing:
                    out_strings.append('-1')
                else:
                    out_strings.append(','.join(str(o) for o in wp.outgoing))
            ET.SubElement(waypoints_elem, 'out').text = ';'.join(out_strings)
            
            # Incoming
            in_strings = []
            for wp in sorted_wps:
                if not wp.incoming:
                    in_strings.append('-1')
                else:
                    in_strings.append(','.join(str(i) for i in wp.incoming))
            ET.SubElement(waypoints_elem, 'incoming').text = ';'.join(in_strings)
            
            # Flags
            ET.SubElement(waypoints_elem, 'flags').text = ','.join(str(wp.flag) for wp in sorted_wps)
        
        # Markers
        if network.markers:
            mapmarker_elem = ET.SubElement(root, 'mapmarker')
            for i, marker in enumerate(network.markers, 1):
                mm = ET.SubElement(mapmarker_elem, f'mm{i}')
                ET.SubElement(mm, 'id').text = f"{float(marker.waypoint_id):.6f}"
                ET.SubElement(mm, 'name').text = marker.name
                ET.SubElement(mm, 'group').text = marker.group
        
        # Write in FS-like style (UTF-8 BOM + standalone + CRLF)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        _write_tree_preserving_format(tree, filepath, {
            "encoding": "utf-8",
            "bom": True,
            "standalone": "no",
            "newline": "\r\n",
        })
        
        print(f"Saved {len(network.waypoints)} waypoints to {filepath}")
        return True
        
    except Exception as e:
        print(f"Error saving AutoDrive XML: {e}")
        return False


def save_autodrive_xml_with_template(network: RoadNetwork, template_path: str, output_path: Optional[str] = None) -> bool:
    """
    Save a RoadNetwork by reusing an existing AutoDrive XML as template.
    This preserves non-network sections (settings, experimental features, etc.).

    Args:
        network: The RoadNetwork to save
        template_path: Existing AutoDrive_config.xml path
        output_path: Output file path (defaults to template_path)

    Returns:
        True on success, False on error
    """
    if output_path is None:
        output_path = template_path

    xml_format = _detect_xml_format(template_path)

    try:
        tree = ET.parse(template_path)
        root = tree.getroot()
    except Exception:
        # Fallback to standard writer when no usable template is available.
        return save_autodrive_xml(network, output_path)

    try:
        _set_or_create(root, 'version', network.version or "3.0.0.8")
        _set_or_create(root, 'MapName', network.map_name or "")
        _set_or_create(root, 'ADRouteVersion', network.route_version or "no version defined")
        _set_or_create(root, 'ADRouteAuthor', network.route_author or "no Author defined")

        _write_waypoints_like_template(root, network)
        _write_markers_like_template(root, network)

        _write_tree_preserving_format(tree, output_path, xml_format)
        print(f"Saved {len(network.waypoints)} waypoints to {output_path} (template mode)")
        return True
    except Exception as e:
        print(f"Error saving AutoDrive XML in template mode: {e}")
        return False


def _recalculate_incoming(network: RoadNetwork):
    """
    Rebuild incoming connection lists based on outgoing connections.
    This ensures topological consistency even if XML 'incoming' data is missing or wrong.
    """
    # Clear existing incoming lists
    for wp in network.waypoints.values():
        wp.incoming = []
        
    # Rebuild from outgoing
    for wp_id, wp in network.waypoints.items():
        for out_id in wp.outgoing:
            target_wp = network.get_waypoint(out_id)
            if target_wp:
                if wp_id not in target_wp.incoming:
                    target_wp.incoming.append(wp_id)


def _set_or_create(root: ET.Element, tag: str, text: str) -> ET.Element:
    elem = root.find(tag)
    if elem is None:
        elem = ET.SubElement(root, tag)
    elem.text = text
    return elem


def _write_waypoints_like_template(root: ET.Element, network: RoadNetwork):
    waypoints_elem = root.find('waypoints')
    if waypoints_elem is None:
        waypoints_elem = ET.SubElement(root, 'waypoints')

    sorted_wps = sorted(network.waypoints.values(), key=lambda wp: wp.id)

    x_elem_existing = waypoints_elem.find('x')
    coord_sep = ';' if (x_elem_existing is not None and (x_elem_existing.text or '').find(';') >= 0) else ','

    flags_elem_existing = waypoints_elem.find('flags')
    if flags_elem_existing is not None and (flags_elem_existing.text or '').find(';') >= 0:
        flags_sep = ';'
    else:
        flags_sep = coord_sep

    has_count_attr = 'c' in waypoints_elem.attrib

    id_elem = waypoints_elem.find('id')
    x_elem = waypoints_elem.find('x')
    if x_elem is None:
        x_elem = ET.SubElement(waypoints_elem, 'x')
    y_elem = waypoints_elem.find('y')
    if y_elem is None:
        y_elem = ET.SubElement(waypoints_elem, 'y')
    z_elem = waypoints_elem.find('z')
    if z_elem is None:
        z_elem = ET.SubElement(waypoints_elem, 'z')
    out_elem = waypoints_elem.find('out')
    if out_elem is None:
        out_elem = ET.SubElement(waypoints_elem, 'out')
    in_elem = waypoints_elem.find('in')
    incoming_elem = waypoints_elem.find('incoming')

    use_in_tag = in_elem is not None
    if use_in_tag:
        in_out_elem = in_elem
    elif incoming_elem is not None:
        in_out_elem = incoming_elem
    else:
        in_out_elem = ET.SubElement(waypoints_elem, 'incoming')

    if id_elem is not None:
        id_elem.text = coord_sep.join(str(wp.id) for wp in sorted_wps)
    x_elem.text = coord_sep.join(f'{wp.x:.3f}' for wp in sorted_wps)
    y_elem.text = coord_sep.join(f'{wp.y:.3f}' for wp in sorted_wps)
    z_elem.text = coord_sep.join(f'{wp.z:.3f}' for wp in sorted_wps)

    out_strings = []
    in_strings = []
    for wp in sorted_wps:
        out_strings.append(','.join(str(o) for o in wp.outgoing) if wp.outgoing else '-1')
        in_strings.append(','.join(str(i) for i in wp.incoming) if wp.incoming else '-1')

    out_elem.text = ';'.join(out_strings)
    in_out_elem.text = ';'.join(in_strings)
    flags_elem = waypoints_elem.find('flags')
    if flags_elem is None:
        flags_elem = ET.SubElement(waypoints_elem, 'flags')
    flags_elem.text = flags_sep.join(str(wp.flag) for wp in sorted_wps)

    if has_count_attr:
        waypoints_elem.set('c', str(len(sorted_wps)))


def _write_markers_like_template(root: ET.Element, network: RoadNetwork):
    had_new = root.find('markers') is not None
    had_old = root.find('mapmarker') is not None

    for child in list(root):
        if child.tag in ('markers', 'mapmarker'):
            root.remove(child)

    prefer_new = had_new and not had_old

    if prefer_new:
        markers_elem = ET.SubElement(root, 'markers')
        for marker in network.markers:
            m = ET.SubElement(markers_elem, 'm')
            m.set('i', str(marker.waypoint_id))
            m.set('n', marker.name)
            m.set('g', marker.group)
        # Keep root closing tag on its own line when this is the last section.
        markers_elem.tail = "\n"
        _sync_groups_if_present(root, network)
    else:
        mapmarker_elem = ET.SubElement(root, 'mapmarker')
        if network.markers:
            mapmarker_elem.text = "\n        "
        marker_count = len(network.markers)
        for i, marker in enumerate(network.markers, 1):
            mm = ET.SubElement(mapmarker_elem, f'mm{i}')
            mm.text = "\n            "

            id_elem = ET.SubElement(mm, 'id')
            id_elem.text = f"{float(marker.waypoint_id):.6f}"
            id_elem.tail = "\n            "

            name_elem = ET.SubElement(mm, 'name')
            name_elem.text = marker.name
            name_elem.tail = "\n            "

            group_elem = ET.SubElement(mm, 'group')
            group_elem.text = marker.group
            group_elem.tail = "\n        "

            if i < marker_count:
                mm.tail = "\n        "
            else:
                mm.tail = "\n    "
        # Keep root closing tag on its own line when this is the last section.
        mapmarker_elem.tail = "\n"


def _sync_groups_if_present(root: ET.Element, network: RoadNetwork):
    groups_elem = root.find('groups')
    if groups_elem is None:
        return

    for child in list(groups_elem):
        groups_elem.remove(child)

    names = []
    seen = set()
    for marker in network.markers:
        grp = marker.group or "All"
        if grp not in seen:
            names.append(grp)
            seen.add(grp)

    if "All" in seen:
        names = ["All"] + [n for n in names if n != "All"]
    else:
        names = ["All"] + names

    for idx, name in enumerate(names, 1):
        g = ET.SubElement(groups_elem, 'g')
        g.set('n', name)
        g.set('i', str(idx))


def _detect_xml_format(path: str):
    fmt = {
        "encoding": "utf-8",
        "bom": False,
        "standalone": None,
        "newline": "\n",
        "trailing_newlines": 0,
    }
    try:
        raw = open(path, "rb").read()
    except Exception:
        return fmt

    fmt["bom"] = raw.startswith(b"\xef\xbb\xbf")
    if b"\r\n" in raw:
        fmt["newline"] = "\r\n"

    head = raw[:512].decode("utf-8", errors="ignore")
    m_enc = re.search(r'encoding\s*=\s*["\']([^"\']+)["\']', head, flags=re.IGNORECASE)
    if m_enc:
        fmt["encoding"] = m_enc.group(1)
    m_std = re.search(r'standalone\s*=\s*["\']([^"\']+)["\']', head, flags=re.IGNORECASE)
    if m_std:
        fmt["standalone"] = m_std.group(1)

    nl = fmt["newline"].encode("ascii")
    trailing = 0
    pos = len(raw)
    while pos >= len(nl) and raw[pos - len(nl):pos] == nl:
        trailing += 1
        pos -= len(nl)
    fmt["trailing_newlines"] = trailing
    return fmt


def _write_tree_preserving_format(tree: ET.ElementTree, output_path: str, fmt):
    encoding = fmt.get("encoding", "utf-8")
    newline = fmt.get("newline", "\n")
    standalone = fmt.get("standalone")
    use_bom = bool(fmt.get("bom"))
    trailing_newlines = int(fmt.get("trailing_newlines", 0))

    root = tree.getroot()
    body_bytes = ET.tostring(root, encoding=encoding)
    body_text = body_bytes.decode(encoding, errors="strict")
    body_text = body_text.replace("\r\n", "\n").replace("\n", newline)

    decl = f'<?xml version="1.0" encoding="{encoding}"'
    if standalone is not None:
        decl += f' standalone="{standalone}"'
    decl += "?>"

    full_text = decl + newline + body_text
    if trailing_newlines > 0:
        full_text = full_text.rstrip("\r\n") + (newline * trailing_newlines)

    out_bytes = full_text.encode(encoding)
    if use_bom and encoding.lower().replace("_", "-") == "utf-8":
        out_bytes = b"\xef\xbb\xbf" + out_bytes

    with open(output_path, "wb") as f:
        f.write(out_bytes)
