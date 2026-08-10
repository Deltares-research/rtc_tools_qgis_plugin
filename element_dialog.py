import json
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QLabel,
    QHeaderView,
    QGroupBox,
)
from qgis.PyQt.QtCore import Qt

class ElementDialog(QDialog):
    """Dialog for editing properties of an RTC-Tools element or Branch connection."""

    def __init__(self, element_data, element_types=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit RTC-Tools Element")
        self.resize(480, 500)

        self.element_data = element_data
        self.element_types = element_types or ["Node", "Inflow", "Level", "Reservoir", "Branch"]

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.txt_id = QLineEdit()
        self.txt_id.setReadOnly(True)

        self.txt_name = QLineEdit()

        self.combo_type = QComboBox()
        for et in self.element_types:
            self.combo_type.addItem(et)
        self.combo_type.currentTextChanged.connect(self._on_type_changed)

        self.txt_x = QLineEdit()
        self.txt_x.setReadOnly(True)
        self.txt_y = QLineEdit()
        self.txt_y.setReadOnly(True)

        self.txt_from = QLineEdit()
        self.txt_from.setReadOnly(True)
        self.txt_to = QLineEdit()
        self.txt_to.setReadOnly(True)

        form.addRow("ID:", self.txt_id)
        form.addRow("Name:", self.txt_name)
        form.addRow("Type:", self.combo_type)

        is_branch = self.element_data.get("type") == "Branch"
        if is_branch:
            form.addRow("Upstream (From):", self.txt_from)
            form.addRow("Downstream (To):", self.txt_to)
        else:
            form.addRow("X Coordinate:", self.txt_x)
            form.addRow("Y Coordinate:", self.txt_y)

        layout.addLayout(form)

        # Reservoir Specific Properties Group
        self.grp_reservoir = QGroupBox("Reservoir Parameters (Optional)")
        form_res = QFormLayout(self.grp_reservoir)

        self.txt_min = QLineEdit()
        self.txt_min.setPlaceholderText("e.g. 0.0")
        self.txt_max = QLineEdit()
        self.txt_max.setPlaceholderText("e.g. 1000.0")
        self.txt_nominal = QLineEdit()
        self.txt_nominal.setPlaceholderText("e.g. 500.0")

        form_res.addRow("Minimum Value:", self.txt_min)
        form_res.addRow("Maximum Value:", self.txt_max)
        form_res.addRow("Nominal Value:", self.txt_nominal)

        layout.addWidget(self.grp_reservoir)

        # Custom Properties Table
        layout.addWidget(QLabel("<b>Additional Properties:</b>"))
        self.prop_table = QTableWidget(0, 2)
        self.prop_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.prop_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.prop_table)

        # Table Control Buttons
        table_btn_layout = QHBoxLayout()
        btn_add_prop = QPushButton("+ Add Property")
        btn_add_prop.clicked.connect(self._add_prop_row)
        btn_del_prop = QPushButton("- Remove Property")
        btn_del_prop.clicked.connect(self._remove_selected_prop_row)

        table_btn_layout.addWidget(btn_add_prop)
        table_btn_layout.addWidget(btn_del_prop)
        table_btn_layout.addStretch()
        layout.addLayout(table_btn_layout)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_type_changed(self, text):
        if text == "Reservoir":
            self.grp_reservoir.show()
        else:
            self.grp_reservoir.hide()

    def _load_data(self):
        self.txt_id.setText(str(self.element_data.get("id", "")))
        self.txt_name.setText(str(self.element_data.get("name", "")))

        elem_type = str(self.element_data.get("type", "Node"))
        index = self.combo_type.findText(elem_type)
        if index >= 0:
            self.combo_type.setCurrentIndex(index)
        else:
            self.combo_type.addItem(elem_type)
            self.combo_type.setCurrentText(elem_type)

        self._on_type_changed(elem_type)

        if elem_type == "Branch":
            from_id = self.element_data.get("from_element") or self.element_data.get("upstream", "")
            to_id = self.element_data.get("to_element") or self.element_data.get("downstream", "")
            self.txt_from.setText(str(from_id))
            self.txt_to.setText(str(to_id))
        else:
            loc = self.element_data.get("location", {})
            self.txt_x.setText(str(loc.get("x", 0.0)))
            self.txt_y.setText(str(loc.get("y", 0.0)))

        # Load Reservoir properties if present
        props = dict(self.element_data.get("properties", {}))

        min_val = props.pop("Minimum", props.pop("minimum", ""))
        max_val = props.pop("Maximum", props.pop("maximum", ""))
        nom_val = props.pop("Nominal", props.pop("nominal", ""))

        self.txt_min.setText(str(min_val) if min_val is not None else "")
        self.txt_max.setText(str(max_val) if max_val is not None else "")
        self.txt_nominal.setText(str(nom_val) if nom_val is not None else "")

        # Load remaining custom properties table
        self.prop_table.setRowCount(0)
        for k, v in props.items():
            row = self.prop_table.rowCount()
            self.prop_table.insertRow(row)
            self.prop_table.setItem(row, 0, QTableWidgetItem(str(k)))
            self.prop_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _add_prop_row(self):
            row = self.prop_table.rowCount()
            self.prop_table.insertRow(row)
            self.prop_table.setItem(row, 0, QTableWidgetItem(str(k)))
            self.prop_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _add_prop_row(self):
        row = self.prop_table.rowCount()
        self.prop_table.insertRow(row)
        self.prop_table.setItem(row, 0, QTableWidgetItem("new_param"))
        self.prop_table.setItem(row, 1, QTableWidgetItem(""))

    def _remove_selected_prop_row(self):
        current_row = self.prop_table.currentRow()
        if current_row >= 0:
            self.prop_table.removeRow(current_row)

    def get_updated_data(self):
        """Returns updated name, type, and properties dictionary."""
        name = self.txt_name.text().strip()
        elem_type = self.combo_type.currentText().strip()

        props = {}

        # Add Reservoir specific properties if populated and type is Reservoir
        if elem_type == "Reservoir":
            min_val = self.txt_min.text().strip()
            max_val = self.txt_max.text().strip()
            nom_val = self.txt_nominal.text().strip()

            if min_val:
                try:
                    props["Minimum"] = float(min_val) if "." in min_val else int(min_val)
                except ValueError:
                    props["Minimum"] = min_val

            if max_val:
                try:
                    props["Maximum"] = float(max_val) if "." in max_val else int(max_val)
                except ValueError:
                    props["Maximum"] = max_val

            if nom_val:
                try:
                    props["Nominal"] = float(nom_val) if "." in nom_val else int(nom_val)
                except ValueError:
                    props["Nominal"] = nom_val

        for row in range(self.prop_table.rowCount()):
            key_item = self.prop_table.item(row, 0)
            val_item = self.prop_table.item(row, 1)
            if key_item:
                k = key_item.text().strip()
                v = val_item.text().strip() if val_item else ""
                if k and k not in ["Minimum", "Maximum", "Nominal"]:
                    props[k] = v

        return {
            "name": name or self.element_data.get("name"),
            "type": elem_type,
            "properties": props
        }
