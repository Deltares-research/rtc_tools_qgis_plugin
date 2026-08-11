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
    QHeaderView,
    QFileDialog,
    QMessageBox,
)
from qgis.PyQt.QtCore import Qt

RTC_DATA_CONFIG_COLUMNS = [
    "id",
    "locationId",
    "parameterId"
]

class RtcDataConfigDialog(QDialog):
    """Dialog for defining and editing the RTC-Tools rtcDataConfig timeSeries mapping."""

    def __init__(self, mappings=None, model_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RTC-Tools rtcDataConfig Editor")
        self.resize(750, 450)

        self.mappings = [dict(m) for m in (mappings or [])]
        self.model_manager = model_manager
        self.suggested_vars = self._get_suggested_variables()

        self._init_ui()
        self._load_mappings_to_table()

    def _get_suggested_variables(self):
        if self.model_manager and hasattr(self.model_manager, "get_suggested_state_variables"):
            return self.model_manager.get_suggested_state_variables()
        return []

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<b>RTC-Tools TimeSeries Variable Mapping (rtcDataConfig.xml)</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Table Widget
        self.table = QTableWidget(0, len(RTC_DATA_CONFIG_COLUMNS))
        self.table.setHorizontalHeaderLabels(["TimeSeries ID (Model Variable)", "Location ID", "Parameter ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Control buttons for table rows
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕ Add Mapping")
        btn_add.clicked.connect(self._add_mapping_row)

        btn_remove = QPushButton("➖ Remove Selected")
        btn_remove.clicked.connect(self._remove_selected_row)

        btn_import_xml = QPushButton("📂 Import from XML...")
        btn_import_xml.clicked.connect(self._import_xml)

        btn_export_xml = QPushButton("📊 Export to XML...")
        btn_export_xml.clicked.connect(self._export_xml)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_import_xml)
        btn_layout.addWidget(btn_export_xml)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Dialog accept/cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_mappings_to_table(self):
        self.table.setRowCount(0)
        for m in self.mappings:
            self._insert_mapping_row(m)

    def _insert_mapping_row(self, mapping_data):
        row = self.table.rowCount()
        self.table.insertRow(row)

        ts_id = str(mapping_data.get("id", "") or "")
        loc_id = str(mapping_data.get("locationId", "") or "")
        param_id = str(mapping_data.get("parameterId", "") or "")

        # Column 0: Editable ComboBox with suggested model variables
        combo_id = QComboBox()
        combo_id.setEditable(True)
        vars_list = list(self.suggested_vars)
        if ts_id and ts_id not in vars_list:
            vars_list.insert(0, ts_id)

        for v in vars_list:
            combo_id.addItem(v)

        if ts_id:
            combo_id.setCurrentText(ts_id)

        self.table.setCellWidget(row, 0, combo_id)

        # Column 1: locationId
        item_loc = QTableWidgetItem(loc_id)
        self.table.setItem(row, 1, item_loc)

        # Column 2: parameterId
        item_param = QTableWidgetItem(param_id)
        self.table.setItem(row, 2, item_param)

    def _add_mapping_row(self):
        default_var = self.suggested_vars[0] if self.suggested_vars else "variable_id"
        new_mapping = {
            "id": default_var,
            "locationId": "Location_1",
            "parameterId": "Parameter_1"
        }
        self._insert_mapping_row(new_mapping)

    def _remove_selected_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def _import_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import rtcDataConfig XML",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                imported = []
                for ts_elem in root.findall("{*}timeSeries"):
                    ts_id = ts_elem.get("id", "")
                    pi_elem = ts_elem.find("{*}PITimeSeries")
                    loc_id = ""
                    param_id = ""
                    if pi_elem is not None:
                        loc_node = pi_elem.find("{*}locationId")
                        param_node = pi_elem.find("{*}parameterId")
                        if loc_node is not None and loc_node.text:
                            loc_id = loc_node.text.strip()
                        if param_node is not None and param_node.text:
                            param_id = param_node.text.strip()

                    if ts_id:
                        imported.append({
                            "id": ts_id,
                            "locationId": loc_id,
                            "parameterId": param_id
                        })

                self.mappings = imported
                self._load_mappings_to_table()
                QMessageBox.information(self, "RTC-Tools", f"Imported {len(imported)} timeSeries mappings from XML.")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error parsing XML file:\n{str(e)}")

    def _export_xml(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export rtcDataConfig XML",
            os.path.expanduser("~/rtcDataConfig.xml"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".xml"):
                file_path += ".xml"

            mappings_data = self.get_updated_mappings()

            try:
                root = ET.Element("rtcDataConfig", {
                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "xmlns:rtc": "http://www.wldelft.nl/fews",
                    "xmlns": "http://www.wldelft.nl/fews",
                    "xsi:schemaLocation": "http://www.wldelft.nl/fews ../xsd/rtcDataConfig.xsd"
                })

                for m in mappings_data:
                    ts_elem = ET.SubElement(root, "timeSeries", {"id": m.get("id", "")})
                    pi_elem = ET.SubElement(ts_elem, "PITimeSeries")
                    loc_elem = ET.SubElement(pi_elem, "locationId")
                    loc_elem.text = m.get("locationId", "")
                    param_elem = ET.SubElement(pi_elem, "parameterId")
                    param_elem.text = m.get("parameterId", "")

                xml_str = ET.tostring(root, encoding="utf-8")
                parsed_dom = minidom.parseString(xml_str)
                pretty_xml = parsed_dom.toprettyxml(indent="\t", encoding="UTF-8").decode("utf-8")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(pretty_xml)

                QMessageBox.information(self, "RTC-Tools", f"rtcDataConfig exported successfully to '{file_path}'")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error writing XML file:\n{str(e)}")

    def get_updated_mappings(self):
        """Collects current rows from table into a list of mapping dictionaries."""
        updated = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            ts_id = widget.currentText().strip() if isinstance(widget, QComboBox) else ""

            loc_item = self.table.item(row, 1)
            loc_id = loc_item.text().strip() if loc_item else ""

            param_item = self.table.item(row, 2)
            param_id = param_item.text().strip() if param_item else ""

            if ts_id:
                updated.append({
                    "id": ts_id,
                    "locationId": loc_id,
                    "parameterId": param_id
                })

        return updated
