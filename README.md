# RTC-Tools QGIS Plugin (`RTC-Tools-QGIS-Plugin`)

A QGIS plugin for constructing, editing, and exporting RTC-Tools model network elements directly from the QGIS map canvas.

## Features

- **Supported Element Types**:
  - `Inflow` (1 output, upside-down triangle symbol)
  - `Level` (1 input, rectangle/square symbol)
  - `Reservoir` (1 inflow, 1 outflow, diamond symbol)
  - `Node` (junction point, circle symbol)
  - `Branch` (thick line connecting upstream element to downstream element)
- **Map Interaction**: Place elements on canvas and connect them with `Branch` lines (including topological validation).
- **QGIS Memory Layers**: Vector layers (`RTC-Tools Elements` and `RTC-Tools Branches`) with custom symbology and labels.
- **Property Management**: Edit properties, names, and custom key-value metadata.
- **JSON Export / Import**: Save network models with node locations and branch topology to JSON or reload existing JSON models.

## Plugin Structure

```
RTC-Tools-QGIS-Plugin/
├── metadata.txt         # QGIS plugin metadata specification
├── __init__.py          # Plugin entry point (classFactory)
├── plugin.py            # Main plugin controller class (RTCToolsPlugin)
├── model_manager.py     # Layer management, element data, topological validation, JSON export/import
├── map_tool.py          # Custom QgsMapTool for canvas point selection and line branch creation
├── dock_widget.py       # RTCToolsDockWidget UI panel
├── element_dialog.py    # Element properties editor dialog
├── icon.png             # Plugin toolbar icon
└── README.md            # Documentation
```

## JSON Model Output Format

When exporting via **Save Model to JSON...**, the plugin generates a JSON file structured as follows:

```json
{
  "model_type": "RTC-Tools Model",
  "version": "1.0",
  "crs": "EPSG:4326",
  "element_count": 3,
  "elements": [
    {
      "id": "inflow_1",
      "name": "Inflow 1",
      "type": "Inflow",
      "location": {
        "x": 4.8951,
        "y": 52.3702
      },
      "properties": {}
    },
    {
      "id": "level_1",
      "name": "Level 1",
      "type": "Level",
      "location": {
        "x": 4.9123,
        "y": 52.3811
      },
      "properties": {}
    },
    {
      "id": "branch_1",
      "name": "Branch 1",
      "type": "Branch",
      "from_element": "inflow_1",
      "to_element": "level_1",
      "upstream": "inflow_1",
      "downstream": "level_1",
      "properties": {}
    }
  ]
}
```

## How to Install in QGIS

1. Copy or link this folder (`RTC-Tools-QGIS-Plugin`) into your QGIS plugins directory:
   - **Windows**: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\RTC-Tools-QGIS-Plugin`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/RTC-Tools-QGIS-Plugin`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/RTC-Tools-QGIS-Plugin`
2. Open QGIS.
3. Go to **Plugins > Manage and Install Plugins... > Installed**.
4. Enable **RTC-Tools QGIS Plugin**.
5. Click the **RTC-Tools Model Builder** icon on the toolbar or access it under **Plugins > RTC-Tools**.

## Usage

1. Open the **RTC-Tools Model Builder** dock panel.
2. Choose an **Element Type** (`Inflow`, `Level`, `Reservoir`, `Node`).
3. Click **📍 Add Element on Map** and click canvas to place elements.
4. Select **Branch**, click **🔗 Connect Elements with Branch**, click the upstream element, then click the downstream element.
5. Edit, delete, or export your model to JSON via **💾 Save Model to JSON...**.
