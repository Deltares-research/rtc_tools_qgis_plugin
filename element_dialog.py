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
    QMessageBox,
)
from qgis.PyQt.QtCore import Qt

class ElementDialog(QDialog):
    """Dialog for editing properties of an RTC-Tools element."""

    def __init__(self, element_data, element_types=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit RTC-Tools Element")
        self.resize(450, 400)

        self.element_data = element_data
        self.element_types = element_types or ["Node"]

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Basic Info Form
        form = QFormLayout()

        self.txt_id = QLineEdit()
        self.txt_id.setReadOnly(True)

        self.txt_name = QLineEdit()

        self.combo_type = QComboBox()
        for et in self.element_types:
            self.combo_type.addItem(et)

        self.txt_x = QLineEdit()
        self.txt_x.setReadOnly(True)
        self.txt_y = QLineEdit()
        self.txt_y.setReadOnly(True)

        form.addRow("ID:", self.txt_id)
        form.addRow("Name:", self.txt_name)
        form.addRow("Type:", self.combo_type)
        form.addRow("X Coordinate:", self.txt_x)
        form.addRow("Y Coordinate:", self.txt_y)

        layout.addLayout(form)

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

        loc = self.element_data.get("location", {})
        self.txt_x.setText(str(loc.get("x", 0.0)))
        self.txt_y.setText(str(loc.get("y", 0.0)))

        # Load properties table
        props = self.element_data.get("properties", {})
        self.prop_table.setRowCount(0)
        for k, v in props.items():
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
        for row in range(self.prop_table.rowCount()):
            key_item = self.prop_table.item(row, 0)
            val_item = self.prop_table.item(row, 1)
            if key_item:
                k = key_item.text().strip()
                v = val_item.text().strip() if val_item else ""
                if k:
                    props[k] = v

        return {
            "name": name or self.element_data.get("name"),
            "type": elem_type,
            "properties": props
        }
