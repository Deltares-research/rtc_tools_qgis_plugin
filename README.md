# RTC-Tools QGIS Plugin (`RTC-Tools-QGIS-Plugin`)

A QGIS plugin for constructing, editing, and exporting RTC-Tools model network elements directly from the QGIS map canvas.

## Features

- **Supported Element Types**:
  - `Inflow` (1 output, upside-down triangle symbol)
  - `Level` / `Terminal` (1 input, rectangle/square symbol; optional flow `min`, `max`, and `nominal` parameters)
  - `Reservoir` (1 inflow, 1 outflow, diamond symbol; optional volume `min`/`max`/`nominal`, and flow bounds for `Turbine`, `Spill`, and `Total Outflow`)
  - `Node` (junction point, circle symbol)
  - `Branch` (thick line connecting upstream element to downstream element)
- **Full RTC-Tools Model Package Construction**: Automatically scaffold complete RTC-Tools model project directory structures:
  - `<ModelName>.json` (JSON model file)
  - `<ModelName>/input/goal_table.csv` (goal table)
  - `<ModelName>/input/plot_table.csv` (plot configuration table)
  - `<ModelName>/input/rtcDataConfig.xml` (timeSeries mapping XML)
  - `<ModelName>/input/rtcParameterConfig.xml` (parameters XML)
  - `<ModelName>/input/timeseries_import.xml` (timeSeries event data XML)
  - `<ModelName>/model/<ModelName>.mo` (Modelica file)
  - `<ModelName>/src/<ModelName>.py` (Python optimization runner script)
  - `<ModelName>/output/` (empty output folder)
- **Modelica File Generation**: Construct RTC-Tools compatible Modelica (`*.mo`) files complete with:
  - Element declarations (`Node`, `Reservoir`, `Inflow`, `Terminal`, `Branch`)
  - Reservoir decision variables (`Q_turbine`, `Q_spill`) and state/flow outputs (`V`, `Q_out`)
  - Inflow boundary inputs (`<Inflow>_Inflow`)
  - Terminal/Level flow outputs (`<Terminal>_Q`)
  - Topological `connect()` equations and variable assignment statements
- **Map Interaction**: Place elements on canvas and connect them with `Branch` lines (including topological validation).
- **QGIS Memory Layers**: Vector layers (`RTC-Tools Elements` and `RTC-Tools Branches`) with custom symbology and labels.
- **Model Validation**: Check model topology against RTC-Tools connectivity rules:
  - `Inflow`: Exactly 1 output (0 inputs)
  - `Level`: Exactly 1 input (0 outputs)
  - `Reservoir`: Exactly 1 input and 1 output
  - `Node`: At least 1 input and exactly 1 output
  - `Branch`: Valid upstream and downstream connections
- **Collapsible Panel Sections**: Toggle between expand/collapse states for all dock panel sections ("Add Elements", "Model Elements", "Optimization Goals", "Model File") to optimize screen space.
- **Optimization Goal Table**:
  - Interactive Goal Table editor supporting all RTC-Tools goal parameters (`id`, `state`, `active`, `goal_type`, `function_min`, `function_max`, `function_nominal`, `target_data_type`, `target_min`, `target_max`, `priority`, `weight`, `order`, `Description`)
  - Auto-suggests state variable names from current model elements (e.g. `TroutLake_V`, `TroutLake_Q_out`)
  - Export & Import goals to/from RTC-Tools standard CSV format (`goal_table.csv`)
  - Full preservation of goal configuration inside exported and imported JSON model files
- **Plot Table Configuration**:
  - Interactive Plot Table editor supporting columns: `id`, `y_axis_title`, `variables_style_1`, `variables_style_2`, `custom_title`, `specified_in`
  - Auto-suggests Goal IDs from the Optimization Goal Table in a drop-down menu for the `id` column
  - Auto-suggests model state variables in drop-down menus for `variables_style_1` and `variables_style_2`
  - Validates unique `id` constraints and fixes `specified_in` to `goal_generator`
  - Export & Import plots to/from RTC-Tools standard CSV format (`plot_table.csv`)
  - Full preservation of plot configuration inside exported and imported JSON model files
