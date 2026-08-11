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
    QScrollArea,
    QInputDialog,
    QLineEdit,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis

from .element_dialog import ElementDialog
from .goal_table_dialog import GoalTableDialog
from .plot_table_dialog import PlotTableDialog
from .rtc_data_config_dialog import RtcDataConfigDialog

class CollapsibleGroupBox(QGroupBox):
    """A QGroupBox that can expand and collapse its content area when toggled via its checkbox."""

    def __init__(self, title, expanded=False, parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(expanded)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)

        box_layout = QVBoxLayout(self)
        box_layout.setContentsMargins(6, 12, 6, 6)
        box_layout.addWidget(self.content_widget)

        self.toggled.connect(self._on_toggled)
        self.content_widget.setVisible(expanded)

    def _on_toggled(self, checked):
        self.content_widget.setVisible(checked)


class RTCToolsDockWidget(QDockWidget):
    """Dockable panel for RTC-Tools model building and JSON export."""

    def __init__(self, iface, model_manager, map_tool, parent=None):
        super().__init__("RTC-Tools Model Builder", parent)
        self.iface = iface
        self.model_manager = model_manager
        self.map_tool = map_tool
        self.setObjectName("RTCToolsDockWidget")

        # Element types supported
        self.AVAILABLE_ELEMENT_TYPES = ["Node", "Inflow", "Level", "Terminal", "Reservoir", "Branch"]

        self._init_ui()
        self._connect_signals()
        self.refresh_table()

    def _init_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(8)

        # Title Label
        title_label = QLabel("<b>RTC-Tools Model Builder</b>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # --- 1. Element Placement Group ---
        grp_placement = CollapsibleGroupBox("Add Elements", expanded=False)
        layout_placement = grp_placement.content_layout

        h_layout_type = QHBoxLayout()
        h_layout_type.addWidget(QLabel("Element Type:"))
        self.combo_element_type = QComboBox()
        for et in self.AVAILABLE_ELEMENT_TYPES:
            self.combo_element_type.addItem(et)
        self.combo_element_type.currentTextChanged.connect(self._on_type_changed)
        h_layout_type.addWidget(self.combo_element_type)
        layout_placement.addLayout(h_layout_type)

        self.btn_add_element = QPushButton("📍 Add Element on Map")
        self.btn_add_element.setCheckable(True)
        self.btn_add_element.clicked.connect(self._toggle_map_tool)
        layout_placement.addWidget(self.btn_add_element)

        layout.addWidget(grp_placement)

        # --- 2. Model Elements Table Group ---
        grp_table = CollapsibleGroupBox("Model Elements", expanded=False)
        layout_table = grp_table.content_layout

        self.table_elements = QTableWidget(0, 4)
        self.table_elements.setHorizontalHeaderLabels(["Name", "Type", "X / Upstream", "Y / Downstream"])
        self.table_elements.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_elements.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_elements.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_elements.setMinimumHeight(150)
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

        # --- 3. Optimization Goals Group ---
        grp_goals = CollapsibleGroupBox("Optimization Goals", expanded=False)
        layout_goals = grp_goals.content_layout

        self.btn_edit_goals = QPushButton("🎯 Edit Goal Table...")
        self.btn_edit_goals.setStyleSheet("padding: 5px;")
        self.btn_edit_goals.clicked.connect(self._edit_goal_table)
        layout_goals.addWidget(self.btn_edit_goals)

        h_layout_goals_csv = QHBoxLayout()
        self.btn_export_goals_csv = QPushButton("📊 Export Goal CSV...")
        self.btn_export_goals_csv.clicked.connect(self._export_goals_csv)
        self.btn_import_goals_csv = QPushButton("📂 Import Goal CSV...")
        self.btn_import_goals_csv.clicked.connect(self._import_goals_csv)
        h_layout_goals_csv.addWidget(self.btn_export_goals_csv)
        h_layout_goals_csv.addWidget(self.btn_import_goals_csv)
        layout_goals.addLayout(h_layout_goals_csv)

        layout.addWidget(grp_goals)

        # --- 4. Plot Configuration Group ---
        grp_plots = CollapsibleGroupBox("Plot Configuration", expanded=False)
        layout_plots = grp_plots.content_layout

        self.btn_edit_plots = QPushButton("📈 Edit Plot Table...")
        self.btn_edit_plots.setStyleSheet("padding: 5px;")
        self.btn_edit_plots.clicked.connect(self._edit_plot_table)
        layout_plots.addWidget(self.btn_edit_plots)

        h_layout_plots_csv = QHBoxLayout()
        self.btn_export_plots_csv = QPushButton("📊 Export Plot CSV...")
        self.btn_export_plots_csv.clicked.connect(self._export_plots_csv)
        self.btn_import_plots_csv = QPushButton("📂 Import Plot CSV...")
        self.btn_import_plots_csv.clicked.connect(self._import_plots_csv)
        h_layout_plots_csv.addWidget(self.btn_export_plots_csv)
        h_layout_plots_csv.addWidget(self.btn_import_plots_csv)
        layout_plots.addLayout(h_layout_plots_csv)

        layout.addWidget(grp_plots)

        # --- 5. Data Config Mapping Group ---
        grp_data_config = CollapsibleGroupBox("Data Config Mapping", expanded=False)
        layout_data_config = grp_data_config.content_layout

        self.btn_edit_data_config = QPushButton("🔗 Edit rtcDataConfig Table...")
        self.btn_edit_data_config.setStyleSheet("padding: 5px;")
        self.btn_edit_data_config.clicked.connect(self._edit_rtc_data_config)
        layout_data_config.addWidget(self.btn_edit_data_config)

        h_layout_data_config_xml = QHBoxLayout()
        self.btn_export_data_config_xml = QPushButton("📊 Export XML...")
        self.btn_export_data_config_xml.clicked.connect(self._export_rtc_data_config_xml)
        self.btn_import_data_config_xml = QPushButton("📂 Import XML...")
        self.btn_import_data_config_xml.clicked.connect(self._import_rtc_data_config_xml)
        h_layout_data_config_xml.addWidget(self.btn_export_data_config_xml)
        h_layout_data_config_xml.addWidget(self.btn_import_data_config_xml)
        layout_data_config.addLayout(h_layout_data_config_xml)

        layout.addWidget(grp_data_config)

        # --- 6. Save / Export Group ---
        grp_export = CollapsibleGroupBox("Model File", expanded=False)
        layout_export = grp_export.content_layout

        self.btn_validate = QPushButton("🔍 Validate Model")
        self.btn_validate.setStyleSheet("padding: 5px;")
        self.btn_validate.clicked.connect(self._validate_model)
        layout_export.addWidget(self.btn_validate)

        self.btn_export = QPushButton("💾 Save Model to JSON...")
        self.btn_export.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_export.clicked.connect(self._export_model)
        layout_export.addWidget(self.btn_export)

        self.btn_import = QPushButton("📂 Open Model from JSON...")
        self.btn_import.clicked.connect(self._import_model)
        layout_export.addWidget(self.btn_import)

        self.btn_export_mo = QPushButton("⚙️ Construct Modelica File...")
        self.btn_export_mo.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_export_mo.clicked.connect(self._export_modelica)
        layout_export.addWidget(self.btn_export_mo)

        self.btn_construct_rtc = QPushButton("🚀 Construct RTC-Tools Model...")
        self.btn_construct_rtc.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_construct_rtc.clicked.connect(self._construct_rtc_tools_model)
        layout_export.addWidget(self.btn_construct_rtc)

        layout.addWidget(grp_export)

        layout.addStretch()

        scroll_area.setWidget(main_widget)
        self.setWidget(scroll_area)

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

    def _on_type_changed(self, text):
        if not self.btn_add_element.isChecked():
            if text == "Branch":
                self.btn_add_element.setText("🔗 Connect Elements with Branch")
            else:
                self.btn_add_element.setText("📍 Add Element on Map")

    def _toggle_map_tool(self, checked):
        if checked:
            self.iface.mapCanvas().setMapTool(self.map_tool)
            self.btn_add_element.setText("❌ Cancel Map Tool")
        else:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self._on_type_changed(self.get_selected_element_type())

    def _on_element_placed(self, elem_data):
        elem_type = elem_data.get("type")
        if elem_type == "Branch":
            msg = f"Added Branch '{elem_data.get('name')}' ({elem_data.get('from_element')} → {elem_data.get('to_element')})"
        else:
            msg = f"Added {elem_type} '{elem_data.get('name')}'"

        self.iface.messageBar().pushMessage(
            "RTC-Tools",
            msg,
            level=Qgis.MessageLevel.Success,
            duration=3
        )

    def _on_element_changed(self, *args):
        self.refresh_table()

    def refresh_table(self):
        """Reloads element data into the table widget."""
        elements = self.model_manager.get_all_elements()
        self.table_elements.setRowCount(0)

        for elem in elements:
            row = self.table_elements.rowCount()
            self.table_elements.insertRow(row)

            elem_type = elem.get("type", "")
            if elem_type == "Branch":
                col2_str = str(elem.get("from_element", ""))
                col3_str = str(elem.get("to_element", ""))
            else:
                loc = elem.get("location", {})
                col2_str = f"{loc.get('x', 0.0):.4f}"
                col3_str = f"{loc.get('y', 0.0):.4f}"

            self.table_elements.setItem(row, 0, QTableWidgetItem(str(elem.get("name", ""))))
            self.table_elements.setItem(row, 1, QTableWidgetItem(str(elem_type)))
            self.table_elements.setItem(row, 2, QTableWidgetItem(col2_str))
            self.table_elements.setItem(row, 3, QTableWidgetItem(col3_str))

    def _get_selected_element_name(self):
        selected_rows = self.table_elements.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.table_elements.item(row, 0)
        return item.text() if item else None

    def _edit_selected_element(self):
        elem_name = self._get_selected_element_name()
        if not elem_name:
            QMessageBox.information(self, "RTC-Tools", "Please select an element from the table to edit.")
            return

        elem_data = self.model_manager.get_element(elem_name)
        if not elem_data:
            return

        dlg = ElementDialog(elem_data, element_types=self.AVAILABLE_ELEMENT_TYPES, parent=self)
        if dlg.exec_() == ElementDialog.Accepted:
            updated = dlg.get_updated_data()
            success = self.model_manager.update_element(
                elem_name,
                new_name=updated["name"],
                new_type=updated["type"],
                new_properties=updated["properties"]
            )
            if not success:
                QMessageBox.warning(self, "RTC-Tools", f"Could not update element. An element named '{updated['name']}' may already exist.")

    def _delete_selected_element(self):
        elem_name = self._get_selected_element_name()
        if not elem_name:
            QMessageBox.information(self, "RTC-Tools", "Please select an element from the table to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Element",
            f"Are you sure you want to delete element '{elem_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.model_manager.remove_element(elem_name)

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

    def _validate_model(self):
        """Validates element connections and topology, showing a detailed message dialog."""
        is_valid, issues = self.model_manager.validate_model()

        if is_valid:
            QMessageBox.information(
                self,
                "Model Validation Passed",
                "✅ <b>Model Validation Successful!</b><br><br>"
                "All elements and branch connections meet the RTC-Tools topology requirements."
            )
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                "Model validation passed successfully!",
                level=Qgis.MessageLevel.Success,
                duration=4
            )
        else:
            issue_items = "".join([f"<li>{issue}</li>" for issue in issues])
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Model Validation Failed")
            msg_box.setText("⚠️ <b>Model validation found the following issues:</b>")
            msg_box.setInformativeText(f"<ul>{issue_items}</ul>")
            msg_box.exec_()

    def _export_model(self):
        elements = self.model_manager.get_all_elements()
        if not elements:
            QMessageBox.warning(self, "RTC-Tools", "No elements in the model to export.")
            return

        # Perform validation check prior to export
        is_valid, issues = self.model_manager.validate_model()
        if not is_valid:
            issue_text = "\n".join([f"• {issue}" for issue in issues])
            reply = QMessageBox.question(
                self,
                "Validation Warnings Detected",
                f"The model has the following validation issues:\n\n{issue_text}\n\nDo you still want to export to JSON?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
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

    def _export_modelica(self):
        """Constructs and exports a Modelica (*.mo) file."""
        elements = self.model_manager.get_all_elements()
        if not elements:
            QMessageBox.warning(self, "RTC-Tools", "No elements in the model to export.")
            return

        is_valid, issues = self.model_manager.validate_model()
        if not is_valid:
            issue_text = "\n".join([f"• {issue}" for issue in issues])
            reply = QMessageBox.question(
                self,
                "Validation Warnings Detected",
                f"The model has the following validation issues:\n\n{issue_text}\n\nDo you still want to construct the Modelica file anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Construct Modelica File",
            os.path.expanduser("~/rtc_tools_model.mo"),
            "Modelica Files (*.mo);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith(".mo"):
                file_path += ".mo"

            if self.model_manager.export_to_modelica(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Modelica file constructed successfully at '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _construct_rtc_tools_model(self):
        """Asks user for RTC-Tools model name and save location, then constructs full project directory structure."""
        elements = self.model_manager.get_all_elements()
        if not elements:
            QMessageBox.warning(self, "RTC-Tools", "No elements in the model to export.")
            return

        is_valid, issues = self.model_manager.validate_model()
        if not is_valid:
            issue_text = "\n".join([f"• {issue}" for issue in issues])
            reply = QMessageBox.question(
                self,
                "Validation Warnings Detected",
                f"The model has the following validation issues:\n\n{issue_text}\n\nDo you still want to construct the RTC-Tools model structure anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        model_name, ok = QInputDialog.getText(
            self,
            "RTC-Tools Model Name",
            "Enter the RTC-Tools model name:",
            QLineEdit.Normal,
            "rtc_model"
        )
        if not ok or not model_name.strip():
            return
        model_name = model_name.strip()

        save_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Location for Saving RTC-Tools Model",
            os.path.expanduser("~")
        )
        if not save_dir:
            return

        if self.model_manager.construct_rtc_tools_model(save_dir, model_name):
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"RTC-Tools model '{model_name}' constructed successfully in '{save_dir}'",
                level=Qgis.MessageLevel.Success,
                duration=5
            )

    def _edit_goal_table(self):
        """Opens the Goal Table Editor dialog."""
        current_goals = self.model_manager.get_goals()
        dlg = GoalTableDialog(goals=current_goals, model_manager=self.model_manager, parent=self)
        if dlg.exec_() == GoalTableDialog.Accepted:
            updated_goals = dlg.get_updated_goals()
            self.model_manager.set_goals(updated_goals)
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"Goal table updated ({len(updated_goals)} goals configured)",
                level=Qgis.MessageLevel.Success,
                duration=3
            )

    def _export_goals_csv(self):
        """Exports the goal table to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Goal Table CSV",
            os.path.expanduser("~/goal_table.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".csv"):
                file_path += ".csv"

            if self.model_manager.export_goals_to_csv(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Goal table exported successfully to '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _import_goals_csv(self):
        """Imports the goal table from a CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Goal Table CSV",
            os.path.expanduser("~"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            if self.model_manager.import_goals_from_csv(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Imported {len(self.model_manager.get_goals())} goals from '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _edit_plot_table(self):
        """Opens the Plot Table Editor dialog."""
        current_plots = self.model_manager.get_plots()
        dlg = PlotTableDialog(plots=current_plots, model_manager=self.model_manager, parent=self)
        if dlg.exec_() == PlotTableDialog.Accepted:
            updated_plots = dlg.get_updated_plots()
            self.model_manager.set_plots(updated_plots)
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"Plot table updated ({len(updated_plots)} plots configured)",
                level=Qgis.MessageLevel.Success,
                duration=3
            )

    def _export_plots_csv(self):
        """Exports the plot table to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot Table CSV",
            os.path.expanduser("~/plot_table.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".csv"):
                file_path += ".csv"

            if self.model_manager.export_plots_to_csv(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Plot table exported successfully to '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _import_plots_csv(self):
        """Imports the plot table from a CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Plot Table CSV",
            os.path.expanduser("~"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            if self.model_manager.import_plots_from_csv(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Imported {len(self.model_manager.get_plots())} plots from '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _edit_rtc_data_config(self):
        """Opens the rtcDataConfig Editor dialog."""
        current_mappings = self.model_manager.get_rtc_data_config()
        dlg = RtcDataConfigDialog(mappings=current_mappings, model_manager=self.model_manager, parent=self)
        if dlg.exec_() == RtcDataConfigDialog.Accepted:
            updated_mappings = dlg.get_updated_mappings()
            self.model_manager.set_rtc_data_config(updated_mappings)
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"rtcDataConfig updated ({len(updated_mappings)} timeSeries mappings configured)",
                level=Qgis.MessageLevel.Success,
                duration=3
            )

    def _export_rtc_data_config_xml(self):
        """Exports the rtcDataConfig table to an XML file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export rtcDataConfig XML",
            os.path.expanduser("~/rtcDataConfig.xml"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".xml"):
                file_path += ".xml"

            if self.model_manager.export_rtc_data_config_to_xml(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"rtcDataConfig XML exported successfully to '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _import_rtc_data_config_xml(self):
        """Imports the rtcDataConfig table from an XML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import rtcDataConfig XML",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if self.model_manager.import_rtc_data_config_from_xml(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Imported {len(self.model_manager.get_rtc_data_config())} mappings from '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )
