import os
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QLabel,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis

from .element_dialog import ElementDialog

class RTCToolsDockWidget(QDockWidget):
    """Dockable panel for RTC-Tools model building and JSON export."""

    def __init__(self, iface, model_manager, map_tool, parent=None):
        super().__init__("RTC-Tools Model Builder", parent)
        self.iface = iface
        self.model_manager = model_manager
        self.map_tool = map_tool
        self.setObjectName("RTCToolsDockWidget")

        # Element types supported (extensible)
        self.AVAILABLE_ELEMENT_TYPES = ["Node"]

        self._init_ui()
        self._connect_signals()
        self.refresh_table()

    def _init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)

        # Title Label
        title_label = QLabel("<b>RTC-Tools Model Builder</b>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # --- 1. Element Placement Group ---
        grp_placement = QGroupBox("Add Elements")
        layout_placement = QVBoxLayout(grp_placement)

        h_layout_type = QHBoxLayout()
        h_layout_type.addWidget(QLabel("Element Type:"))
        self.combo_element_type = QComboBox()
        for et in self.AVAILABLE_ELEMENT_TYPES:
            self.combo_element_type.addItem(et)
        h_layout_type.addWidget(self.combo_element_type)
        layout_placement.addLayout(h_layout_type)

        self.btn_add_element = QPushButton("📍 Add Element on Map")
        self.btn_add_element.setCheckable(True)
        self.btn_add_element.clicked.connect(self._toggle_map_tool)
        layout_placement.addWidget(self.btn_add_element)

        layout.addWidget(grp_placement)

        # --- 2. Model Elements Table Group ---
        grp_table = QGroupBox("Model Elements")
        layout_table = QVBoxLayout(grp_table)

        self.table_elements = QTableWidget(0, 5)
        self.table_elements.setHorizontalHeaderLabels(["ID", "Name", "Type", "X", "Y"])
        self.table_elements.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_elements.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_elements.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_elements.doubleClicked.connect(self._edit_selected_element)
        layout_table.addWidget(self.table_elements)

        # Table Control Buttons
        h_layout_btns = QHBoxLayout()
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.clicked.connect(self._edit_selected_element)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self._delete_selected_element)

        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self._clear_all_elements)

        h_layout_btns.addWidget(self.btn_edit)
        h_layout_btns.addWidget(self.btn_delete)
        h_layout_btns.addWidget(self.btn_clear)
        layout_table.addLayout(h_layout_btns)

        layout.addWidget(grp_table)

        # --- 3. Save / Export Group ---
        grp_export = QGroupBox("Model File")
        layout_export = QVBoxLayout(grp_export)

        self.btn_export = QPushButton("💾 Save Model to JSON...")
        self.btn_export.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_export.clicked.connect(self._export_model)
        layout_export.addWidget(self.btn_export)

        self.btn_import = QPushButton("📂 Open Model from JSON...")
        self.btn_import.clicked.connect(self._import_model)
        layout_export.addWidget(self.btn_import)

        layout.addWidget(grp_export)

        layout.addStretch()
        self.setWidget(main_widget)

    def _connect_signals(self):
        # Connect model manager signals to refresh GUI automatically
        self.model_manager.elementAdded.connect(self._on_element_changed)
        self.model_manager.elementUpdated.connect(self._on_element_changed)
        self.model_manager.elementRemoved.connect(self._on_element_changed)
        self.model_manager.modelCleared.connect(self.refresh_table)

        # Map tool placement signal
        self.map_tool.elementPlaced.connect(self._on_element_placed)

    def get_selected_element_type(self):
        return self.combo_element_type.currentText()

    def _toggle_map_tool(self, checked):
        if checked:
            self.iface.mapCanvas().setMapTool(self.map_tool)
            self.btn_add_element.setText("❌ Cancel Map Tool")
        else:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self.btn_add_element.setText("📍 Add Element on Map")

    def _on_element_placed(self, elem_data):
        self.iface.messageBar().pushMessage(
            "RTC-Tools",
            f"Added {elem_data.get('type')} '{elem_data.get('name')}' ({elem_data.get('id')})",
            level=Qgis.MessageLevel.Success,
            duration=3
        )
        # Keep map tool active for continuous element addition or uncheck if desired

    def _on_element_changed(self, *args):
        self.refresh_table()

    def refresh_table(self):
        """Reloads element data into the table widget."""
        elements = self.model_manager.get_all_elements()
        self.table_elements.setRowCount(0)

        for elem in elements:
            row = self.table_elements.rowCount()
            self.table_elements.insertRow(row)

            loc = elem.get("location", {})
            x_str = f"{loc.get('x', 0.0):.4f}"
            y_str = f"{loc.get('y', 0.0):.4f}"

            self.table_elements.setItem(row, 0, QTableWidgetItem(str(elem.get("id", ""))))
            self.table_elements.setItem(row, 1, QTableWidgetItem(str(elem.get("name", ""))))
            self.table_elements.setItem(row, 2, QTableWidgetItem(str(elem.get("type", ""))))
            self.table_elements.setItem(row, 3, QTableWidgetItem(x_str))
            self.table_elements.setItem(row, 4, QTableWidgetItem(y_str))

    def _get_selected_element_id(self):
        selected_rows = self.table_elements.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.table_elements.item(row, 0)
        return item.text() if item else None

    def _edit_selected_element(self):
        elem_id = self._get_selected_element_id()
        if not elem_id:
            QMessageBox.information(self, "RTC-Tools", "Please select an element from the table to edit.")
            return

        elem_data = self.model_manager.get_element(elem_id)
        if not elem_data:
            return

        dlg = ElementDialog(elem_data, element_types=self.AVAILABLE_ELEMENT_TYPES, parent=self)
        if dlg.exec_() == ElementDialog.Accepted:
            updated = dlg.get_updated_data()
            self.model_manager.update_element(
                elem_id,
                new_name=updated["name"],
                new_type=updated["type"],
                new_properties=updated["properties"]
            )

    def _delete_selected_element(self):
        elem_id = self._get_selected_element_id()
        if not elem_id:
            QMessageBox.information(self, "RTC-Tools", "Please select an element from the table to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Element",
            f"Are you sure you want to delete element '{elem_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.model_manager.remove_element(elem_id)

    def _clear_all_elements(self):
        if not self.model_manager.get_all_elements():
            return

        reply = QMessageBox.question(
            self,
            "Clear Model",
            "Are you sure you want to clear all model elements?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.model_manager.clear_all()

    def _export_model(self):
        elements = self.model_manager.get_all_elements()
        if not elements:
            QMessageBox.warning(self, "RTC-Tools", "No elements in the model to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save RTC-Tools Model",
            os.path.expanduser("~/rtc_tools_model.json"),
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith(".json"):
                file_path += ".json"

            if self.model_manager.export_to_json(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Model saved successfully to '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _import_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open RTC-Tools Model",
            os.path.expanduser("~"),
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if self.model_manager.import_from_json(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Loaded model from '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )
            else:
                QMessageBox.critical(self, "RTC-Tools", f"Failed to load model from '{file_path}'")
