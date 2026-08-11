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

RTC_PARAM_CONFIG_COLUMNS = ["id", "name", "type", "value"]

TYPE_MAP = {
    "double": "dblValue",
    "integer": "intValue",
    "boolean": "boolValue",
    "string": "stringValue",
    "dateTime": "dateTimeValue"
}

REVERSE_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}

PARAM_TYPES = ["double", "integer", "boolean", "string", "dateTime"]

class RtcParameterConfigDialog(QDialog):
    """Dialog for defining and editing the RTC-Tools rtcParameterConfig parameters."""

    def __init__(self, parameters=None, model_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RTC-Tools rtcParameterConfig Editor")
        self.resize(750, 450)

        self.parameters = [dict(p) for p in (parameters or [])]
        self.model_manager = model_manager

        self._init_ui()
        self._load_parameters_to_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<b>RTC-Tools Parameter Configuration (rtcParameterConfig.xml)</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Table Widget
        self.table = QTableWidget(0, len(RTC_PARAM_CONFIG_COLUMNS))
        self.table.setHorizontalHeaderLabels(["Parameter ID", "Parameter Name", "Data Type", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Control buttons for table rows
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕ Add Parameter")
        btn_add.clicked.connect(self._add_parameter_row)

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

    def _load_parameters_to_table(self):
        self.table.setRowCount(0)
        for p in self.parameters:
            self._insert_parameter_row(p)

    def _insert_parameter_row(self, param_data):
        row = self.table.rowCount()
        self.table.insertRow(row)

        p_id = str(param_data.get("id", "") or "")
        p_name = str(param_data.get("name", "") or p_id or "")
        p_type = str(param_data.get("type", "double") or "double")
        p_value = str(param_data.get("value", "") if param_data.get("value") is not None else "")

        # Column 0: Parameter ID
        self.table.setItem(row, 0, QTableWidgetItem(p_id))

        # Column 1: Parameter Name
        self.table.setItem(row, 1, QTableWidgetItem(p_name))

        # Column 2: Data Type Dropdown
        combo_type = QComboBox()
        for pt in PARAM_TYPES:
            combo_type.addItem(pt)
        if p_type in PARAM_TYPES:
            combo_type.setCurrentText(p_type)
        else:
            combo_type.setCurrentText("double")

        self.table.setCellWidget(row, 2, combo_type)

        # Column 3: Value
        self.table.setItem(row, 3, QTableWidgetItem(p_value))

    def _add_parameter_row(self):
        row_count = self.table.rowCount() + 1
        new_param = {
            "id": f"param_{row_count}",
            "name": f"param_{row_count}",
            "type": "double",
            "value": "0.0"
        }
        self._insert_parameter_row(new_param)

    def _remove_selected_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def _import_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import rtcParameterConfig XML",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                imported = []
                for param_elem in root.findall(".//{*}parameter"):
                    p_id = param_elem.get("id", "")
                    p_name = param_elem.get("name", p_id)

                    p_type = "double"
                    p_value = ""

                    for child in param_elem:
                        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        if tag_name in REVERSE_TYPE_MAP:
                            p_type = REVERSE_TYPE_MAP[tag_name]
                            p_value = child.text.strip() if child.text else ""
                            break

                    if p_id:
                        imported.append({
                            "id": p_id,
                            "name": p_name or p_id,
                            "type": p_type,
                            "value": p_value
                        })

                self.parameters = imported
                self._load_parameters_to_table()
                QMessageBox.information(self, "RTC-Tools", f"Imported {len(imported)} parameters from XML.")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error parsing XML file:\n{str(e)}")

    def _export_xml(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export rtcParameterConfig XML",
            os.path.expanduser("~/rtcParameterConfig.xml"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".xml"):
                file_path += ".xml"

            params_data = self.get_updated_parameters()

            try:
                root = ET.Element("parameters", {
                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "xmlns": "http://www.wldelft.nl/fews/PI",
                    "xsi:schemaLocation": "http://www.wldelft.nl/fews/PI http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_modelparameters.xsd",
                    "version": "1.5"
                })

                group_elem = ET.SubElement(root, "group", {
                    "id": "default",
                    "readonly": "false",
                    "modified": "false"
                })

                for p in params_data:
                    p_id = p.get("id", "")
                    p_name = p.get("name") or p_id
                    p_type = p.get("type", "double")
                    p_val = p.get("value", "")

                    param_elem = ET.SubElement(group_elem, "parameter", {
                        "id": p_id,
                        "name": p_name
                    })

                    val_tag = TYPE_MAP.get(p_type, "dblValue")
                    val_elem = ET.SubElement(param_elem, val_tag)
                    val_elem.text = str(p_val)

                xml_str = ET.tostring(root, encoding="utf-8")
                parsed_dom = minidom.parseString(xml_str)
                pretty_xml = parsed_dom.toprettyxml(indent="\t", encoding="UTF-8").decode("utf-8")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(pretty_xml)

                QMessageBox.information(self, "RTC-Tools", f"rtcParameterConfig exported successfully to '{file_path}'")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error writing XML file:\n{str(e)}")

    def get_updated_parameters(self):
        """Collects current rows from table into a list of parameter dictionaries."""
        updated = []
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 0)
            p_id = id_item.text().strip() if id_item else ""

            name_item = self.table.item(row, 1)
            p_name = name_item.text().strip() if name_item else p_id

            widget = self.table.cellWidget(row, 2)
            p_type = widget.currentText().strip() if isinstance(widget, QComboBox) else "double"

            val_item = self.table.item(row, 3)
            p_value = val_item.text().strip() if val_item else ""

            if p_id:
                updated.append({
                    "id": p_id,
                    "name": p_name or p_id,
                    "type": p_type,
                    "value": p_value
                })

        return updated
