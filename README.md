# AutoDrive Editor

A user-friendly route editor for the AutoDrive mod of Farming Simulator 25.

## Overview

AutoDrive Editor is a complete rewrite of the original Java-based AutoDrive Course Editor, designed to provide a more intuitive and powerful experience for creating and editing AutoDrive routes in Farming Simulator 25.

### Main Features

- **Visual Route Editor**: Display and edit AutoDrive routes directly on the map overview
- **DDS Support**: Native DDS image reader (no external dependencies)
- **Heightmap Integration**: Automatic altitude calculation from heightmap data
- **Project Management**: Save/load projects with all map data included
- **Non-Destructive Editing**: Original savegame files remain untouched until explicit export
- **Zoom & Pan**: Smooth navigation with mouse wheel zoom and drag-to-pan
- **Route Validation**: Automatic detection of invalid connections and network issues

## License

Like the original Java version, this application does not have yet any license attached to it.

### Acknowledgments

- **DDSReader**: Based on [DDSReader.java](https://github.com/npedotnet/DDSReader) by Kenji Sasaki (MIT License), with improvements by [KillBait](https://github.com/KillBait/AutoDrive_Course_Editor)
- **AutoDrive Mod**: AutoDrive mod for Farming Simulator [GitHub](https://github.com/Stephan-S/FS25_AutoDrive)
- **Original Editor**: Java-based AutoDrive Course Editor as reference [GitHub](https://github.com/KillBait/AutoDrive_Course_Editor)

## To do
- **Help file**: Final User and translators manual
- **Check tool** for propagation mode when double-clic on a route segment
  * Option to make this selection persistent between sessions or not
- **Check box": do not show this dialog again on the "delete items" confirmation dialog
  * Option for restoring this (disabled dialogs ?)
- **Background image**: used when no project is loaded
- **Portable package**: a "ready to use" 7z package witch stores its settings in its running folder

### Planned Features

- **Backward routes**: Integrating backward segments ability
- **Connecting segments**: Creating a *curved* path (multi-waypoints) between 2 segments with start and end tangency
- **Waypoints alignment**
- **Traffic Data Integration**: Import existing road network from map to create routes quickly
- **Magnifying glass system** Facilitating selection when several items are located close to others
- **Advanced Route Tools**:
  - Auto-connect waypoints along roads
  - Bulk waypoint operations (move, delete, flag change)
  - Route templates and patterns
- **Route Validation**:
  - Detect unreachable waypoints
  - Find disconnected route segments
  - Identify routing loops
- **Import/Export Routes**: Share route networks with the community
- **Grid Snap**: Snap waypoints to grid for alignment
- **Route Statistics**: Total route length, waypoint count, marker distribution

## Changelog

### Version 1.0.0

- **Visual Route Editor**: Display and edit AutoDrive routes directly on the map overview
- **DDS image reader**: Native DDS format support without external dependencies
- **Heightmap integration**: Automatic altitude calculation from heightmap data
- **Project management**: Save and load projects with all map data included
- **Non-destructive editing**: Original savegame files remain untouched until explicit export
- **Navigation tools**: Smooth zoom and pan controls with mouse wheel support
- **Route validation**: Automatic detection of invalid connections and network issues
- **Marker management**: Create and edit route markers
- **Settings persistence**: User preferences and recent files management
- **Multilingual support**: French and English interface support but can be easily translated into other languages
- **Complete core architecture**: XML parsing, data management, and network processing

---

**Made with ❤️ for the Farming Simulator community**

