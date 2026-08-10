# RTC-Tools QGIS Plugin (`RTC-Tools-QGIS-Plugin`)

A QGIS plugin for constructing, editing, and exporting RTC-Tools model network elements directly from the QGIS map canvas.

## Features

- **Map Interaction**: Add model elements (e.g. `Node`) by clicking directly on the QGIS map canvas.
- **QGIS Memory Layer**: Placed elements are displayed on a dedicated vector memory layer (`RTC-Tools Elements`) with custom styling and point labels.
- **Property Management**: View and edit element properties (ID, name, element type, coordinates, and custom key-value metadata) via a dedicated editor dialog or table view.
- **JSON Export / Import**: Save constructed models into a structured JSON file format or reload existing JSON models.

## Plugin Structure

```
RTC-Tools-QGIS-Plugin/
├── metadata.txt         # QGIS plugin metadata specification
├── __init__.py          # Plugin entry point (classFactory)
├── plugin.py            # Main plugin controller class (RTCToolsPlugin)
├── model_manager.py     # Layer management, element data, and JSON export/import
├── map_tool.py          # Custom QgsMapTool for canvas point selection
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
  "element_count": 1,
  "elements": [
    {
      "id": "node_1",
      "name": "Node 1",
      "type": "Node",
      "location": {
        "x": 4.8951,
        "y": 52.3702
      },
      "properties": {
        "description": "Initial control point"
      }
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
2. Select the **Element Type** (e.g. `Node`).
3. Click **📍 Add Element on Map**.
4. Click anywhere on the QGIS map canvas to place elements.
5. Select elements in the panel table to edit properties, delete, or clear all.
6. Click **💾 Save Model to JSON...** to export the model to a text JSON file.
