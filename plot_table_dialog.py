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

PLOT_COLUMNS = [
    "id",
    "y_axis_title",
    "variables_style_1",
    "variables_style_2",
    "custom_title",
    "specified_in"
]

class PlotTableDialog(QDialog):
    """Dialog for defining and editing the RTC-Tools Plot Table."""

    def __init__(self, plots=None, model_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RTC-Tools Plot Table Editor")
        self.resize(900, 450)

        self.plots = [dict(p) for p in (plots or [])]
        self.model_manager = model_manager

        self._init_ui()
        self._load_plots_to_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<b>RTC-Tools Plot Table Configuration</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Table Widget
        self.table = QTableWidget(0, len(PLOT_COLUMNS))
        self.table.setHorizontalHeaderLabels(PLOT_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Control buttons for table rows
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕ Add Plot")
        btn_add.clicked.connect(self._add_plot_row)

        btn_remove = QPushButton("➖ Remove Selected")
        btn_remove.clicked.connect(self._remove_selected_row)

        btn_import_csv = QPushButton("📂 Import Plots from CSV...")
        btn_import_csv.clicked.connect(self._import_csv)

        btn_export_csv = QPushButton("📊 Export Plots to CSV...")
        btn_export_csv.clicked.connect(self._export_csv)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_import_csv)
        btn_layout.addWidget(btn_export_csv)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Dialog accept/cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_plots_to_table(self):
        self.table.setRowCount(0)
        for plot in self.plots:
            self._insert_plot_row(plot)

    def _insert_plot_row(self, plot_data):
        row = self.table.rowCount()
        self.table.insertRow(row)

        for col_idx, col_name in enumerate(PLOT_COLUMNS):
            val = str(plot_data.get(col_name, "") if plot_data.get(col_name) is not None else "")

            if col_name == "specified_in":
                combo = QComboBox()
                combo.addItem("goal_generator")
                combo.setCurrentText("goal_generator")
                self.table.setCellWidget(row, col_idx, combo)
            else:
                item = QTableWidgetItem(val)
                self.table.setItem(row, col_idx, item)

    def _add_plot_row(self):
        row_count = self.table.rowCount() + 1
        new_plot = {
            "id": f"Plot_{row_count}",
            "y_axis_title": "",
            "variables_style_1": "",
            "variables_style_2": "",
            "custom_title": "",
            "specified_in": "goal_generator"
        }
        self._insert_plot_row(new_plot)

    def _remove_selected_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def _import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Plot Table CSV",
            os.path.expanduser("~"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            try:
                imported_plots = []
                with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        plot = {col: row.get(col, "") for col in PLOT_COLUMNS}
                        plot["specified_in"] = "goal_generator"
                        imported_plots.append(plot)

                self.plots = imported_plots
                self._load_plots_to_table()
                QMessageBox.information(self, "RTC-Tools", f"Imported {len(imported_plots)} plots from CSV.")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error reading CSV file:\n{str(e)}")

    def _export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot Table CSV",
            os.path.expanduser("~/plot_table.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith(".csv"):
                file_path += ".csv"

            plots_data, is_valid, err_msg = self._collect_and_validate()
            if not is_valid:
                QMessageBox.warning(self, "RTC-Tools Plot Table", err_msg)
                return

            try:
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=PLOT_COLUMNS)
                    writer.writeheader()
                    for p in plots_data:
                        writer.writerow(p)

                QMessageBox.information(self, "RTC-Tools", f"Plot table exported successfully to '{file_path}'")
            except Exception as e:
                QMessageBox.critical(self, "RTC-Tools", f"Error writing CSV file:\n{str(e)}")

    def _collect_and_validate(self):
        plots = []
        seen_ids = set()

        for row in range(self.table.rowCount()):
            plot = {}
            for col_idx, col_name in enumerate(PLOT_COLUMNS):
                if col_name == "specified_in":
                    widget = self.table.cellWidget(row, col_idx)
                    plot[col_name] = widget.currentText().strip() if isinstance(widget, QComboBox) else "goal_generator"
                else:
                    item = self.table.item(row, col_idx)
                    plot[col_name] = item.text().strip() if item else ""

            plot_id = plot.get("id", "")
            if not plot_id:
                return [], False, f"Row {row + 1} has an empty 'id'. All plot rows must have a unique ID."

            if plot_id in seen_ids:
                return [], False, f"Duplicate ID '{plot_id}' found at row {row + 1}. All plot IDs must be unique."

            seen_ids.add(plot_id)
            plot["specified_in"] = "goal_generator"
            plots.append(plot)

        return plots, True, ""

    def _validate_and_accept(self):
        plots, is_valid, err_msg = self._collect_and_validate()
        if not is_valid:
            QMessageBox.warning(self, "RTC-Tools Plot Table", err_msg)
            return

        self.plots = plots
        self.accept()

    def get_updated_plots(self):
        """Returns the current validated plot list."""
        plots, is_valid, _ = self._collect_and_validate()
        return plots if is_valid else self.plots
