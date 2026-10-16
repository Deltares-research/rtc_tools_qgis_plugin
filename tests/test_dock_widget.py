import unittest
from unittest.mock import patch
from qgis.core import QgsPointXY
from qgis.gui import QgsMapCanvas
from rtc_tools_qgis_plugin.model_manager import ModelManager
from rtc_tools_qgis_plugin.map_tool import AddElementMapTool, MoveNodeMapTool
from rtc_tools_qgis_plugin.dock_widget import RTCToolsDockWidget
from rtc_tools_qgis_plugin.element_dialog import ElementDialog

class TestDockWidget(unittest.TestCase):
    def setUp(self):
        from qgis.core import QgsProject
        QgsProject.instance().removeAllMapLayers()
        self.canvas = QgsMapCanvas()
        self.canvas.resize(800, 600)
        self.mm = ModelManager(None)
        self.add_tool = AddElementMapTool(self.canvas, self.mm)
        self.move_tool = MoveNodeMapTool(self.canvas, self.mm)
        self.dock = RTCToolsDockWidget(None, self.mm, self.add_tool, move_tool=self.move_tool)

    def tearDown(self):
        from qgis.core import QgsProject
        QgsProject.instance().removeAllMapLayers()

    def test_ui_components_exist(self):
        self.assertIsNotNone(self.dock.btn_add_element)
        self.assertIsNotNone(self.dock.btn_move_element)
        self.assertEqual(self.dock.btn_move_element.text(), "✋ Move Element on Map")
        self.assertIsNotNone(self.dock.btn_move)
        self.assertEqual(self.dock.btn_move.text(), "Move")
        self.assertIsNotNone(self.dock.table_elements)

    def test_table_refresh_on_move(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.assertEqual(self.dock.table_elements.rowCount(), 1)
        self.assertEqual(self.dock.table_elements.item(0, 2).text(), "10.0000")
        self.assertEqual(self.dock.table_elements.item(0, 3).text(), "20.0000")

        # Move the element
        self.mm.move_element("Node 1", QgsPointXY(75.5, 85.25))

        # Check table updated automatically via signals
        self.assertEqual(self.dock.table_elements.item(0, 2).text(), "75.5000")
        self.assertEqual(self.dock.table_elements.item(0, 3).text(), "85.2500")

    def test_element_dialog_coordinate_editing(self):
        elem_data = {
            "name": "Node 1",
            "type": "Node",
            "location": {"x": 10.0, "y": 20.0},
            "properties": {}
        }
        dlg = ElementDialog(elem_data)
        self.assertEqual(dlg.txt_x.text(), "10.0")
        self.assertEqual(dlg.txt_y.text(), "20.0")

        # Simulate user changing coordinates
        dlg.txt_x.setText("42.5")
        dlg.txt_y.setText("99.1")

        updated = dlg.get_updated_data()
        self.assertIn("location", updated)
        self.assertEqual(updated["location"]["x"], 42.5)
        self.assertEqual(updated["location"]["y"], 99.1)

    def test_element_dialog_invalid_coordinates_raise_value_error(self):
        elem_data = {
            "name": "Node 1",
            "type": "Node",
            "location": {"x": 10.0, "y": 20.0},
            "properties": {}
        }
        dlg = ElementDialog(elem_data)
        for bad_val in ["not_a_number", "nan", "inf", "-inf"]:
            dlg.txt_x.setText(bad_val)
            with self.assertRaises(ValueError):
                dlg.get_updated_data()
        dlg.txt_x.setText("10.0")
        for bad_val in ["not_a_number", "nan", "inf", "-inf"]:
            dlg.txt_y.setText(bad_val)
            with self.assertRaises(ValueError):
                dlg.get_updated_data()

    @patch("rtc_tools_qgis_plugin.element_dialog.QMessageBox.warning")
    def test_element_dialog_accept_validation(self, mock_warning):
        elem_data = {
            "name": "Node 1",
            "type": "Node",
            "location": {"x": 10.0, "y": 20.0},
            "properties": {}
        }
        dlg = ElementDialog(elem_data)

        # Empty name should be rejected
        dlg.txt_name.setText("")
        dlg.accept()
        self.assertTrue(mock_warning.called)
        self.assertNotEqual(dlg.result(), ElementDialog.Accepted)

        # Non-numeric or non-finite X should be rejected
        for bad_x in ["abc", "nan", "inf", "-inf"]:
            mock_warning.reset_mock()
            dlg.txt_name.setText("Node 1")
            dlg.txt_x.setText(bad_x)
            dlg.accept()
            self.assertTrue(mock_warning.called)
            self.assertNotEqual(dlg.result(), ElementDialog.Accepted)

        # Non-numeric or non-finite Y should be rejected
        for bad_y in ["xyz", "nan", "inf", "-inf"]:
            mock_warning.reset_mock()
            dlg.txt_x.setText("10.0")
            dlg.txt_y.setText(bad_y)
            dlg.accept()
            self.assertTrue(mock_warning.called)
            self.assertNotEqual(dlg.result(), ElementDialog.Accepted)

        # Valid input should be accepted
        dlg.txt_y.setText("25.0")
        dlg.accept()
        self.assertEqual(dlg.result(), ElementDialog.Accepted)

    def test_dock_constructor_positional_parent_compatibility(self):
        from qgis.PyQt.QtWidgets import QWidget
        parent_widget = QWidget()
        dock = RTCToolsDockWidget(None, self.mm, self.add_tool, parent_widget)
        self.assertEqual(dock.parentWidget(), parent_widget)

    def test_element_dialog_branch_type_locked(self):
        branch_data = {
            "name": "Branch 1",
            "type": "Branch",
            "from_element": "Node 1",
            "to_element": "Node 2",
            "properties": {}
        }
        dlg = ElementDialog(branch_data)
        self.assertFalse(dlg.combo_type.isEnabled())
        self.assertEqual(dlg.combo_type.currentText(), "Branch")

        node_data = {
            "name": "Node 1",
            "type": "Node",
            "location": {"x": 10.0, "y": 20.0},
            "properties": {}
        }
        dlg_node = ElementDialog(node_data)
        self.assertTrue(dlg_node.combo_type.isEnabled())
        self.assertEqual(dlg_node.combo_type.findText("Branch"), -1)

    def test_on_element_placed_handles_none_safely(self):
        # Should not raise AttributeError when None or when iface is None
        self.dock._on_element_placed(None)
        self.dock._on_element_placed({"name": "Node 1", "type": "Node"})

    def test_model_name_and_working_dir_ui_components_and_sync(self):
        from rtc_tools_qgis_plugin.dock_widget import CollapsibleGroupBox
        self.assertIsNotNone(self.dock.txt_model_name)
        self.assertIsNotNone(self.dock.txt_working_dir)
        self.assertIsNotNone(self.dock.btn_browse_working_dir)
        self.assertEqual(self.dock.btn_export.text(), "💾 Save")
        self.assertEqual(self.dock.btn_save_as.text(), "💾➕ Save as")
        self.assertEqual(self.dock.btn_import.text(), "📂 Open")
        self.assertEqual(self.dock.btn_close.text(), "❌ Close")
        self.assertFalse(hasattr(self.dock, "btn_export_mo"))

        # Verify "Model File" is the first section in the main layout
        main_layout = self.dock.widget().widget().layout()
        groups = [
            main_layout.itemAt(i).widget()
            for i in range(main_layout.count())
            if isinstance(main_layout.itemAt(i).widget(), CollapsibleGroupBox)
        ]
        self.assertGreater(len(groups), 0)
        self.assertEqual(groups[0].title(), "Model File")

        self.dock.txt_model_name.setText("BlueRiver")
        self.dock.txt_working_dir.setText("/tmp/work")
        self.assertEqual(self.mm.get_model_name(), "BlueRiver")
        self.assertEqual(self.mm.get_working_dir(), __import__("os").path.abspath("/tmp/work"))

    @patch("rtc_tools_qgis_plugin.dock_widget.QFileDialog.getOpenFileName")
    def test_close_model_and_open_another(self, mock_open_file):
        import os
        import shutil
        import tempfile

        work_dir = tempfile.mkdtemp()
        try:
            # Create and save first model
            self.mm.add_element(QgsPointXY(0.0, 0.0), element_type="Inflow", name="Inflow 1")
            self.mm.add_element(QgsPointXY(10.0, 10.0), element_type="Level", name="Level 1")
            self.mm.add_branch("Inflow 1", "Level 1", name="Branch 1")
            self.dock.set_model_name("ModelOne")
            self.dock.set_working_dir(work_dir)
            self.dock._export_model()

            model_one_json = os.path.join(work_dir, "ModelOne", "ModelOne.json")
            self.assertTrue(os.path.isfile(model_one_json))

            # Close current model
            self.dock._close_model()
            self.assertEqual(self.mm.get_all_elements(), [])
            self.assertEqual(self.dock.table_elements.rowCount(), 0)
            self.assertEqual(self.dock.txt_model_name.text(), "")
            self.assertEqual(self.dock.txt_working_dir.text(), "")
            self.assertEqual(self.mm.get_model_name(), "")
            self.assertEqual(self.mm.get_working_dir(), "")
            self.assertIsNone(self.mm.last_saved_json_path)

            # Open the saved model
            mock_open_file.return_value = (model_one_json, "JSON Files (*.json)")
            self.dock._import_model()
            self.assertEqual(len(self.mm.get_all_elements()), 3)
            self.assertEqual(self.dock.table_elements.rowCount(), 3)
            self.assertEqual(self.dock.txt_model_name.text(), "ModelOne")
            self.assertEqual(self.dock.txt_working_dir.text(), os.path.abspath(work_dir))
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def test_csv_column_import_dialog_and_timeseries_import(self):
        import os
        import tempfile
        from qgis.PyQt.QtWidgets import QDialog
        from rtc_tools_qgis_plugin.timeseries_import_dialog import (
            CsvColumnImportDialog,
            TimeseriesImportDialog,
            SeriesValuesDialog,
            _read_csv_rows,
        )

        csv_content = (
            "DateTime,Inflow_1,Inflow_2\n"
            "2026-01-01 00:00:00,12.5,100.0\n"
            "2026-01-01 01:00:00,15.0,110.0\n"
            "2026-01-01 02:00:00,18.25,120.0\n"
            "2026-01-01 03:00:00,20.0,130.0\n"
        )
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        tmp.write(csv_content)
        tmp.close()

        try:
            rows = _read_csv_rows(tmp.name)
            self.assertEqual(len(rows), 5)

            # Test selecting Column 1 (DateTime), rows 2 to 4
            col_dlg = CsvColumnImportDialog(rows, file_path=tmp.name)
            col_dlg.combo_column.setCurrentIndex(0)
            col_dlg.spin_start_row.setValue(2)
            col_dlg.spin_end_row.setValue(4)
            col_dlg.accept()
            self.assertEqual(col_dlg.result(), QDialog.Accepted)
            dts = col_dlg.get_selected_values()
            self.assertEqual(dts, [
                "2026-01-01 00:00:00",
                "2026-01-01 01:00:00",
                "2026-01-01 02:00:00",
            ])

            # Test selecting Column 2 (Inflow_1), rows 2 to 4
            col_dlg.combo_column.setCurrentIndex(1)
            vals = col_dlg.get_selected_values()
            self.assertEqual(vals, ["12.5", "15.0", "18.25"])

            # Test SeriesValuesDialog CSV import using selected column and row range
            series_dlg = SeriesValuesDialog("Inflow_1", dts)
            with patch("rtc_tools_qgis_plugin.timeseries_import_dialog.QFileDialog.getOpenFileName", return_value=(tmp.name, "CSV Files (*.csv)")), \
                 patch.object(CsvColumnImportDialog, "exec_", return_value=QDialog.Accepted), \
                 patch.object(CsvColumnImportDialog, "get_selected_values", return_value=vals):
                series_dlg._import_csv()

            self.assertEqual(series_dlg.get_events(), {
                "2026-01-01 00:00:00": "12.5",
                "2026-01-01 01:00:00": "15.0",
                "2026-01-01 02:00:00": "18.25",
            })

            # Test TimeseriesImportDialog Tab 1 CSV import
            ts_dlg = TimeseriesImportDialog()
            with patch("rtc_tools_qgis_plugin.timeseries_import_dialog.QFileDialog.getOpenFileName", return_value=(tmp.name, "CSV Files (*.csv)")), \
                 patch.object(CsvColumnImportDialog, "exec_", return_value=QDialog.Accepted), \
                 patch.object(CsvColumnImportDialog, "get_selected_values", return_value=dts):
                ts_dlg._import_dt_csv()

            self.assertEqual(ts_dlg.get_updated_data()["datetimes"], dts)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    @patch("rtc_tools_qgis_plugin.dock_widget.QFileDialog.getExistingDirectory")
    @patch("rtc_tools_qgis_plugin.dock_widget.QInputDialog.getText")
    def test_construct_and_save_use_gui_fields_without_prompting(self, mock_get_text, mock_get_dir):
        import os
        import shutil
        import tempfile

        work_dir = tempfile.mkdtemp()
        try:
            self.mm.add_element(QgsPointXY(0.0, 0.0), element_type="Inflow", name="Inflow 1")
            self.mm.add_element(QgsPointXY(10.0, 10.0), element_type="Level", name="Level 1")
            self.mm.add_branch("Inflow 1", "Level 1", name="Branch 1")

            self.dock.txt_model_name.setText("BlueRiver")
            self.dock.txt_working_dir.setText(work_dir)

            self.dock._construct_rtc_tools_model()

            # Should not prompt since model name and working folder are already specified
            mock_get_text.assert_not_called()
            mock_get_dir.assert_not_called()

            model_dir = os.path.join(work_dir, "BlueRiver")
            json_path = os.path.join(model_dir, "BlueRiver.json")
            self.assertTrue(os.path.isfile(json_path))
            self.assertTrue(os.path.isdir(os.path.join(model_dir, "input")))
            self.assertTrue(os.path.isdir(os.path.join(model_dir, "model")))
            self.assertTrue(os.path.isdir(os.path.join(model_dir, "output")))
            self.assertTrue(os.path.isdir(os.path.join(model_dir, "src")))

            # Subsequent save and construct actions also do not prompt
            self.mm.move_element("Level 1", QgsPointXY(20.0, 30.0))
            self.dock._export_model()
            self.dock._construct_rtc_tools_model()
            mock_get_text.assert_not_called()
            mock_get_dir.assert_not_called()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    @patch("rtc_tools_qgis_plugin.dock_widget.QFileDialog.getExistingDirectory")
    @patch("rtc_tools_qgis_plugin.dock_widget.QInputDialog.getText")
    def test_prompt_once_then_remember_and_save_as(self, mock_get_text, mock_get_dir):
        import os
        import shutil
        import tempfile

        work_dir_1 = tempfile.mkdtemp()
        work_dir_2 = tempfile.mkdtemp()
        try:
            self.mm.add_element(QgsPointXY(0.0, 0.0), element_type="Inflow", name="Inflow 1")
            self.mm.add_element(QgsPointXY(10.0, 10.0), element_type="Level", name="Level 1")
            self.mm.add_branch("Inflow 1", "Level 1", name="Branch 1")

            mock_get_text.return_value = ("BlueRiver", True)
            mock_get_dir.return_value = work_dir_1

            # 1st construct prompts because fields are initially empty
            self.dock._construct_rtc_tools_model()
            self.assertEqual(mock_get_text.call_count, 1)
            self.assertEqual(mock_get_dir.call_count, 1)
            self.assertEqual(self.dock.txt_model_name.text(), "BlueRiver")
            self.assertEqual(self.dock.txt_working_dir.text(), os.path.abspath(work_dir_1))
            self.assertTrue(os.path.isfile(os.path.join(work_dir_1, "BlueRiver", "BlueRiver.json")))

            # 2nd construct and save do NOT prompt again
            mock_get_text.reset_mock()
            mock_get_dir.reset_mock()
            self.dock._construct_rtc_tools_model()
            self.dock._export_model()
            mock_get_text.assert_not_called()
            mock_get_dir.assert_not_called()

            # Save Model As prompts for new name and location and updates GUI
            mock_get_text.return_value = ("GreenRiver", True)
            mock_get_dir.return_value = work_dir_2
            self.dock._save_model_as()
            self.assertEqual(mock_get_text.call_count, 1)
            self.assertEqual(mock_get_dir.call_count, 1)
            self.assertEqual(self.dock.txt_model_name.text(), "GreenRiver")
            self.assertEqual(self.dock.txt_working_dir.text(), os.path.abspath(work_dir_2))
            self.assertTrue(os.path.isfile(os.path.join(work_dir_2, "GreenRiver", "GreenRiver.json")))

            # Subsequent Construct RTC-Tools Model uses GreenRiver & work_dir_2 without prompting
            mock_get_text.reset_mock()
            mock_get_dir.reset_mock()
            self.dock._construct_rtc_tools_model()
            mock_get_text.assert_not_called()
            mock_get_dir.assert_not_called()
            self.assertTrue(os.path.isfile(os.path.join(work_dir_2, "GreenRiver", "model", "GreenRiver.mo")))
        finally:
            shutil.rmtree(work_dir_1, ignore_errors=True)
            shutil.rmtree(work_dir_2, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()


