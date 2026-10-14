import unittest
import tempfile
import json
import os
from qgis.core import QgsPointXY
from rtc_tools_qgis_plugin.model_manager import ModelManager

class TestModelManager(unittest.TestCase):
    def setUp(self):
        from qgis.core import QgsProject
        QgsProject.instance().removeAllMapLayers()
        self.mm = ModelManager(None)

    def tearDown(self):
        from qgis.core import QgsProject
        QgsProject.instance().removeAllMapLayers()

    def test_add_point_elements(self):
        node = self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.assertEqual(node["name"], "Node 1")
        self.assertEqual(node["type"], "Node")
        self.assertEqual(node["location"]["x"], 10.0)
        self.assertEqual(node["location"]["y"], 20.0)

        inflow = self.mm.add_element(QgsPointXY(0.0, 0.0), element_type="Inflow", name="Inflow 1")
        self.assertEqual(inflow["name"], "Inflow 1")
        self.assertEqual(inflow["type"], "Inflow")

    def test_add_branch(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")
        branch = self.mm.add_branch("Node 1", "Node 2", name="Branch 1")

        self.assertIsNotNone(branch)
        self.assertEqual(branch["from_element"], "Node 1")
        self.assertEqual(branch["to_element"], "Node 2")

        b_feat = list(self.mm.branches_layer.getFeatures())[0]
        polyline = b_feat.geometry().asPolyline()
        self.assertEqual(polyline[0], QgsPointXY(10.0, 20.0))
        self.assertEqual(polyline[1], QgsPointXY(30.0, 40.0))

    def test_move_element_point_geometry(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        updated = self.mm.move_element("Node 1", QgsPointXY(50.0, 60.0))

        self.assertIsNotNone(updated)
        self.assertEqual(updated["location"]["x"], 50.0)
        self.assertEqual(updated["location"]["y"], 60.0)

        # Check retrieval from manager
        retrieved = self.mm.get_element("Node 1")
        self.assertEqual(retrieved["location"]["x"], 50.0)
        self.assertEqual(retrieved["location"]["y"], 60.0)

    def test_move_element_connected_branches(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")
        self.mm.add_element(QgsPointXY(50.0, 60.0), element_type="Node", name="Node 3")

        self.mm.add_branch("Node 1", "Node 2", name="Branch 1")
        self.mm.add_branch("Node 2", "Node 3", name="Branch 2")

        # Move intermediate Node 2 to (35.0, 45.0)
        self.mm.move_element("Node 2", QgsPointXY(35.0, 45.0))

        # Branch 1 (Node 1 -> Node 2) end point should be (35.0, 45.0)
        b1_feat = [f for f in self.mm.branches_layer.getFeatures() if f.attribute("name") == "Branch 1"][0]
        b1_pts = b1_feat.geometry().asPolyline()
        self.assertEqual(b1_pts[0], QgsPointXY(10.0, 20.0))
        self.assertEqual(b1_pts[1], QgsPointXY(35.0, 45.0))

        # Branch 2 (Node 2 -> Node 3) start point should be (35.0, 45.0)
        b2_feat = [f for f in self.mm.branches_layer.getFeatures() if f.attribute("name") == "Branch 2"][0]
        b2_pts = b2_feat.geometry().asPolyline()
        self.assertEqual(b2_pts[0], QgsPointXY(35.0, 45.0))
        self.assertEqual(b2_pts[1], QgsPointXY(50.0, 60.0))

    def test_move_element_signals(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")

        moved_events = []
        updated_events = []
        self.mm.elementMoved.connect(lambda d: moved_events.append(d))
        self.mm.elementUpdated.connect(lambda d: updated_events.append(d))

        self.mm.move_element("Node 1", {"x": 25.0, "y": 35.0})

        self.assertEqual(len(moved_events), 1)
        self.assertEqual(moved_events[0]["name"], "Node 1")
        self.assertEqual(moved_events[0]["location"]["x"], 25.0)

        self.assertEqual(len(updated_events), 1)
        self.assertEqual(updated_events[0]["name"], "Node 1")

    def test_update_element_with_new_location(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")
        self.mm.add_branch("Node 1", "Node 2", name="Branch 1")

        # Update both location and properties
        success = self.mm.update_element("Node 1", new_location={"x": 15.0, "y": 25.0}, new_properties={"flow": 10})
        self.assertTrue(success)

        elem = self.mm.get_element("Node 1")
        self.assertEqual(elem["location"]["x"], 15.0)
        self.assertEqual(elem["location"]["y"], 25.0)
        self.assertEqual(elem["properties"].get("flow"), 10)

        # Connected branch must also have updated start point
        b1_feat = list(self.mm.branches_layer.getFeatures())[0]
        self.assertEqual(b1_feat.geometry().asPolyline()[0], QgsPointXY(15.0, 25.0))

    def test_export_import_json_preserves_moved_positions(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")
        self.mm.add_branch("Node 1", "Node 2", name="Branch 1")

        self.mm.move_element("Node 1", QgsPointXY(99.0, 88.0))

        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            self.mm.export_to_json(tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as f:
                data = json.load(f)

            n1 = [e for e in data["elements"] if e["name"] == "Node 1"][0]
            self.assertEqual(n1["location"]["x"], 99.0)
            self.assertEqual(n1["location"]["y"], 88.0)

            # Re-import to a fresh manager
            from qgis.core import QgsProject
            QgsProject.instance().removeAllMapLayers()
            mm2 = ModelManager(None)
            self.assertTrue(mm2.import_from_json(tmp.name))
            n1_imported = mm2.get_element("Node 1")
            self.assertEqual(n1_imported["location"]["x"], 99.0)
            self.assertEqual(n1_imported["location"]["y"], 88.0)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_update_element_name_collision_does_not_move(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")
        self.mm.add_element(QgsPointXY(30.0, 40.0), element_type="Node", name="Node 2")

        # Attempt to rename Node 1 to Node 2 (collision) while also passing a new location
        success = self.mm.update_element("Node 1", new_name="Node 2", new_location={"x": 50.0, "y": 60.0})
        self.assertFalse(success)

        # Node 1 position must NOT have changed
        elem1 = self.mm.get_element("Node 1")
        self.assertEqual(elem1["location"]["x"], 10.0)
        self.assertEqual(elem1["location"]["y"], 20.0)

    def test_update_element_invalid_location_fails(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")

        # Pass invalid location strings and non-finite numbers
        for bad_loc in ["invalid_coords", {"x": float("nan"), "y": 20.0}, {"x": 10.0, "y": float("inf")}, (float("-inf"), 0.0)]:
            success = self.mm.update_element("Node 1", new_location=bad_loc)
            self.assertFalse(success)

        # Position should remain unchanged
        elem = self.mm.get_element("Node 1")
        self.assertEqual(elem["location"]["x"], 10.0)
        self.assertEqual(elem["location"]["y"], 20.0)

    def test_move_element_non_finite_coordinates_fails(self):
        self.mm.add_element(QgsPointXY(10.0, 20.0), element_type="Node", name="Node 1")

        self.assertIsNone(self.mm.move_element("Node 1", {"x": float("nan"), "y": 20.0}))
        self.assertIsNone(self.mm.move_element("Node 1", {"x": 10.0, "y": float("inf")}))
        self.assertIsNone(self.mm.move_element("Node 1", [float("-inf"), float("nan")]))
        self.assertIsNone(self.mm.move_element("Node 1", QgsPointXY(float("nan"), 20.0)))

        elem = self.mm.get_element("Node 1")
        self.assertEqual(elem["location"]["x"], 10.0)
        self.assertEqual(elem["location"]["y"], 20.0)

    def test_add_element_non_finite_coordinates_fails(self):
        self.assertIsNone(self.mm.add_element(QgsPointXY(float("nan"), 20.0), name="Bad1"))
        self.assertIsNone(self.mm.add_element(QgsPointXY(10.0, float("inf")), name="Bad2"))

if __name__ == "__main__":
    unittest.main()


