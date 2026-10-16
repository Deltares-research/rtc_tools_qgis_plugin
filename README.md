# RTC-Tools QGIS Plugin (`RTC-Tools-QGIS-Plugin`)

A QGIS plugin providing a graphical user interface (GUI) for constructing, editing, and exporting [RTC-Tools](https://rtc-tools.readthedocs.io/) models directly from the QGIS map canvas.

## About RTC-Tools

[RTC-Tools](https://rtc-tools.readthedocs.io/) (Real-Time Control Tools) is an open-source optimization and simulation package for operational water management and multi-energy systems, hosted under [LF Energy](https://www.lfenergy.org/) (a [Linux Foundation](https://www.linuxfoundation.org/) project) and originally developed by [Deltares](https://www.deltares.nl/). It enables model-predictive control, rule-based control, and decision support using Modelica and Python.

This QGIS plugin provides a spatial and visual interface (GUI) to:
- Visually lay out water network topologies (inflows, reservoirs, nodes, terminals, and branches).
- Configure optimization goals, plot definitions, and FEWS data/parameter mappings.
- Automatically generate the complete directory structure, Modelica model (`*.mo`), and Python runner script for RTC-Tools simulations.
- Run optimizations and view results directly from QGIS.

## Features

- **Supported Element Types**:
  - `Inflow` (1 output, upside-down triangle symbol)
  - `Level` / `Terminal` (1 input, rectangle/square symbol; optional flow `min`, `max`, and `nominal` parameters)
  - `Reservoir` (1 inflow, 1 outflow, diamond symbol; optional volume `min`/`max`/`nominal`, and flow bounds for `Turbine`, `Spill`, and `Total Outflow`)
  - `Node` (junction point, circle symbol)
  - `Branch` (thick line connecting upstream element to downstream element)
- **Full RTC-Tools Model Package Construction**: Automatically scaffold complete RTC-Tools model project directory structures inside `<WorkingFolder>/<ModelName>/`:
  - `<WorkingFolder>/<ModelName>/<ModelName>.json` (JSON model file)
  - `<WorkingFolder>/<ModelName>/input/goal_table.csv` (goal table)
  - `<WorkingFolder>/<ModelName>/input/plot_table.csv` (plot configuration table)
  - `<WorkingFolder>/<ModelName>/input/rtcDataConfig.xml` (timeSeries mapping XML)
  - `<WorkingFolder>/<ModelName>/input/rtcParameterConfig.xml` (parameters XML)
  - `<WorkingFolder>/<ModelName>/input/timeseries_import.xml` (timeSeries event data XML)
  - `<WorkingFolder>/<ModelName>/model/<ModelName>.mo` (Modelica file)
  - `<WorkingFolder>/<ModelName>/src/<ModelName>.py` (Python optimization runner script)
  - `<WorkingFolder>/<ModelName>/output/` (empty output folder)
- **Modelica File Generation**: Construct RTC-Tools compatible Modelica (`*.mo`) files complete with:
  - Element declarations (`Node`, `Reservoir`, `Inflow`, `Terminal`, `Branch`)
  - Reservoir decision variables (`Q_turbine`, `Q_spill`) and state/flow outputs (`V`, `Q_out`)
  - Inflow boundary inputs (`<Inflow>_Inflow`)
  - Terminal/Level flow outputs (`<Terminal>_Q`)
  - Topological `connect()` equations and variable assignment statements
- **Map Interaction & Node Relocation**:
  - Place elements on canvas and connect them with `Branch` lines (including topological validation).
  - Interactively move any node/element on the canvas using the **✋ Move Element on Map** tool (supports click-and-drag as well as two-click pick-and-place with live rubber band previews).
  - Relocating a node automatically stretches and updates all connected incoming and outgoing branch lines in real time.
  - Nodes can also be moved from the table using the **Move** button or by directly editing their X and Y coordinates in the element properties dialog.
- **QGIS Memory Layers**: Vector layers (`RTC-Tools Elements` and `RTC-Tools Branches`) with custom symbology and labels.
- **Model Validation**: Check model topology against RTC-Tools connectivity rules:
  - `Inflow`: Exactly 1 output (0 inputs)
  - `Level`: Exactly 1 input (0 outputs)
  - `Reservoir`: Exactly 1 input and 1 output
  - `Node`: At least 1 input and exactly 1 output
  - `Branch`: Valid upstream and downstream connections
- **Collapsible Panel Sections**: Toggle between expand/collapse states for all dock panel sections ("Model File", "Elements", "Model Elements", "Optimization Goals", "Plot Configuration", "Data Config Mapping", "Parameter Config", "TimeSeries Import Data", and "Model Construction and Run") to optimize screen space.
- **Model File Management**:
  - Dedicated **Model File** section at the top of the dock panel for setting the **Model Name** (validated as a valid Python/Modelica identifier) and **Working Folder** once, avoiding repetitive prompts on subsequent save or model construction actions.
  - Supports **🔍 Validate Model**, **💾 Save**, **💾➕ Save as**, **📂 Open**, and **❌ Close** (to cleanly close the current model before starting or opening another).
- **Optimization Goal Table**:
  - Interactive Goal Table editor supporting all RTC-Tools goal parameters (`id`, `state`, `active`, `goal_type`, `function_min`, `function_max`, `function_nominal`, `target_data_type`, `target_min`, `target_max`, `priority`, `weight`, `order`, `Description`)
  - Auto-suggests state variable names from current model elements (e.g. `TroutLake_V`, `TroutLake_Q_out`)
  - Import & Export goals to/from RTC-Tools standard CSV format (`goal_table.csv`)
  - Full preservation of goal configuration inside exported and imported JSON model files
- **Plot Table Configuration**:
  - Interactive Plot Table editor supporting columns: `id`, `y_axis_title`, `variables_style_1`, `variables_style_2`, `custom_title`, `specified_in`
  - Auto-suggests Goal IDs from the Optimization Goal Table in a drop-down menu for the `id` column
  - Auto-suggests model state variables in drop-down menus for `variables_style_1` and `variables_style_2`
  - Validates unique `id` constraints and fixes `specified_in` to `goal_generator`
  - Import & Export plots to/from RTC-Tools standard CSV format (`plot_table.csv`)
  - Full preservation of plot configuration inside exported and imported JSON model files
- **Data Config Mapping (`rtcDataConfig.xml`)**:
  - Interactive table mapping model variables (`id`) to FEWS `locationId` and `parameterId`
  - Auto-suggests model variables from placed elements (e.g. `TroutLake_V`, `TroutLake_Q_out`)
  - Import & Export mappings to/from standard FEWS `rtcDataConfig.xml`
  - Full preservation of timeSeries mappings inside exported and imported JSON model files
- **Parameter Config (`rtcParameterConfig.xml`)**:
  - Interactive table managing model parameters (`id`, `name`, `type`, `value`)
  - Supports multiple FEWS parameter types (`double`, `integer`, `boolean`, `string`, `dateTime`) with correct XML tags (`<dblValue>`, `<intValue>`, `<boolValue>`, `<stringValue>`, `<dateTimeValue>`)
  - Import & Export parameter definitions to/from standard FEWS `rtcParameterConfig.xml`
  - Full preservation of parameter configuration inside exported and imported JSON model files
- **TimeSeries Import Data (`timeseries_import.xml`)**:
  - Tabbed editor for defining simulation TimeSteps (`datetimes`) and TimeSeries variable event data.
  - Supports both **nonequidistant** and **equidistant** timeStep modes (`unit` and `multiplier`).
  - Auto-suggests variable names and default `locationId`/`parameterId` headers from `rtcDataConfig.xml`.
  - Both simulation **TimeSteps / Datetimes** and per-variable **Series Event Values** can be edited directly or imported from CSV files using an interactive column and row-range selector dialog with table preview.
  - Import & Export definitions to/from FEWS `timeseries_import.xml`.
  - Full preservation of timeseries import configuration inside exported and imported JSON model files.
- **Model Construction, Execution & Results**:
  - Interactive **Model Construction and Run** section containing **🔨 Construct RTC-Tools Model**, virtual environment Python executable selection, and **▶ Run RTC-Tools Model**.
  - Comprehensive pre-flight checks (JSON saved, project folders `input`, `model`, `src`, `output`, configuration CSVs/XMLs, `<ModelName>.mo`, `<ModelName>.py`, and `timeseries_import.xml`).
  - Runs optimization script and redirects logs to `output/rtc_tools_log.txt`.
  - Result view buttons: **📄 Log Messages**, **📁 Show Result Folder**, and **🌐 Show Final Result** (`output/figures/final_results.html`).
- **Property Management**: Edit properties, names, and custom key-value metadata.

## Plugin Structure

```
RTC-Tools-QGIS-Plugin/
├── metadata.txt                   # QGIS plugin metadata specification
├── __init__.py                    # Plugin entry point (classFactory)
├── plugin.py                      # Main plugin controller class (RTCToolsPlugin)
├── model_manager.py               # Layer management, element data, topological validation, JSON/Modelica/RTC-Tools export & import
├── map_tool.py                    # Custom QgsMapTool for canvas point placement, branch creation, and interactive node moving
├── dock_widget.py                 # RTCToolsDockWidget UI panel
├── element_dialog.py              # Element properties editor dialog
├── goal_table_dialog.py           # Optimization Goal Table editor dialog
├── plot_table_dialog.py           # Plot Table editor dialog
├── rtc_data_config_dialog.py      # FEWS rtcDataConfig editor dialog
├── rtc_parameter_config_dialog.py # FEWS rtcParameterConfig editor dialog
├── timeseries_import_dialog.py    # FEWS timeseries_import editor and CSV column/row-range import dialogs
├── run_tests.py                   # Headless QGIS test runner script
├── tests/                         # Automated unit tests
│   ├── test_dock_widget.py
│   ├── test_map_tool.py
│   └── test_model_manager.py
├── icon.png                       # Plugin toolbar icon
├── LICENSE                        # MIT License
└── README.md                      # Documentation
```

## JSON Model Output Format

When exporting via **💾 Save**, **💾➕ Save as**, or **🔨 Construct RTC-Tools Model**, the plugin generates `<WorkingFolder>/<ModelName>/<ModelName>.json` structured as follows:

```json
{
  "model_type": "RTC-Tools Model",
  "model_name": "BlueRiver",
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
  ],
  "goals": [],
  "plots": [],
  "rtc_data_config": [],
  "rtc_parameter_config": [],
  "timeseries_import": {}
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
2. Under **Model File**, specify a valid **Model Name** (e.g. `BlueRiver`) and select a **Working Folder**.
3. Under **Elements**, choose an **Element Type** (`Node`, `Inflow`, `Level`, `Terminal`, `Reservoir`).
4. Click **📍 Add Element on Map** and click the canvas to place elements.
5. Select **Branch**, click **🔗 Connect Elements with Branch**, click the upstream element, then click the downstream element.
6. To reposition an element, click **✋ Move Element on Map** and drag the node (or click to pick and click to place). Connected branches automatically update. You can also select a node in the table and click **Move**, or edit coordinates directly in the **Edit** dialog.
7. Under **Model Elements**, edit or delete model elements in the table and specify bounds/properties.
8. Under **Model File**, click **🔍 Validate Model** to verify all topological input/output constraints.
9. Configure optimization goals (**Optimization Goals**), plot definitions (**Plot Configuration**), FEWS mappings (**Data Config Mapping**), model parameters (**Parameter Config**), and simulation timesteps/series values (**TimeSeries Import Data** — including importing timesteps or values from a specific CSV column and row range).
10. Save your model via **💾 Save** (or **💾➕ Save as** to save under a new model name or working folder). Use **❌ Close** to close the currently opened model and **📂 Open** to load an existing model from JSON.
11. Under **Model Construction and Run**, click **🔨 Construct RTC-Tools Model** to generate the complete RTC-Tools project structure (`<ModelName>.json`, `input/`, `model/`, `output/`, and `src/`) inside `<WorkingFolder>/<ModelName>/`.
12. Select a Python environment (if needed) under **Model Construction and Run** and click **▶ Run RTC-Tools Model** to execute the optimization, then inspect results via **📄 Log Messages**, **📁 Show Result Folder**, or **🌐 Show Final Result**.

## Running Tests

Automated headless tests are provided in the `tests/` directory and can be run using QGIS's Python environment:

- **Windows**:
  ```powershell
  & "C:\Program Files\QGIS 3.34.12\bin\python-qgis-ltr.bat" run_tests.py
  ```
- **Linux / macOS (or CI/CD)**:
  ```bash
  python3 run_tests.py
  ```

The test runner configures `QT_QPA_PLATFORM=offscreen` and starts a GUI-enabled `QgsApplication([], True)` in headless mode, exercising the model manager, map tools, canvas operations, dock widget, and dialogs without requiring a graphical window or display.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
