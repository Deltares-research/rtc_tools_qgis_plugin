import unittest
from qgis.core import QgsPointXY
from qgis.gui import QgsMapCanvas
from RTC_Tools_QGIS_Plugin.model_manager import ModelManager
from RTC_Tools_QGIS_Plugin.map_tool import AddElementMapTool, MoveNodeMapTool
from RTC_Tools_QGIS_Plugin.dock_widget import RTCToolsDockWidget
from RTC_Tools_QGIS_Plugin.element_dialog import ElementDialog

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

if __name__ == "__main__":
    unittest.main()


