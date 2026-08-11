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
        self.element_types = element_types or ["Node", "Inflow", "Level", "Terminal", "Reservoir", "Branch"]

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

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
        self.grp_reservoir = QGroupBox("Reservoir Storage Volume Parameters (Optional)")
        form_res = QFormLayout(self.grp_reservoir)

        self.txt_min = QLineEdit()
        self.txt_min.setPlaceholderText("e.g. 0.0")
        self.txt_max = QLineEdit()
        self.txt_max.setPlaceholderText("e.g. 1000.0")
        self.txt_nominal = QLineEdit()
        self.txt_nominal.setPlaceholderText("e.g. 500.0")

        form_res.addRow("Minimum Volume:", self.txt_min)
        form_res.addRow("Maximum Volume:", self.txt_max)
        form_res.addRow("Nominal Volume:", self.txt_nominal)

        layout.addWidget(self.grp_reservoir)

        # Reservoir Flows (Turbine, Spill, Outflow) Group
        self.grp_res_flows = QGroupBox("Reservoir Flow Parameters (Optional)")
        form_res_flows = QFormLayout(self.grp_res_flows)

        self.txt_turb_min = QLineEdit()
        self.txt_turb_min.setPlaceholderText("min (e.g. 0)")
        self.txt_turb_max = QLineEdit()
        self.txt_turb_max.setPlaceholderText("max (e.g. 15)")
        self.txt_turb_nom = QLineEdit()
        self.txt_turb_nom.setPlaceholderText("nominal (e.g. 14)")

        self.txt_spill_min = QLineEdit()
        self.txt_spill_min.setPlaceholderText("min (e.g. 0)")
        self.txt_spill_max = QLineEdit()
        self.txt_spill_max.setPlaceholderText("max (e.g. 460)")
        self.txt_spill_nom = QLineEdit()
        self.txt_spill_nom.setPlaceholderText("nominal (e.g. 1)")

        self.txt_qout_min = QLineEdit()
        self.txt_qout_min.setPlaceholderText("min (e.g. 0)")
        self.txt_qout_max = QLineEdit()
        self.txt_qout_max.setPlaceholderText("max (e.g. 575.13)")
        self.txt_qout_nom = QLineEdit()
        self.txt_qout_nom.setPlaceholderText("nominal (e.g. 46.05)")

        h_turb = QHBoxLayout()
        h_turb.addWidget(self.txt_turb_min)
        h_turb.addWidget(self.txt_turb_max)
        h_turb.addWidget(self.txt_turb_nom)
        form_res_flows.addRow("Turbine Flow (min, max, nominal):", h_turb)

        h_spill = QHBoxLayout()
        h_spill.addWidget(self.txt_spill_min)
        h_spill.addWidget(self.txt_spill_max)
        h_spill.addWidget(self.txt_spill_nom)
        form_res_flows.addRow("Spill Flow (min, max, nominal):", h_spill)

        h_qout = QHBoxLayout()
        h_qout.addWidget(self.txt_qout_min)
        h_qout.addWidget(self.txt_qout_max)
        h_qout.addWidget(self.txt_qout_nom)
        form_res_flows.addRow("Total Outflow (min, max, nominal):", h_qout)

        layout.addWidget(self.grp_res_flows)

        # Level Flow Properties Group
        self.grp_level = QGroupBox("Level Flow Parameters (Optional)")
        form_level = QFormLayout(self.grp_level)

        self.txt_level_min = QLineEdit()
        self.txt_level_min.setPlaceholderText("min (e.g. 0)")
        self.txt_level_max = QLineEdit()
        self.txt_level_max.setPlaceholderText("max (e.g. 1000)")
        self.txt_level_nom = QLineEdit()
        self.txt_level_nom.setPlaceholderText("nominal (e.g. 10)")

        h_level = QHBoxLayout()
        h_level.addWidget(self.txt_level_min)
        h_level.addWidget(self.txt_level_max)
        h_level.addWidget(self.txt_level_nom)
        form_level.addRow("Flow Bounds (min, max, nominal):", h_level)

        layout.addWidget(self.grp_level)

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
            self.grp_res_flows.show()
            self.grp_level.hide()
        elif text in ["Level", "Terminal"]:
            self.grp_reservoir.hide()
            self.grp_res_flows.hide()
            self.grp_level.show()
        else:
            self.grp_reservoir.hide()
            self.grp_res_flows.hide()
            self.grp_level.hide()

    def _load_data(self):
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

        props = dict(self.element_data.get("properties", {}))

        # Reservoir volume properties
        min_val = props.pop("Minimum", props.pop("minimum", ""))
        max_val = props.pop("Maximum", props.pop("maximum", ""))
        nom_val = props.pop("Nominal", props.pop("nominal", ""))

        self.txt_min.setText(str(min_val) if min_val is not None else "")
        self.txt_max.setText(str(max_val) if max_val is not None else "")
        self.txt_nominal.setText(str(nom_val) if nom_val is not None else "")

        # Reservoir flow properties
        turb_min = props.pop("Turbine_min", props.pop("turbine_min", ""))
        turb_max = props.pop("Turbine_max", props.pop("turbine_max", ""))
        turb_nom = props.pop("Turbine_nominal", props.pop("turbine_nominal", ""))
        self.txt_turb_min.setText(str(turb_min) if turb_min is not None else "")
        self.txt_turb_max.setText(str(turb_max) if turb_max is not None else "")
        self.txt_turb_nom.setText(str(turb_nom) if turb_nom is not None else "")

        spill_min = props.pop("Spill_min", props.pop("spill_min", ""))
        spill_max = props.pop("Spill_max", props.pop("spill_max", ""))
        spill_nom = props.pop("Spill_nominal", props.pop("spill_nominal", ""))
        self.txt_spill_min.setText(str(spill_min) if spill_min is not None else "")
        self.txt_spill_max.setText(str(spill_max) if spill_max is not None else "")
        self.txt_spill_nom.setText(str(spill_nom) if spill_nom is not None else "")

        qout_min = props.pop("Qout_min", props.pop("qout_min", ""))
        qout_max = props.pop("Qout_max", props.pop("qout_max", ""))
        qout_nom = props.pop("Qout_nominal", props.pop("qout_nominal", ""))
        self.txt_qout_min.setText(str(qout_min) if qout_min is not None else "")
        self.txt_qout_max.setText(str(qout_max) if qout_max is not None else "")
        self.txt_qout_nom.setText(str(qout_nom) if qout_nom is not None else "")

        # Level flow properties
        level_min = props.pop("Flow_min", props.pop("flow_min", ""))
        level_max = props.pop("Flow_max", props.pop("flow_max", ""))
        level_nom = props.pop("Flow_nominal", props.pop("flow_nominal", ""))
        self.txt_level_min.setText(str(level_min) if level_min is not None else "")
        self.txt_level_max.setText(str(level_max) if level_max is not None else "")
        self.txt_level_nom.setText(str(level_nom) if level_nom is not None else "")

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

        def _parse_num(val_str):
            if not val_str:
                return None
            try:
                return float(val_str) if "." in val_str else int(val_str)
            except ValueError:
                return val_str

        managed_keys = [
            "Minimum", "Maximum", "Nominal",
            "Turbine_min", "Turbine_max", "Turbine_nominal",
            "Spill_min", "Spill_max", "Spill_nominal",
            "Qout_min", "Qout_max", "Qout_nominal",
            "Flow_min", "Flow_max", "Flow_nominal"
        ]

        # Add Reservoir specific properties if populated
        if elem_type == "Reservoir":
            min_v = _parse_num(self.txt_min.text().strip())
            max_v = _parse_num(self.txt_max.text().strip())
            nom_v = _parse_num(self.txt_nominal.text().strip())
            if min_v is not None: props["Minimum"] = min_v
            if max_v is not None: props["Maximum"] = max_v
            if nom_v is not None: props["Nominal"] = nom_v

            t_min = _parse_num(self.txt_turb_min.text().strip())
            t_max = _parse_num(self.txt_turb_max.text().strip())
            t_nom = _parse_num(self.txt_turb_nom.text().strip())
            if t_min is not None: props["Turbine_min"] = t_min
            if t_max is not None: props["Turbine_max"] = t_max
            if t_nom is not None: props["Turbine_nominal"] = t_nom

            s_min = _parse_num(self.txt_spill_min.text().strip())
            s_max = _parse_num(self.txt_spill_max.text().strip())
            s_nom = _parse_num(self.txt_spill_nom.text().strip())
            if s_min is not None: props["Spill_min"] = s_min
            if s_max is not None: props["Spill_max"] = s_max
            if s_nom is not None: props["Spill_nominal"] = s_nom

            q_min = _parse_num(self.txt_qout_min.text().strip())
            q_max = _parse_num(self.txt_qout_max.text().strip())
            q_nom = _parse_num(self.txt_qout_nom.text().strip())
            if q_min is not None: props["Qout_min"] = q_min
            if q_max is not None: props["Qout_max"] = q_max
            if q_nom is not None: props["Qout_nominal"] = q_nom

        elif elem_type in ["Level", "Terminal"]:
            l_min = _parse_num(self.txt_level_min.text().strip())
            l_max = _parse_num(self.txt_level_max.text().strip())
            l_nom = _parse_num(self.txt_level_nom.text().strip())
            if l_min is not None: props["Flow_min"] = l_min
            if l_max is not None: props["Flow_max"] = l_max
            if l_nom is not None: props["Flow_nominal"] = l_nom

        for row in range(self.prop_table.rowCount()):
            key_item = self.prop_table.item(row, 0)
            val_item = self.prop_table.item(row, 1)
            if key_item:
                k = key_item.text().strip()
                v = val_item.text().strip() if val_item else ""
                if k and k not in managed_keys:
                    props[k] = v

        return {
            "name": name or self.element_data.get("name"),
            "type": elem_type,
            "properties": props
        }
