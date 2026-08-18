import csv
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QLabel,
    QComboBox,
    QLineEdit,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QTabWidget,
    QWidget,
)
from qgis.PyQt.QtCore import Qt

class TimeseriesImportDialog(QDialog):
    """Dialog for defining and editing timeseries_import.xml parameters and series events."""

    def __init__(self, data=None, model_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RTC-Tools timeseries_import.xml Editor")
        self.resize(1000, 600)

        self.model_manager = model_manager
        
        # Load or initialize data structure
        data = data or {}
        self.timezone = str(data.get("timeZone", "-6.0"))
        self.time_step_mode = str(data.get("timeStepMode", "nonequidistant"))  # 'nonequidistant' or 'equidistant'
        self.time_step_unit = str(data.get("timeStepUnit", "second"))
        self.time_step_multiplier = str(data.get("timeStepMultiplier", "600"))
        self.global_miss_val = str(data.get("missVal", "-999.0"))

        # Datetimes list: ["2000-01-01 00:00:00", ...]
        self.datetimes = list(data.get("datetimes", []))

        # Series list: [{ "variable_id": "...", "locationId": "...", "parameterId": "...", "units": "m³/s", "missVal": "-999.0", "events": { "2000-01-01 00:00:00": "9.91" } }]
        self.series_list = [dict(s) for s in data.get("series", [])]

        self.suggested_vars = self._get_suggested_variables()

        self._init_ui()
        self._load_datetimes_to_table()
        self._load_series_to_table()

    def _get_suggested_variables(self):
        # First check rtcDataConfig mappings if defined
        if self.model_manager and hasattr(self.model_manager, "get_rtc_data_config"):
            mappings = self.model_manager.get_rtc_data_config()
            if mappings:
                return mappings  # list of dicts with 'id', 'locationId', 'parameterId'

        # Fallback to state variables from model manager
        if self.model_manager and hasattr(self.model_manager, "get_suggested_state_variables"):
            states = self.model_manager.get_suggested_state_variables()
            return [{"id": s, "locationId": "", "parameterId": ""} for s in states]

        return []

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<b>RTC-Tools TimeSeries Import Configuration (timeseries_import.xml)</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Top Global Settings Box
        grp_settings = QGroupBox("Global Header & TimeStep Settings")
        form_settings = QFormLayout(grp_settings)

        self.txt_timezone = QLineEdit(self.timezone)
        self.txt_global_miss_val = QLineEdit(self.global_miss_val)

        self.combo_step_mode = QComboBox()
        self.combo_step_mode.addItem("Nonequidistant (nonequidistant)", "nonequidistant")
        self.combo_step_mode.addItem("Equidistant (unit & multiplier)", "equidistant")
        if self.time_step_mode == "equidistant":
            self.combo_step_mode.setCurrentIndex(1)
        else:
            self.combo_step_mode.setCurrentIndex(0)
        self.combo_step_mode.currentIndexChanged.connect(self._on_step_mode_changed)

        self.txt_step_unit = QLineEdit(self.time_step_unit)
        self.txt_step_multiplier = QLineEdit(self.time_step_multiplier)

        h_step = QHBoxLayout()
        h_step.addWidget(QLabel("Unit:"))
        h_step.addWidget(self.txt_step_unit)
        h_step.addWidget(QLabel("Multiplier:"))
        h_step.addWidget(self.txt_step_multiplier)

        form_settings.addRow("TimeZone:", self.txt_timezone)
        form_settings.addRow("Default Missing Value:", self.txt_global_miss_val)
        form_settings.addRow("TimeStep Mode:", self.combo_step_mode)
        form_settings.addRow("TimeStep Parameters:", h_step)

        layout.addWidget(grp_settings)
        self._on_step_mode_changed()

        # Tabs for Datetimes and Series Variables
        self.tabs = QTabWidget()

        # --- Tab 1: Datetimes List ---
        tab_dt = QWidget()
        layout_dt = QVBoxLayout(tab_dt)

        layout_dt.addWidget(QLabel("<b>Defined Simulation TimeSteps (Date & Time: YYYY-MM-DD HH:MM:SS)</b>"))
        self.table_dt = QTableWidget(0, 1)
        self.table_dt.setHorizontalHeaderLabels(["DateTime"])
        self.table_dt.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_dt.addWidget(self.table_dt)

        btn_layout_dt = QHBoxLayout()
        btn_add_dt = QPushButton("➕ Add TimeStep")
        btn_add_dt.clicked.connect(self._add_dt_row)
        btn_del_dt = QPushButton("➖ Remove Selected")
        btn_del_dt.clicked.connect(self._del_dt_row)
        btn_clear_dt = QPushButton("🗑️ Clear All TimeSteps")
        btn_clear_dt.clicked.connect(self._clear_dt_rows)

        btn_layout_dt.addWidget(btn_add_dt)
        btn_layout_dt.addWidget(btn_del_dt)
        btn_layout_dt.addWidget(btn_clear_dt)
        btn_layout_dt.addStretch()
        layout_dt.addLayout(btn_layout_dt)

        self.tabs.addTab(tab_dt, "1. TimeSteps / Datetimes")

        # --- Tab 2: Series Variables & Data Values ---
        tab_series = QWidget()
        layout_series = QVBoxLayout(tab_series)

        layout_series.addWidget(QLabel("<b>TimeSeries Variables & Data Events</b>"))
        self.table_series = QTableWidget(0, 6)
        self.table_series.setHorizontalHeaderLabels(["Variable ID", "Location ID", "Parameter ID", "Units", "Missing Val", "Values Count"])
        self.table_series.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_series.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_series.doubleClicked.connect(self._edit_series_values)
        layout_series.addWidget(self.table_series)

        btn_layout_series = QHBoxLayout()
        btn_add_s = QPushButton("➕ Add Series Variable")
        btn_add_s.clicked.connect(self._add_series_row)
        btn_edit_s = QPushButton("✏️ Edit Values / CSV Import")
        btn_edit_s.clicked.connect(self._edit_series_values)
        btn_del_s = QPushButton("➖ Remove Selected")
        btn_del_s.clicked.connect(self._del_series_row)

        btn_layout_series.addWidget(btn_add_s)
        btn_layout_series.addWidget(btn_edit_s)
        btn_layout_series.addWidget(btn_del_s)
        btn_layout_series.addStretch()
        layout_series.addLayout(btn_layout_series)

        self.tabs.addTab(tab_series, "2. TimeSeries Variables")

        layout.addWidget(self.tabs)

        # XML Action Buttons & Dialog Buttons
        btn_xml_layout = QHBoxLayout()
        btn_import_xml = QPushButton("📂 Import from XML...")
        btn_import_xml.clicked.connect(self._import_xml)
        btn_export_xml = QPushButton("📊 Export to XML...")
        btn_export_xml.clicked.connect(self._export_xml)

        btn_xml_layout.addWidget(btn_import_xml)
        btn_xml_layout.addWidget(btn_export_xml)
        btn_xml_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        btn_xml_layout.addWidget(button_box)
        layout.addLayout(btn_xml_layout)

    def _on_step_mode_changed(self):
        is_equi = self.combo_step_mode.currentData() == "equidistant"
        self.txt_step_unit.setEnabled(is_equi)
        self.txt_step_multiplier.setEnabled(is_equi)

    def _load_datetimes_to_table(self):
        self.table_dt.setRowCount(0)
        for dt_str in self.datetimes:
            row = self.table_dt.rowCount()
            self.table_dt.insertRow(row)
            self.table_dt.setItem(row, 0, QTableWidgetItem(dt_str))

    def _add_dt_row(self):
        row = self.table_dt.rowCount()
        self.table_dt.insertRow(row)
        dt_val = "2000-01-01 00:00:00" if row == 0 else self.table_dt.item(row - 1, 0).text()
        self.table_dt.setItem(row, 0, QTableWidgetItem(dt_val))

    def _del_dt_row(self):
        curr = self.table_dt.currentRow()
        if curr >= 0:
            self.table_dt.removeRow(curr)

    def _clear_dt_rows(self):
        self.table_dt.setRowCount(0)

    def _get_current_datetimes(self):
        dts = []
        for r in range(self.table_dt.rowCount()):
            item = self.table_dt.item(r, 0)
            if item and item.text().strip():
                dts.append(item.text().strip())
        return dts

    def _load_series_to_table(self):
        self.table_series.setRowCount(0)
        for s in self.series_list:
            self._insert_series_row(s)

    def _insert_series_row(self, series_data):
        row = self.table_series.rowCount()
        self.table_series.insertRow(row)

        var_id = str(series_data.get("variable_id", "") or series_data.get("id", ""))
        loc_id = str(series_data.get("locationId", ""))
        param_id = str(series_data.get("parameterId", ""))
        units = str(series_data.get("units", "m³/s"))
        miss_val = str(series_data.get("missVal", self.txt_global_miss_val.text().strip() or "-999.0"))
        events = series_data.get("events", {})

        # Column 0: Editable ComboBox with suggested model variables / rtcDataConfig mappings
        combo_var = QComboBox()
        combo_var.setEditable(True)

        mapping_dict = {}
        for m in self.suggested_vars:
            mid = m["id"]
            combo_var.addItem(mid)
            mapping_dict[mid] = m

        if var_id and var_id not in [combo_var.itemText(i) for i in range(combo_var.count())]:
            combo_var.addItem(var_id)

        if var_id:
            combo_var.setCurrentText(var_id)

        combo_var.currentTextChanged.connect(lambda text, r=row: self._on_series_var_changed(text, r, mapping_dict))
        self.table_series.setCellWidget(row, 0, combo_var)

        self.table_series.setItem(row, 1, QTableWidgetItem(loc_id))
        self.table_series.setItem(row, 2, QTableWidgetItem(param_id))
        self.table_series.setItem(row, 3, QTableWidgetItem(units))
        self.table_series.setItem(row, 4, QTableWidgetItem(miss_val))
        self.table_series.setItem(row, 5, QTableWidgetItem(f"{len(events)} datapoint(s)"))

        # Store events dict on the row's item data
        item_0 = self.table_series.item(row, 1)
        item_0.setData(Qt.UserRole, events)

    def _on_series_var_changed(self, text, row, mapping_dict):
        if text in mapping_dict:
            m = mapping_dict[text]
            if m.get("locationId"):
                self.table_series.setItem(row, 1, QTableWidgetItem(m["locationId"]))
            if m.get("parameterId"):
                self.table_series.setItem(row, 2, QTableWidgetItem(m["parameterId"]))

    def _add_series_row(self):
        new_series = {
            "variable_id": "Inflow_1",
            "locationId": "Location_1",
            "parameterId": "Inflow",
            "units": "m³/s",
            "missVal": self.txt_global_miss_val.text().strip() or "-999.0",
            "events": {}
        }
        self._insert_series_row(new_series)

    def _del_series_row(self):
        curr = self.table_series.currentRow()
        if curr >= 0:
            self.table_series.removeRow(curr)

    def _edit_series_values(self):
        curr_row = self.table_series.currentRow()
        if curr_row < 0:
            QMessageBox.information(self, "RTC-Tools", "Please select a series variable row to edit values.")
            return

        curr_dts = self._get_current_datetimes()
        if not curr_dts:
            QMessageBox.warning(self, "RTC-Tools", "Please define at least one TimeStep in Tab 1 before editing event values.")
            self.tabs.setCurrentIndex(0)
            return

        combo_widget = self.table_series.cellWidget(curr_row, 0)
        var_name = combo_widget.currentText() if isinstance(combo_widget, QComboBox) else "Variable"

        item_1 = self.table_series.item(curr_row, 1)
        existing_events = item_1.data(Qt.UserRole) or {}

        dlg = SeriesValuesDialog(var_name, curr_dts, existing_events, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            updated_events = dlg.get_events()
            item_1.setData(Qt.UserRole, updated_events)
            self.table_series.setItem(curr_row, 5, QTableWidgetItem(f"{len(updated_events)} datapoint(s)"))

    def _collect_dialog_data(self):
        dts = self._get_current_datetimes()
        series = []

        for r in range(self.table_series.rowCount()):
            widget = self.table_series.cellWidget(r, 0)
            var_id = widget.currentText().strip() if isinstance(widget, QComboBox) else ""

            loc_item = self.table_series.item(r, 1)
            loc_id = loc_item.text().strip() if loc_item else ""

            param_item = self.table_series.item(r, 2)
            param_id = param_item.text().strip() if param_item else ""

            unit_item = self.table_series.item(r, 3)
            units = unit_item.text().strip() if unit_item else "m³/s"

            miss_item = self.table_series.item(r, 4)
            miss_val = miss_item.text().strip() if miss_item else "-999.0"

            events = loc_item.data(Qt.UserRole) if loc_item else {}

            if var_id:
                series.append({
                    "variable_id": var_id,
                    "locationId": loc_id,
                    "parameterId": param_id,
                    "units": units,
                    "missVal": miss_val,
                    "events": events or {}
                })

        return {
            "timeZone": self.txt_timezone.text().strip() or "-6.0",
            "timeStepMode": self.combo_step_mode.currentData(),
            "timeStepUnit": self.txt_step_unit.text().strip() or "second",
            "timeStepMultiplier": self.txt_step_multiplier.text().strip() or "600",
            "missVal": self.txt_global_miss_val.text().strip() or "-999.0",
            "datetimes": dts,
            "series": series
        }

    def _import_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import timeseries_import XML",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                tz_node = root.find("{*}timeZone")
                tz = tz_node.text.strip() if tz_node is not None and tz_node.text else "-6.0"

                all_dts = set()
                imported_series = []

                step_mode = "nonequidistant"
                step_unit = "second"
                step_mult = "600"

                for s_elem in root.findall("{*}series"):
                    hdr = s_elem.find("{*}header")
                    if hdr is None:
                        continue

                    loc_node = hdr.find("{*}locationId")
                    param_node = hdr.find("{*}parameterId")
                    unit_node = hdr.find("{*}units")
                    miss_node = hdr.find("{*}missVal")

                    loc_id = loc_node.text.strip() if loc_node is not None and loc_node.text else ""
                    param_id = param_node.text.strip() if param_node is not None and param_node.text else ""
                    units = unit_node.text.strip() if unit_node is not None and unit_node.text else "m³/s"
                    miss_val = miss_node.text.strip() if miss_node is not None and miss_node.text else "-999.0"

                    # Infer variable ID matching rtcDataConfig if possible
                    var_id = f"{loc_id}_{param_id}" if loc_id and param_id else (loc_id or param_id)
                    if self.model_manager and hasattr(self.model_manager, "get_rtc_data_config"):
                        for m in self.model_manager.get_rtc_data_config():
                            if m.get("locationId") == loc_id and m.get("parameterId") == param_id:
                                var_id = m.get("id")
                                break

                    step_node = hdr.find("{*}timeStep")
                    if step_node is not None:
                        if step_node.get("unit") != "nonequidistant":
                            step_mode = "equidistant"
                            step_unit = step_node.get("unit", "second")
                            step_mult = step_node.get("multiplier", "600")

                    events = {}
                    for ev in s_elem.findall("{*}event"):
                        d = ev.get("date", "")
                        t = ev.get("time", "")
                        v = ev.get("value", "")
                        if d and t:
                            dt_key = f"{d} {t}"
                            events[dt_key] = v
                            all_dts.add(dt_key)

                    imported_series.append({
                        "variable_id": var_id,
                        "locationId": loc_id,
                        "parameterId": param_id,
                        "units": units,
                        "missVal": miss_val,
                        "events": events
                    })

                self.txt_timezone.setText(tz)
                self.combo_step_mode.setCurrentIndex(1 if step_mode == "equidistant" else 0)
                self.txt_step_unit.setText(step_unit)
                self.txt_step_multiplier.setText(step_mult)

                self.datetimes = sorted(list(all_dts))
                self.series_list = imported_series

                self._load_datetimes_to_table()
                self._load_series_to_table()

                QMessageBox.information(self, "RTC-Tools", f"Imported {len(imported_series)} series with {len(all_dts)} unique timesteps from XML.")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error parsing XML file:\n{str(e)}")

    def _export_xml(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export timeseries_import XML",
            os.path.expanduser("~/timeseries_import.xml"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".xml"):
                file_path += ".xml"

            data = self._collect_dialog_data()

            try:
                root = ET.Element("TimeSeries", {
                    "xmlns": "http://www.wldelft.nl/fews/PI",
                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "xsi:schemaLocation": "http://www.wldelft.nl/fews/PI http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd",
                    "version": "1.5"
                })

                tz_elem = ET.SubElement(root, "timeZone")
                tz_elem.text = data["timeZone"]

                dts = data["datetimes"]

                for s in data["series"]:
                    s_elem = ET.SubElement(root, "series")
                    hdr = ET.SubElement(s_elem, "header")

                    ET.SubElement(hdr, "type").text = "instantaneous"
                    ET.SubElement(hdr, "locationId").text = s["locationId"]
                    ET.SubElement(hdr, "parameterId").text = s["parameterId"]

                    if data["timeStepMode"] == "equidistant":
                        ET.SubElement(hdr, "timeStep", {
                            "unit": data["timeStepUnit"],
                            "multiplier": data["timeStepMultiplier"]
                        })
                    else:
                        ET.SubElement(hdr, "timeStep", {"unit": "nonequidistant"})

                    start_d, start_t = ("2000-01-01", "00:00:00")
                    end_d, end_t = ("2000-01-01", "00:00:00")

                    s_events = s.get("events", {})
                    active_dts = [dt for dt in dts if dt in s_events]

                    if active_dts:
                        sorted_active = sorted(active_dts)
                        parts_start = sorted_active[0].split(" ")
                        start_d, start_t = parts_start[0], parts_start[1] if len(parts_start) > 1 else "00:00:00"

                        parts_end = sorted_active[-1].split(" ")
                        end_d, end_t = parts_end[0], parts_end[1] if len(parts_end) > 1 else "00:00:00"

                    ET.SubElement(hdr, "startDate", {"date": start_d, "time": start_t})
                    ET.SubElement(hdr, "endDate", {"date": end_d, "time": end_t})
                    ET.SubElement(hdr, "missVal").text = str(s.get("missVal", data["missVal"]))
                    ET.SubElement(hdr, "units").text = str(s.get("units", "m³/s"))

                    for dt in dts:
                        if dt in s_events:
                            val_str = str(s_events[dt])
                            parts = dt.split(" ")
                            d_str = parts[0]
                            t_str = parts[1] if len(parts) > 1 else "00:00:00"
                            ET.SubElement(s_elem, "event", {
                                "date": d_str,
                                "time": t_str,
                                "value": val_str,
                                "flag": "0"
                            })

                xml_str = ET.tostring(root, encoding="utf-8")
                parsed_dom = minidom.parseString(xml_str)
                pretty_xml = parsed_dom.toprettyxml(indent="\t", encoding="UTF-8").decode("utf-8")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(pretty_xml)

                QMessageBox.information(self, "RTC-Tools", f"timeseries_import XML exported successfully to '{file_path}'")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error writing XML file:\n{str(e)}")

    def get_updated_data(self):
        return self._collect_dialog_data()


class SeriesValuesDialog(QDialog):
    """Sub-dialog to assign event values to a specific series variable across defined datetimes, or import via CSV."""

    def __init__(self, var_name, datetimes, events=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Values for '{var_name}'")
        self.resize(500, 450)

        self.var_name = var_name
        self.datetimes = datetimes
        self.events = dict(events or {})

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<b>TimeStep Values for Variable:</b> <font color='#1E508C'>{self.var_name}</font>"))

        self.table = QTableWidget(len(self.datetimes), 2)
        self.table.setHorizontalHeaderLabels(["DateTime", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, dt in enumerate(self.datetimes):
            dt_item = QTableWidgetItem(dt)
            dt_item.setFlags(dt_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, dt_item)

            val = str(self.events.get(dt, ""))
            self.table.setItem(row, 1, QTableWidgetItem(val))

        layout.addWidget(self.table)

        btn_csv = QPushButton("📂 Import Values from CSV...")
        btn_csv.clicked.connect(self._import_csv)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        h_bottom = QHBoxLayout()
        h_bottom.addWidget(btn_csv)
        h_bottom.addStretch()
        h_bottom.addWidget(btn_box)

        layout.addLayout(h_bottom)

    def _import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Values CSV",
            os.path.expanduser("~"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                imported_map = {}
                with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if not row:
                            continue
                        if len(row) >= 2:
                            k = row[0].strip()
                            v = row[1].strip()
                            imported_map[k] = v

                for r in range(self.table.rowCount()):
                    dt_str = self.table.item(r, 0).text()
                    if dt_str in imported_map:
                        self.table.setItem(r, 1, QTableWidgetItem(imported_map[dt_str]))

                QMessageBox.information(self, "RTC-Tools", "Imported values from CSV successfully.")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error reading CSV:\n{str(e)}")

    def get_events(self):
        res = {}
        for r in range(self.table.rowCount()):
            dt_str = self.table.item(r, 0).text().strip()
            val_item = self.table.item(r, 1)
            val_str = val_item.text().strip() if val_item else ""
            if val_str:
                res[dt_str] = val_str
        return res
