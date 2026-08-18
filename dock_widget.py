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
    QDialog,
    QDialogButtonBox,
    QTextEdit,
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.core import Qgis

from .element_dialog import ElementDialog
from .goal_table_dialog import GoalTableDialog
from .plot_table_dialog import PlotTableDialog
from .rtc_data_config_dialog import RtcDataConfigDialog
from .rtc_parameter_config_dialog import RtcParameterConfigDialog
from .timeseries_import_dialog import TimeseriesImportDialog

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


class ModelRunnerThread(QThread):
    """Background worker thread to run RTC-Tools model without freezing QGIS UI."""

    finished_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, python_exec, py_file_path, model_dir, log_file_path, run_env, parent=None):
        super().__init__(parent)
        self.python_exec = python_exec
        self.py_file_path = py_file_path
        self.model_dir = model_dir
        self.log_file_path = log_file_path
        self.run_env = run_env

    def run(self):
        import subprocess
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as log_f:
                process = subprocess.Popen(
                    [self.python_exec, self.py_file_path],
                    cwd=self.model_dir,
                    env=self.run_env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT
                )
                process.wait()
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.error_signal.emit(str(e))


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

        # --- 6. Parameter Config Group ---
        grp_param_config = CollapsibleGroupBox("Parameter Config", expanded=False)
        layout_param_config = grp_param_config.content_layout

        self.btn_edit_param_config = QPushButton("⚙️ Edit rtcParameterConfig Table...")
        self.btn_edit_param_config.setStyleSheet("padding: 5px;")
        self.btn_edit_param_config.clicked.connect(self._edit_rtc_parameter_config)
        layout_param_config.addWidget(self.btn_edit_param_config)

        h_layout_param_config_xml = QHBoxLayout()
        self.btn_export_param_config_xml = QPushButton("📊 Export XML...")
        self.btn_export_param_config_xml.clicked.connect(self._export_rtc_parameter_config_xml)
        self.btn_import_param_config_xml = QPushButton("📂 Import XML...")
        self.btn_import_param_config_xml.clicked.connect(self._import_rtc_parameter_config_xml)
        h_layout_param_config_xml.addWidget(self.btn_export_param_config_xml)
        h_layout_param_config_xml.addWidget(self.btn_import_param_config_xml)
        layout_param_config.addLayout(h_layout_param_config_xml)

        layout.addWidget(grp_param_config)

        # --- 7. TimeSeries Import Group ---
        grp_ts_import = CollapsibleGroupBox("TimeSeries Import Data", expanded=False)
        layout_ts_import = grp_ts_import.content_layout

        self.btn_edit_ts_import = QPushButton("📅 Edit TimeSeries Import Data...")
        self.btn_edit_ts_import.setStyleSheet("padding: 5px;")
        self.btn_edit_ts_import.clicked.connect(self._edit_timeseries_import)
        layout_ts_import.addWidget(self.btn_edit_ts_import)

        h_layout_ts_xml = QHBoxLayout()
        self.btn_export_ts_xml = QPushButton("📊 Export XML...")
        self.btn_export_ts_xml.clicked.connect(self._export_timeseries_import_xml)
        self.btn_import_ts_xml = QPushButton("📂 Import XML...")
        self.btn_import_ts_xml.clicked.connect(self._import_timeseries_import_xml)
        h_layout_ts_xml.addWidget(self.btn_export_ts_xml)
        h_layout_ts_xml.addWidget(self.btn_import_ts_xml)
        layout_ts_import.addLayout(h_layout_ts_xml)

        layout.addWidget(grp_ts_import)

        # --- 8. Model Run Group ---
        grp_run = CollapsibleGroupBox("Model Run", expanded=False)
        layout_run = grp_run.content_layout

        h_layout_venv = QHBoxLayout()
        h_layout_venv.addWidget(QLabel("Python Environment:"))
        self.btn_browse_venv = QPushButton("Browse...")
        self.btn_browse_venv.clicked.connect(self._browse_venv_python)
        h_layout_venv.addWidget(self.btn_browse_venv)
        layout_run.addLayout(h_layout_venv)

        self.lbl_venv_path = QLabel("System Default Python")
        self.lbl_venv_path.setStyleSheet("color: #555555; font-size: 10px;")
        self.lbl_venv_path.setWordWrap(True)
        layout_run.addWidget(self.lbl_venv_path)
        self.venv_python_executable = None

        self.btn_run_rtc = QPushButton("▶ Run RTC-Tools Model")
        self.btn_run_rtc.setStyleSheet("font-weight: bold; padding: 6px; background-color: #27AE60; color: white;")
        self.btn_run_rtc.clicked.connect(self._run_rtc_tools_model)
        layout_run.addWidget(self.btn_run_rtc)

        h_layout_run_results = QHBoxLayout()
        self.btn_show_log = QPushButton("📄 Log Messages")
        self.btn_show_log.clicked.connect(self._show_log_messages)

        self.btn_show_res_folder = QPushButton("📁 Show Result Folder")
        self.btn_show_res_folder.clicked.connect(self._show_result_folder)

        h_layout_run_results.addWidget(self.btn_show_log)
        h_layout_run_results.addWidget(self.btn_show_res_folder)
        layout_run.addLayout(h_layout_run_results)

        self.btn_show_final_result = QPushButton("🌐 Show Final Result")
        self.btn_show_final_result.clicked.connect(self._show_final_result)
        layout_run.addWidget(self.btn_show_final_result)

        layout.addWidget(grp_run)

        # --- 8. Save / Export Group ---
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

        # Refresh Model Run buttons initial state
        self._update_run_buttons_state()

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
        self._update_run_buttons_state()

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

    def _edit_rtc_parameter_config(self):
        """Opens the rtcParameterConfig Editor dialog."""
        current_params = self.model_manager.get_rtc_parameter_config()
        dlg = RtcParameterConfigDialog(parameters=current_params, model_manager=self.model_manager, parent=self)
        if dlg.exec_() == RtcParameterConfigDialog.Accepted:
            updated_params = dlg.get_updated_parameters()
            self.model_manager.set_rtc_parameter_config(updated_params)
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"rtcParameterConfig updated ({len(updated_params)} parameters configured)",
                level=Qgis.MessageLevel.Success,
                duration=3
            )

    def _export_rtc_parameter_config_xml(self):
        """Exports the rtcParameterConfig table to an XML file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export rtcParameterConfig XML",
            os.path.expanduser("~/rtcParameterConfig.xml"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".xml"):
                file_path += ".xml"

            if self.model_manager.export_rtc_parameter_config_to_xml(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"rtcParameterConfig XML exported successfully to '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _import_rtc_parameter_config_xml(self):
        """Imports the rtcParameterConfig table from an XML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import rtcParameterConfig XML",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if self.model_manager.import_rtc_parameter_config_from_xml(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Imported {len(self.model_manager.get_rtc_parameter_config())} parameters from '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _edit_timeseries_import(self):
        """Opens the timeseries_import Editor dialog."""
        current_data = self.model_manager.get_timeseries_import()
        dlg = TimeseriesImportDialog(data=current_data, model_manager=self.model_manager, parent=self)
        if dlg.exec_() == TimeseriesImportDialog.Accepted:
            updated_data = dlg.get_updated_data()
            self.model_manager.set_timeseries_import(updated_data)
            series_count = len(updated_data.get("series", []))
            dt_count = len(updated_data.get("datetimes", []))
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"timeseries_import updated ({series_count} series across {dt_count} timeSteps)",
                level=Qgis.MessageLevel.Success,
                duration=3
            )

    def _export_timeseries_import_xml(self):
        """Exports the timeseries_import configuration to an XML file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export timeseries_import XML",
            os.path.expanduser("~/timeseries_import.xml"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".xml"):
                file_path += ".xml"

            if self.model_manager.export_timeseries_import_to_xml(file_path):
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"timeseries_import XML exported successfully to '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _import_timeseries_import_xml(self):
        """Imports the timeseries_import configuration from an XML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import timeseries_import XML",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            if self.model_manager.import_timeseries_import_from_xml(file_path):
                ts_data = self.model_manager.get_timeseries_import()
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Imported {len(ts_data.get('series', []))} series from '{file_path}'",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )

    def _browse_venv_python(self):
        """Allows user to browse for a virtual environment Python executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Virtual Environment Python Executable",
            os.path.expanduser("~"),
            "Python Executable (python.exe python3 python);;All Files (*)"
        )
        if file_path:
            self.venv_python_executable = file_path
            self.lbl_venv_path.setText(f"Python: {file_path}")

    def _get_active_python_executable(self):
        return self.venv_python_executable or "python"

    def _get_current_model_context(self):
        """Returns tuple (json_path, model_dir, model_name) if valid saved model exists."""
        json_path = getattr(self.model_manager, "last_saved_json_path", None)
        if not json_path or not os.path.exists(json_path):
            return None, None, None

        base_dir = os.path.dirname(json_path)
        json_filename = os.path.basename(json_path)
        model_name = os.path.splitext(json_filename)[0]

        model_dir = os.path.join(base_dir, model_name)
        return json_path, model_dir, model_name

    def _update_run_buttons_state(self):
        """Updates enablement of Log Messages, Show Result Folder, and Show Final Result buttons."""
        _, model_dir, _ = self.get_current_model_context_for_ui()

        has_log = False
        has_output_dir = False
        has_final_result = False

        if model_dir and os.path.isdir(model_dir):
            output_dir = os.path.join(model_dir, "output")
            if os.path.isdir(output_dir):
                has_output_dir = True

            log_file = os.path.join(output_dir, "rtc_tools_log.txt") if has_output_dir else None
            if log_file and os.path.exists(log_file):
                has_log = True

            html_file = os.path.join(output_dir, "figures", "final_results.html") if has_output_dir else None
            if html_file and os.path.exists(html_file):
                has_final_result = True

        self.btn_show_log.setEnabled(has_log)
        self.btn_show_res_folder.setEnabled(has_output_dir)
        self.btn_show_final_result.setEnabled(has_final_result)

    def get_current_model_context_for_ui(self):
        json_path = getattr(self.model_manager, "last_saved_json_path", None)
        if not json_path:
            return None, None, None
        base_dir = os.path.dirname(json_path)
        model_name = os.path.splitext(os.path.basename(json_path))[0]
        model_dir = os.path.join(base_dir, model_name)
        return json_path, model_dir, model_name

    def _run_rtc_tools_model(self):
        """Validates model files & directories, then executes the RTC-Tools Python script."""
        import subprocess

        # 1. Check if model has been saved to JSON
        json_path, model_dir, model_name = self._get_current_model_context()
        if not json_path:
            QMessageBox.critical(
                self,
                "Model Not Saved",
                "The constructed model has not been saved to a JSON file yet.\n\n"
                "Please click 'Save Model to JSON...' or 'Construct RTC-Tools Model...' first."
            )
            return

        # 2. Check if sibling model directory exists
        if not os.path.isdir(model_dir):
            QMessageBox.critical(
                self,
                "Model Directory Missing",
                f"The RTC-Tools model directory was not found:\n'{model_dir}'\n\n"
                "Please click 'Construct RTC-Tools Model...' to generate the project directory."
            )
            return

        # 3. Check subfolders
        input_dir = os.path.join(model_dir, "input")
        output_dir = os.path.join(model_dir, "output")
        model_sub_dir = os.path.join(model_dir, "model")
        src_dir = os.path.join(model_dir, "src")

        for s_dir, s_name in [(input_dir, "input"), (output_dir, "output"), (model_sub_dir, "model"), (src_dir, "src")]:
            if not os.path.isdir(s_dir):
                QMessageBox.critical(
                    self,
                    "Subfolder Missing",
                    f"Required subfolder '{s_name}' is missing inside:\n'{model_dir}'"
                )
                return

        # 4. Check required input files
        required_inputs = ["plot_table.csv", "goal_table.csv", "rtcDataConfig.xml", "rtcParameterConfig.xml"]
        for f_name in required_inputs:
            f_path = os.path.join(input_dir, f_name)
            if not os.path.exists(f_path):
                QMessageBox.critical(
                    self,
                    "Required File Missing",
                    f"Required configuration file '{f_name}' is missing in:\n'{input_dir}'"
                )
                return

        # Check timeseries_import.xml with manual copy explanation
        timeseries_import_path = os.path.join(input_dir, "timeseries_import.xml")
        if not os.path.exists(timeseries_import_path):
            QMessageBox.critical(
                self,
                "timeseries_import.xml Missing",
                f"Required file 'timeseries_import.xml' was not found in:\n'{input_dir}'\n\n"
                "This file is not generated by the plugin. Please copy your 'timeseries_import.xml' file manually into the 'input' folder."
            )
            return

        # 5. Check Modelica file in model/
        mo_file_path = os.path.join(model_sub_dir, f"{model_name}.mo")
        if not os.path.exists(mo_file_path):
            QMessageBox.critical(
                self,
                "Modelica File Missing",
                f"Modelica model file '{model_name}.mo' was not found in:\n'{model_sub_dir}'"
            )
            return

        # 6. Check Python source file in src/
        py_file_path = os.path.join(src_dir, f"{model_name}.py")
        if not os.path.exists(py_file_path):
            QMessageBox.critical(
                self,
                "Python Source File Missing",
                f"Python source runner file '{model_name}.py' was not found in:\n'{src_dir}'"
            )
            return

        # 7. Execute python source file in background thread and log output
        python_exec = self._get_active_python_executable()
        log_file_path = os.path.join(output_dir, "rtc_tools_log.txt")

        # Prepare clean environment variables to prevent inheriting QGIS internal Python paths
        run_env = os.environ.copy()
        run_env.pop("PYTHONPATH", None)
        run_env.pop("PYTHONHOME", None)

        if self.venv_python_executable and os.path.exists(self.venv_python_executable):
            venv_bin = os.path.dirname(self.venv_python_executable)
            venv_root = os.path.dirname(venv_bin)
            run_env["VIRTUAL_ENV"] = venv_root
            run_env["PATH"] = venv_bin + os.path.pathsep + run_env.get("PATH", "")

        self.iface.messageBar().pushMessage(
            "RTC-Tools",
            f"Running RTC-Tools model '{model_name}'...",
            level=Qgis.MessageLevel.Info,
            duration=4
        )

        # Disable Run button while running
        self.btn_run_rtc.setEnabled(False)
        self.btn_run_rtc.setText("⏳ Running Model...")

        self.runner_thread = ModelRunnerThread(
            python_exec=python_exec,
            py_file_path=py_file_path,
            model_dir=model_dir,
            log_file_path=log_file_path,
            run_env=run_env,
            parent=self
        )

        def on_finished(returncode):
            self.btn_run_rtc.setEnabled(True)
            self.btn_run_rtc.setText("▶ Run RTC-Tools Model")

            if returncode == 0:
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Model '{model_name}' execution completed successfully!",
                    level=Qgis.MessageLevel.Success,
                    duration=5
                )
            else:
                QMessageBox.warning(
                    self,
                    "Execution Error",
                    f"Model execution exited with code {returncode}.\n"
                    "Click 'Log Messages' to view the log file."
                )
            self._update_run_buttons_state()

        def on_error(err_msg):
            self.btn_run_rtc.setEnabled(True)
            self.btn_run_rtc.setText("▶ Run RTC-Tools Model")
            QMessageBox.critical(
                self,
                "Execution Failed",
                f"Failed to launch Python execution using '{python_exec}':\n{err_msg}"
            )
            self._update_run_buttons_state()

        self.runner_thread.finished_signal.connect(on_finished)
        self.runner_thread.error_signal.connect(on_error)
        self.runner_thread.start()

    def _show_log_messages(self):
        """Displays the contents of rtc_tools_log.txt in a scrollable message box."""
        _, model_dir, _ = self.get_current_model_context_for_ui()
        if not model_dir:
            return

        log_path = os.path.join(model_dir, "output", "rtc_tools_log.txt")
        if not os.path.exists(log_path):
            QMessageBox.information(self, "RTC-Tools Log", "No log file found.")
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                log_content = f.read()

            dlg = QDialog(self)
            dlg.setWindowTitle("RTC-Tools Log Messages")
            dlg.resize(700, 500)

            v_layout = QVBoxLayout(dlg)
            text_box = QLineEdit()
            text_box.setReadOnly(True)

            from qgis.PyQt.QtWidgets import QTextEdit
            txt_edit = QTextEdit()
            txt_edit.setReadOnly(True)
            txt_edit.setPlainText(log_content)
            v_layout.addWidget(txt_edit)

            btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
            btn_box.accepted.connect(dlg.accept)
            v_layout.addWidget(btn_box)

            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "RTC-Tools Log", f"Error reading log file:\n{str(e)}")

    def _show_result_folder(self):
        """Opens the model output folder in the OS file explorer."""
        import subprocess, platform

        _, model_dir, _ = self.get_current_model_context_for_ui()
        if not model_dir:
            return

        output_dir = os.path.join(model_dir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(output_dir)
            elif system == "Darwin":
                subprocess.Popen(["open", output_dir])
            else:
                subprocess.Popen(["xdg-open", output_dir])
        except Exception as e:
            QMessageBox.critical(self, "RTC-Tools", f"Could not open folder:\n{str(e)}")

    def _show_final_result(self):
        """Opens output/figures/final_results.html in default web browser."""
        import webbrowser

        _, model_dir, _ = self.get_current_model_context_for_ui()
        if not model_dir:
            return

        html_path = os.path.join(model_dir, "output", "figures", "final_results.html")
        if not os.path.exists(html_path):
            QMessageBox.information(
                self,
                "Final Result Missing",
                f"File 'final_results.html' was not found at:\n'{html_path}'"
            )
            return

        webbrowser.open(f"file:///{os.path.abspath(html_path)}")