- **Data Config Mapping (`rtcDataConfig.xml`)**:
  - Interactive table mapping model variables (`id`) to FEWS `locationId` and `parameterId`
  - Auto-suggests model variables from placed elements (e.g. `TroutLake_V`, `TroutLake_Q_out`)
  - Export & Import mappings to/from standard FEWS `rtcDataConfig.xml`
  - Full preservation of timeSeries mappings inside exported and imported JSON model files
- **Parameter Config (`rtcParameterConfig.xml`)**:
  - Interactive table managing model parameters (`id`, `name`, `type`, `value`)
  - Supports multiple FEWS parameter types (`double`, `integer`, `boolean`, `string`, `dateTime`) with correct XML tags (`<dblValue>`, `<intValue>`, `<boolValue>`, `<stringValue>`, `<dateTimeValue>`)
  - Export & Import parameter definitions to/from standard FEWS `rtcParameterConfig.xml`
  - Full preservation of parameter configuration inside exported and imported JSON model files
- **Model Execution & Results**:
  - Interactive **Model Run** section allowing selection of virtual environment Python executables.
  - Comprehensive pre-flight checks (JSON saved, project folders `input`, `model`, `src`, `output`, configuration CSVs/XMLs, `<ModelName>.mo`, `<ModelName>.py`, and `timeseries_import.xml`).
  - Runs optimization script and redirects logs to `output/rtc_tools_log.txt`.
  - Result view buttons: **Log Messages**, **Show Result Folder**, and **Show Final Result** (`output/figures/final_results.html`).
- **TimeSeries Import Data (`timeseries_import.xml`)**:
  - Tabbed editor for defining simulation TimeSteps (`datetimes`) and TimeSeries variable event data.
  - Supports both **nonequidistant** and **equidistant** timeStep modes (`unit` and `multiplier`).
  - Auto-suggests variable names and default `locationId`/`parameterId` headers from `rtcDataConfig.xml`.
  - Event values can be edited directly or imported per-variable from CSV files.
  - Export & Import definitions to/from FEWS `timeseries_import.xml`.
  - Full preservation of timeseries import configuration inside exported and imported JSON model files.
- **Property Management**: Edit properties, names, and custom key-value metadata.
- **JSON Export / Import**: Save network models with node locations and branch topology to JSON or reload existing JSON models.

## Plugin Structure

```
RTC-Tools-QGIS-Plugin/
├── metadata.txt                  # QGIS plugin metadata specification
├── __init__.py                   # Plugin entry point (classFactory)
├── plugin.py                     # Main plugin controller class (RTCToolsPlugin)
├── model_manager.py              # Layer management, element data, topological validation, JSON export/import
├── map_tool.py                   # Custom QgsMapTool for canvas point selection and line branch creation
├── dock_widget.py                # RTCToolsDockWidget UI panel
├── element_dialog.py             # Element properties editor dialog
├── goal_table_dialog.py          # Optimization Goal Table editor dialog
├── plot_table_dialog.py          # Plot Table editor dialog
├── rtc_data_config_dialog.py     # FEWS rtcDataConfig editor dialog
├── rtc_parameter_config_dialog.py# FEWS rtcParameterConfig editor dialog
├── icon.png                      # Plugin toolbar icon
└── README.md                     # Documentation
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
      "name": "Inflow 1",
      "type": "Inflow",
      "location": {
        "x": 4.8951,
        "y": 52.3702
      },
      "properties": {}
    },
    {
      "name": "Level 1",
      "type": "Level",
      "location": {
        "x": 4.9123,
        "y": 52.3811
      },
      "properties": {}
    },
    {
      "name": "Branch 1",
      "type": "Branch",
      "from_element": "Inflow 1",
      "to_element": "Level 1",
      "upstream": "Inflow 1",
      "downstream": "Level 1",
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
5. Click **🔍 Validate Model** to verify all input/output constraints.
6. Edit, delete, or export your model to JSON via **💾 Save Model to JSON...**.
