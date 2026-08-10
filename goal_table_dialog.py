import csv
import os
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

GOAL_COLUMNS = [
    "id",
    "state",
    "active",
    "goal_type",
    "function_min",
    "function_max",
    "function_nominal",
    "target_data_type",
    "target_min",
    "target_max",
    "priority",
    "weight",
    "order",
    "Description"
]

GOAL_TYPES = ["range", "range_rate_of_change", "minimization_path", "maximization_path"]
TARGET_DATA_TYPES = ["value", "timeseries", ""]
ACTIVE_OPTIONS = ["1", "0"]

class GoalTableDialog(QDialog):
    """Dialog for defining and editing the RTC-Tools Goal Table."""

    def __init__(self, goals=None, model_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RTC-Tools Goal Table Editor")
        self.resize(1100, 500)

        self.goals = [dict(g) for g in (goals or [])]
        self.model_manager = model_manager
        self.suggested_states = self._get_suggested_states()

        self._init_ui()
        self._load_goals_to_table()

    def _get_suggested_states(self):
        if self.model_manager and hasattr(self.model_manager, "get_suggested_state_variables"):
            return self.model_manager.get_suggested_state_variables()
        return []

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<b>RTC-Tools Optimization Goal Table</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Table Widget
        self.table = QTableWidget(0, len(GOAL_COLUMNS))
        self.table.setHorizontalHeaderLabels(GOAL_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Control buttons for table rows
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕ Add Goal")
        btn_add.clicked.connect(self._add_goal_row)

        btn_remove = QPushButton("➖ Remove Selected")
        btn_remove.clicked.connect(self._remove_selected_row)

        btn_import_csv = QPushButton("📂 Import Goals from CSV...")
        btn_import_csv.clicked.connect(self._import_csv)

        btn_export_csv = QPushButton("📊 Export Goals to CSV...")
        btn_export_csv.clicked.connect(self._export_csv)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_import_csv)
        btn_layout.addWidget(btn_export_csv)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Dialog accept/cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_goals_to_table(self):
        self.table.setRowCount(0)
        for goal in self.goals:
            self._insert_goal_row(goal)

    def _insert_goal_row(self, goal_data):
        row = self.table.rowCount()
        self.table.insertRow(row)

        for col_idx, col_name in enumerate(GOAL_COLUMNS):
            val = str(goal_data.get(col_name, "") if goal_data.get(col_name) is not None else "")

            if col_name == "state":
                combo = QComboBox()
                combo.setEditable(True)

                states = list(self.suggested_states)
                if val and val not in states:
                    states.insert(0, val)

                for st in states:
                    combo.addItem(st)

                if val:
                    combo.setCurrentText(val)

                self.table.setCellWidget(row, col_idx, combo)

            elif col_name == "active":
                combo = QComboBox()
                for opt in ACTIVE_OPTIONS:
                    combo.addItem(opt)
                if val in ACTIVE_OPTIONS:
                    combo.setCurrentText(val)
                else:
                    combo.setCurrentText("1")
                self.table.setCellWidget(row, col_idx, combo)

            elif col_name == "goal_type":
                combo = QComboBox()
                combo.setEditable(True)
                for gt in GOAL_TYPES:
                    combo.addItem(gt)
                if val:
                    combo.setCurrentText(val)
                else:
                    combo.setCurrentText("range")
                self.table.setCellWidget(row, col_idx, combo)

            elif col_name == "target_data_type":
                combo = QComboBox()
                combo.setEditable(True)
                for dt in TARGET_DATA_TYPES:
                    combo.addItem(dt)
                if val is not None:
                    combo.setCurrentText(val)
                self.table.setCellWidget(row, col_idx, combo)

            else:
                item = QTableWidgetItem(val)
                self.table.setItem(row, col_idx, item)

    def _add_goal_row(self):
        default_state = self.suggested_states[0] if self.suggested_states else "state_var"
        row_count = self.table.rowCount() + 1

        new_goal = {
            "id": f"Goal_{row_count}",
            "state": default_state,
            "active": "1",
            "goal_type": "range",
            "function_min": "",
            "function_max": "",
            "function_nominal": "",
            "target_data_type": "value",
            "target_min": "",
            "target_max": "",
            "priority": "1",
            "weight": "1",
            "order": "1",
            "Description": ""
        }
        self._insert_goal_row(new_goal)

    def _remove_selected_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def _import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Goal Table CSV",
            os.path.expanduser("~"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                imported_goals = []
                with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        goal = {col: row.get(col, "") for col in GOAL_COLUMNS}
                        imported_goals.append(goal)

                self.goals = imported_goals
                self._load_goals_to_table()
                QMessageBox.information(self, "RTC-Tools", f"Imported {len(imported_goals)} goals from CSV.")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error reading CSV file:\n{str(e)}")

    def _export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Goal Table CSV",
            os.path.expanduser("~/goal_table.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".csv"):
                file_path += ".csv"

            goals_data = self.get_updated_goals()
            try:
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=GOAL_COLUMNS)
                    writer.writeheader()
                    for g in goals_data:
                        writer.writerow(g)

                QMessageBox.information(self, "RTC-Tools", f"Goal table exported successfully to '{file_path}'")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error writing CSV file:\n{str(e)}")

    def get_updated_goals(self):
        """Collects current rows from the QTableWidget into a list of goal dictionaries."""
        updated_goals = []
        for row in range(self.table.rowCount()):
            goal = {}
            for col_idx, col_name in enumerate(GOAL_COLUMNS):
                if col_name in ["state", "active", "goal_type", "target_data_type"]:
                    widget = self.table.cellWidget(row, col_idx)
                    if isinstance(widget, QComboBox):
                        goal[col_name] = widget.currentText().strip()
                    else:
                        goal[col_name] = ""
                else:
                    item = self.table.item(row, col_idx)
                    goal[col_name] = item.text().strip() if item else ""
            updated_goals.append(goal)
        return updated_goals
