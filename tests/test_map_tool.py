import unittest
from qgis.core import QgsPointXY
from qgis.gui import QgsMapCanvas
from RTC_Tools_QGIS_Plugin.model_manager import ModelManager
from RTC_Tools_QGIS_Plugin.map_tool import AddElementMapTool, MoveNodeMapTool

class TestMapTools(unittest.TestCase):
    def setUp(self):
        from qgis.core import QgsProject
        QgsProject.instance().removeAllMapLayers()
        self.canvas = QgsMapCanvas()
        self.canvas.resize(800, 600)
        self.mm = ModelManager(None)

    def tearDown(self):
        from qgis.core import QgsProject
        QgsProject.instance().removeAllMapLayers()

    def test_move_tool_start_moving_element(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")
        self.mm.add_branch("Node 1", "Node 2", name="Branch 1")

        move_tool = MoveNodeMapTool(self.canvas, self.mm)
        elem = self.mm.get_element("Node 1")
        move_tool.start_moving_element(elem)

        self.assertIsNotNone(move_tool.moving_element)
        self.assertEqual(move_tool.moving_element["name"], "Node 1")
        self.assertIsNotNone(move_tool.node_rubber_band)
        self.assertEqual(len(move_tool.branch_rubber_bands), 1)

        # Finish move
        move_tool._finish_move(QgsPointXY(15.0, 25.0))
        self.assertIsNone(move_tool.moving_element)
        self.assertIsNone(move_tool.node_rubber_band)
        self.assertEqual(len(move_tool.branch_rubber_bands), 0)

        # Verify manager updated
        updated = self.mm.get_element("Node 1")
        self.assertEqual(updated["location"]["x"], 15.0)
        self.assertEqual(updated["location"]["y"], 25.0)

    def test_move_tool_cancel_move(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        move_tool = MoveNodeMapTool(self.canvas, self.mm)
        elem = self.mm.get_element("Node 1")
        move_tool.start_moving_element(elem)

        # Cancel
        move_tool._cancel_move()
        self.assertIsNone(move_tool.moving_element)
        self.assertIsNone(move_tool.node_rubber_band)

        # Position should remain unchanged
        node = self.mm.get_element("Node 1")
        self.assertEqual(node["location"]["x"], 10.0)
        self.assertEqual(node["location"]["y"], 20.0)

    def test_move_tool_rubber_band_update(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")
        self.mm.add_branch("Node 1", "Node 2", name="Branch 1")

        move_tool = MoveNodeMapTool(self.canvas, self.mm)
        move_tool.start_moving_element(self.mm.get_element("Node 1"))

        # Simulate mouse move update
        move_tool._update_rubber_bands(QgsPointXY(12.0, 22.0))
        self.assertIsNotNone(move_tool.node_rubber_band)
        self.assertEqual(len(move_tool.branch_rubber_bands), 1)

        move_tool._cancel_move()

    def test_add_tool_signals(self):
        add_tool = AddElementMapTool(self.canvas, self.mm)
        deactivated_called = []
        add_tool.deactivated.connect(lambda: deactivated_called.append(True))
        add_tool.deactivate()
        self.assertEqual(len(deactivated_called), 1)

if __name__ == "__main__":
    unittest.main()


