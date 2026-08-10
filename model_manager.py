import json
import os
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsProject,
    QgsMarkerSymbol,
    QgsLineSymbol,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
)
from qgis.PyQt.QtCore import QObject, pyqtSignal, QVariant
from qgis.PyQt.QtGui import QColor

class ModelManager(QObject):
    """Manages RTC-Tools point elements and line branch connections in QGIS vector layers."""

    # Signals
    elementAdded = pyqtSignal(dict)
    elementUpdated = pyqtSignal(dict)
    elementRemoved = pyqtSignal(str)
    modelCleared = pyqtSignal()
    layerCreated = pyqtSignal(object)

    NODES_LAYER_NAME = "RTC-Tools Elements"
    BRANCHES_LAYER_NAME = "RTC-Tools Branches"

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.nodes_layer = None
        self.branches_layer = None
        self._element_counter = 0

    def get_canvas_crs(self):
        """Returns current canvas CRS auth ID (e.g. 'EPSG:4326')."""
        if self.iface and self.iface.mapCanvas():
            return self.iface.mapCanvas().mapSettings().destinationCrs().authid()
        return "EPSG:4326"

    def get_or_create_nodes_layer(self):
        """Retrieves or creates the memory vector layer for point elements."""
        if self.nodes_layer and QgsProject.instance().mapLayer(self.nodes_layer.id()):
            return self.nodes_layer

        existing = QgsProject.instance().mapLayersByName(self.NODES_LAYER_NAME)
        if existing:
            self.nodes_layer = existing[0]
            self._sync_counter()
            return self.nodes_layer

        crs_str = self.get_canvas_crs()
        self.nodes_layer = QgsVectorLayer(f"Point?crs={crs_str}", self.NODES_LAYER_NAME, "memory")
        
        provider = self.nodes_layer.dataProvider()
        provider.addAttributes([
            QgsField("id", QVariant.String),
            QgsField("name", QVariant.String),
            QgsField("type", QVariant.String),
            QgsField("properties", QVariant.String),
        ])
        self.nodes_layer.updateFields()

        self._setup_nodes_layer_style()
        QgsProject.instance().addMapLayer(self.nodes_layer)
        self.layerCreated.emit(self.nodes_layer)
        return self.nodes_layer

    def get_or_create_branches_layer(self):
        """Retrieves or creates the memory vector layer for branch connections."""
        if self.branches_layer and QgsProject.instance().mapLayer(self.branches_layer.id()):
            return self.branches_layer

        existing = QgsProject.instance().mapLayersByName(self.BRANCHES_LAYER_NAME)
        if existing:
            self.branches_layer = existing[0]
            self._sync_counter()
            return self.branches_layer

        crs_str = self.get_canvas_crs()
        self.branches_layer = QgsVectorLayer(f"LineString?crs={crs_str}", self.BRANCHES_LAYER_NAME, "memory")

        provider = self.branches_layer.dataProvider()
        provider.addAttributes([
            QgsField("id", QVariant.String),
            QgsField("name", QVariant.String),
            QgsField("type", QVariant.String),
            QgsField("from_element", QVariant.String),
            QgsField("to_element", QVariant.String),
            QgsField("properties", QVariant.String),
        ])
        self.branches_layer.updateFields()

        self._setup_branches_layer_style()
        QgsProject.instance().addMapLayer(self.branches_layer)
        self.layerCreated.emit(self.branches_layer)
        return self.branches_layer

    def get_or_create_layers(self):
        """Ensures both point elements layer and branch line layer are active."""
        nodes = self.get_or_create_nodes_layer()
        branches = self.get_or_create_branches_layer()
        return nodes, branches

    def _setup_nodes_layer_style(self):
        """Applies categorized symbols and labels to point elements."""
        if not self.nodes_layer:
            return

        # 1. Inflow: Upside down triangle
        sym_inflow = QgsMarkerSymbol.createSimple({
            "name": "triangle",
            "angle": "180",
            "color": "#E74C3C",
            "outline_color": "#FFFFFF",
            "outline_width": "0.6",
            "size": "5.0"
        })
        cat_inflow = QgsRendererCategory("Inflow", sym_inflow, "Inflow")

        # 2. Level / Terminal: Rectangle / square
        sym_level = QgsMarkerSymbol.createSimple({
            "name": "square",
            "color": "#27AE60",
            "outline_color": "#FFFFFF",
            "outline_width": "0.6",
            "size": "5.0"
        })
        cat_level = QgsRendererCategory("Level", sym_level, "Level")

        sym_term = QgsMarkerSymbol.createSimple({
            "name": "square",
            "color": "#8E44AD",
            "outline_color": "#FFFFFF",
            "outline_width": "0.6",
            "size": "5.0"
        })
        cat_term = QgsRendererCategory("Terminal", sym_term, "Terminal")

        # 3. Node: Circle
        sym_node = QgsMarkerSymbol.createSimple({
            "name": "circle",
            "color": "#1E508C",
            "outline_color": "#FFFFFF",
            "outline_width": "0.6",
            "size": "4.5"
        })
        cat_node = QgsRendererCategory("Node", sym_node, "Node")

        # 4. Reservoir: Diamond
        sym_res = QgsMarkerSymbol.createSimple({
            "name": "diamond",
            "color": "#2980B9",
            "outline_color": "#FFFFFF",
            "outline_width": "0.6",
            "size": "5.5"
        })
        cat_res = QgsRendererCategory("Reservoir", sym_res, "Reservoir")

        renderer = QgsCategorizedSymbolRenderer("type", [cat_inflow, cat_level, cat_term, cat_node, cat_res])
        self.nodes_layer.setRenderer(renderer)

        # Labels displaying element name
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = "name"
        label_settings.enabled = True

        text_format = QgsTextFormat()
        text_format.setSize(9)
        text_format.setColor(QColor("#0A2850"))
        label_settings.setFormat(text_format)

        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        self.nodes_layer.setLabeling(labeling)
        self.nodes_layer.setLabelsEnabled(True)

    def _setup_branches_layer_style(self):
        """Applies a thick line symbol and labels to branch connections."""
        if not self.branches_layer:
            return

        line_symbol = QgsLineSymbol.createSimple({
            "color": "#2C3E50",
            "width": "1.2",
            "line_style": "solid"
        })
        renderer = QgsSingleSymbolRenderer(line_symbol)
        self.branches_layer.setRenderer(renderer)

        # Labels displaying branch name
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = "name"
        label_settings.enabled = True

        text_format = QgsTextFormat()
        text_format.setSize(8)
        text_format.setColor(QColor("#2C3E50"))
        label_settings.setFormat(text_format)

        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        self.branches_layer.setLabeling(labeling)
        self.branches_layer.setLabelsEnabled(True)

    def _sync_counter(self):
        """Synchronizes element ID counter from existing layers."""
        max_idx = 0
        layers = [self.nodes_layer, self.branches_layer]
        for lyr in layers:
            if not lyr:
                continue
            for feat in lyr.getFeatures():
                elem_id = str(feat.attribute("id") or "")
                if "_" in elem_id:
                    try:
                        num = int(elem_id.split("_")[-1])
                        if num > max_idx:
                            max_idx = num
                    except ValueError:
                        pass
        self._element_counter = max_idx

    def generate_next_id(self, element_type="Node"):
        """Generates a unique element ID."""
        self._element_counter += 1
        prefix = element_type.lower().replace(" ", "_")
        return f"{prefix}_{self._element_counter}"

    def add_element(self, point, element_type="Node", name=None, properties=None):
        """Adds a point element feature to the memory layer."""
        nodes_layer = self.get_or_create_nodes_layer()

        elem_id = self.generate_next_id(element_type)
        if not name:
            name = f"{element_type} {self._element_counter}"
        if properties is None:
            properties = {}

        feature = QgsFeature(nodes_layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttribute("id", elem_id)
        feature.setAttribute("name", name)
        feature.setAttribute("type", element_type)
        feature.setAttribute("properties", json.dumps(properties))

        nodes_layer.dataProvider().addFeatures([feature])
        nodes_layer.updateExtents()
        nodes_layer.triggerRepaint()

        elem_data = {
            "id": elem_id,
            "name": name,
            "type": element_type,
            "location": {"x": point.x(), "y": point.y()},
            "properties": properties
        }
        self.elementAdded.emit(elem_data)
        return elem_data

    def add_branch(self, from_element_id, to_element_id, name=None, properties=None):
        """Adds a line Branch connection between two point elements."""
        from_elem = self.get_element(from_element_id)
        to_elem = self.get_element(to_element_id)

        if not from_elem or not to_elem:
            return None

        pt_from = QgsPointXY(from_elem["location"]["x"], from_elem["location"]["y"])
        pt_to = QgsPointXY(to_elem["location"]["x"], to_elem["location"]["y"])

        branches_layer = self.get_or_create_branches_layer()
        branch_id = self.generate_next_id("Branch")
        if not name:
            name = f"Branch {self._element_counter}"
        if properties is None:
            properties = {}

        feature = QgsFeature(branches_layer.fields())
        feature.setGeometry(QgsGeometry.fromPolylineXY([pt_from, pt_to]))
        feature.setAttribute("id", branch_id)
        feature.setAttribute("name", name)
        feature.setAttribute("type", "Branch")
        feature.setAttribute("from_element", from_element_id)
        feature.setAttribute("to_element", to_element_id)
        feature.setAttribute("properties", json.dumps(properties))

        branches_layer.dataProvider().addFeatures([feature])
        branches_layer.updateExtents()
        branches_layer.triggerRepaint()

        branch_data = {
            "id": branch_id,
            "name": name,
            "type": "Branch",
            "from_element": from_element_id,
            "to_element": to_element_id,
            "upstream": from_element_id,
            "downstream": to_element_id,
            "properties": properties
        }
        self.elementAdded.emit(branch_data)
        return branch_data

    def validate_branch_connection(self, from_element_id, to_element_id):
        """Validates if a branch connection between two elements is permitted."""
        if from_element_id == to_element_id:
            return False, "Cannot connect an element to itself."

        from_elem = self.get_element(from_element_id)
        to_elem = self.get_element(to_element_id)

        if not from_elem or not to_elem:
            return False, "One or both selected elements could not be found."

        from_type = from_elem.get("type")
        to_type = to_elem.get("type")

        # 1. Level / Terminal element has no output (0 outputs)
        if from_type in ["Level", "Terminal"]:
            return False, f"{from_type} element '{from_elem['name']}' cannot have outgoing connections (has no output)."

        # 2. Inflow element has no input (0 inputs)
        if to_type == "Inflow":
            return False, f"Inflow element '{to_elem['name']}' cannot have incoming connections (has no input)."

        # Check existing branch counts
        branches = self.get_branch_elements()

        # Inflow max 1 output
        if from_type == "Inflow":
            out_count = sum(1 for b in branches if b.get("from_element") == from_element_id)
            if out_count >= 1:
                return False, f"Inflow element '{from_elem['name']}' already has its maximum (1) output connection."

        # Level / Terminal max 1 input
        if to_type in ["Level", "Terminal"]:
            in_count = sum(1 for b in branches if b.get("to_element") == to_element_id)
            if in_count >= 1:
                return False, f"{to_type} element '{to_elem['name']}' already has its maximum (1) input connection."

        # Reservoir max 1 inflow (input) and max 1 outflow (output)
        if from_type == "Reservoir":
            out_count = sum(1 for b in branches if b.get("from_element") == from_element_id)
            if out_count >= 1:
                return False, f"Reservoir element '{from_elem['name']}' already has its maximum (1) outflow connection."

        if to_type == "Reservoir":
            in_count = sum(1 for b in branches if b.get("to_element") == to_element_id)
            if in_count >= 1:
                return False, f"Reservoir element '{to_elem['name']}' already has its maximum (1) inflow connection."

        return True, ""

    def validate_model(self):
        """Validates the constructed model topology and element connection constraints.

        Returns:
            tuple: (is_valid: bool, issues: list[str])
        """
        issues = []
        points = self.get_point_elements()
        branches = self.get_branch_elements()

        if not points:
            return False, ["Model contains no point elements."]

        point_ids = {p["id"]: p for p in points}

        # Count inputs and outputs for each point element
        in_counts = {pid: 0 for pid in point_ids}
        out_counts = {pid: 0 for pid in point_ids}

        # 1. Validate branches (each branch must connect valid upstream and downstream elements)
        for b in branches:
            bid = b.get("id")
            bname = b.get("name", bid)
            from_id = b.get("from_element") or b.get("upstream")
            to_id = b.get("to_element") or b.get("downstream")

            if not from_id or not to_id:
                issues.append(f"Branch '{bname}' ({bid}) must have both an upstream and a downstream element.")
                continue

            if from_id not in point_ids:
                issues.append(f"Branch '{bname}' ({bid}) has invalid upstream element '{from_id}'.")
            else:
                out_counts[from_id] += 1

            if to_id not in point_ids:
                issues.append(f"Branch '{bname}' ({bid}) has invalid downstream element '{to_id}'.")
            else:
                in_counts[to_id] += 1

            if from_id == to_id and from_id in point_ids:
                issues.append(f"Branch '{bname}' ({bid}) connects element '{from_id}' to itself.")

        # 2. Validate point element input/output constraints
        for pid, p in point_ids.items():
            ptype = p.get("type")
            pname = p.get("name", pid)
            inputs = in_counts[pid]
            outputs = out_counts[pid]

            if ptype == "Inflow":
                if inputs > 0:
                    issues.append(f"Inflow '{pname}' ({pid}) cannot have inputs (found {inputs}).")
                if outputs != 1:
                    issues.append(f"Inflow '{pname}' ({pid}) must have exactly 1 output (found {outputs}).")

            elif ptype in ["Level", "Terminal"]:
                if outputs > 0:
                    issues.append(f"{ptype} '{pname}' ({pid}) cannot have outputs (found {outputs}).")
                if inputs != 1:
                    issues.append(f"{ptype} '{pname}' ({pid}) must have exactly 1 input (found {inputs}).")

            elif ptype == "Reservoir":
                if inputs != 1:
                    issues.append(f"Reservoir '{pname}' ({pid}) must have exactly 1 input (found {inputs}).")
                if outputs != 1:
                    issues.append(f"Reservoir '{pname}' ({pid}) must have exactly 1 output (found {outputs}).")

            elif ptype == "Node":
                if inputs < 1:
                    issues.append(f"Node '{pname}' ({pid}) must have at least 1 input (found {inputs}).")
                if outputs != 1:
                    issues.append(f"Node '{pname}' ({pid}) must have exactly 1 output (found {outputs}).")

        is_valid = len(issues) == 0
        return is_valid, issues

    def find_nearest_element(self, point, max_distance=None):
        """Finds the nearest point element feature to a canvas click location."""
        if not self.nodes_layer:
            return None

        nearest_elem = None
        min_dist = float("inf")

        if max_distance is None:
            if self.iface and self.iface.mapCanvas():
                extent = self.iface.mapCanvas().extent()
                max_distance = extent.width() * 0.08
            else:
                max_distance = 1000.0

        for feat in self.nodes_layer.getFeatures():
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                dist = geom.distance(QgsGeometry.fromPointXY(point))
                if dist < min_dist and dist <= max_distance:
                    min_dist = dist
                    nearest_elem = self._node_feature_to_dict(feat)

        return nearest_elem

    def update_element(self, element_id, new_name=None, new_type=None, new_properties=None):
        """Updates attributes of an existing point or branch element by ID."""
        # 1. Check point elements layer
        if self.nodes_layer:
            for feat in self.nodes_layer.getFeatures():
                if feat.attribute("id") == element_id:
                    attr_updates = {}
                    fields = self.nodes_layer.fields()

                    if new_name is not None:
                        attr_updates[fields.indexFromName("name")] = new_name
                    if new_type is not None:
                        attr_updates[fields.indexFromName("type")] = new_type
                    if new_properties is not None:
                        attr_updates[fields.indexFromName("properties")] = json.dumps(new_properties)

                    if attr_updates:
                        self.nodes_layer.dataProvider().changeAttributeValues({feat.id(): attr_updates})
                        self.nodes_layer.triggerRepaint()

                    updated_data = self.get_element(element_id)
                    if updated_data:
                        self.elementUpdated.emit(updated_data)
                    return True

        # 2. Check branch line layer
        if self.branches_layer:
            for feat in self.branches_layer.getFeatures():
                if feat.attribute("id") == element_id:
                    attr_updates = {}
                    fields = self.branches_layer.fields()

                    if new_name is not None:
                        attr_updates[fields.indexFromName("name")] = new_name
                    if new_type is not None:
                        attr_updates[fields.indexFromName("type")] = new_type
                    if new_properties is not None:
                        attr_updates[fields.indexFromName("properties")] = json.dumps(new_properties)

                    if attr_updates:
                        self.branches_layer.dataProvider().changeAttributeValues({feat.id(): attr_updates})
                        self.branches_layer.triggerRepaint()

                    updated_data = self.get_element(element_id)
                    if updated_data:
                        self.elementUpdated.emit(updated_data)
                    return True

        return False

    def remove_element(self, element_id):
        """Deletes an element by ID, removing connected branches if a point element is removed."""
        # Check point nodes layer
        if self.nodes_layer:
            for feat in self.nodes_layer.getFeatures():
                if feat.attribute("id") == element_id:
                    self.nodes_layer.dataProvider().deleteFeatures([feat.id()])
                    self.nodes_layer.triggerRepaint()
                    self._remove_branches_connected_to(element_id)
                    self.elementRemoved.emit(element_id)
                    return True

        # Check branches layer
        if self.branches_layer:
            for feat in self.branches_layer.getFeatures():
                if feat.attribute("id") == element_id:
                    self.branches_layer.dataProvider().deleteFeatures([feat.id()])
                    self.branches_layer.triggerRepaint()
                    self.elementRemoved.emit(element_id)
                    return True

        return False

    def _remove_branches_connected_to(self, point_element_id):
        """Removes any branch features connected to a point_element_id."""
        if not self.branches_layer:
            return

        fids_to_del = []
        for feat in self.branches_layer.getFeatures():
            if feat.attribute("from_element") == point_element_id or feat.attribute("to_element") == point_element_id:
                fids_to_del.append(feat.id())

        if fids_to_del:
            self.branches_layer.dataProvider().deleteFeatures(fids_to_del)
            self.branches_layer.triggerRepaint()

    def get_element(self, element_id):
        """Retrieves dictionary representation of an element or branch by ID."""
        if self.nodes_layer:
            for feat in self.nodes_layer.getFeatures():
                if feat.attribute("id") == element_id:
                    return self._node_feature_to_dict(feat)

        if self.branches_layer:
            for feat in self.branches_layer.getFeatures():
                if feat.attribute("id") == element_id:
                    return self._branch_feature_to_dict(feat)

        return None

    def get_point_elements(self):
        """Returns list of dictionaries for all point elements."""
        if not self.nodes_layer:
            return []
        return [self._node_feature_to_dict(f) for f in self.nodes_layer.getFeatures()]

    def get_branch_elements(self):
        """Returns list of dictionaries for all branch elements."""
        if not self.branches_layer:
            return []
        return [self._branch_feature_to_dict(f) for f in self.branches_layer.getFeatures()]

    def get_all_elements(self):
        """Returns list of dictionaries for all point elements and branch connections."""
        return self.get_point_elements() + self.get_branch_elements()

    def _node_feature_to_dict(self, feat):
        geom = feat.geometry()
        point = geom.asPoint() if geom and not geom.isEmpty() else QgsPointXY(0, 0)

        props_raw = feat.attribute("properties")
        try:
            properties = json.loads(props_raw) if props_raw else {}
        except (ValueError, TypeError):
            properties = {}

        return {
            "id": feat.attribute("id"),
            "name": feat.attribute("name"),
            "type": feat.attribute("type"),
            "location": {
                "x": point.x(),
                "y": point.y()
            },
            "properties": properties
        }

    def _branch_feature_to_dict(self, feat):
        props_raw = feat.attribute("properties")
        try:
            properties = json.loads(props_raw) if props_raw else {}
        except (ValueError, TypeError):
            properties = {}

        from_id = feat.attribute("from_element")
        to_id = feat.attribute("to_element")

        return {
            "id": feat.attribute("id"),
            "name": feat.attribute("name"),
            "type": "Branch",
            "from_element": from_id,
            "to_element": to_id,
            "upstream": from_id,
            "downstream": to_id,
            "properties": properties
        }

    def clear_all(self):
        """Clears all features from both point element layer and branch layer."""
        if self.nodes_layer:
            fids = [f.id() for f in self.nodes_layer.getFeatures()]
            if fids:
                self.nodes_layer.dataProvider().deleteFeatures(fids)
                self.nodes_layer.triggerRepaint()

        if self.branches_layer:
            fids = [f.id() for f in self.branches_layer.getFeatures()]
            if fids:
                self.branches_layer.dataProvider().deleteFeatures(fids)
                self.branches_layer.triggerRepaint()

        self._element_counter = 0
        self.modelCleared.emit()

    def export_to_json(self, file_path):
        """Exports point elements and branch connections to a JSON file."""
        crs_str = self.nodes_layer.crs().authid() if self.nodes_layer else self.get_canvas_crs()
        elements = self.get_all_elements()

        model_data = {
            "model_type": "RTC-Tools Model",
            "version": "1.0",
            "crs": crs_str,
            "element_count": len(elements),
            "elements": elements
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(model_data, f, indent=2)

        return True

    def import_from_json(self, file_path):
        """Imports point elements and branch connections from a JSON file."""
        if not os.path.exists(file_path):
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        elements = data.get("elements", [])
        self.clear_all()

        point_elems = [e for e in elements if e.get("type") != "Branch"]
        branch_elems = [e for e in elements if e.get("type") == "Branch"]

        # Pass 1: Import point elements
        for elem in point_elems:
            loc = elem.get("location", {})
            pt = QgsPointXY(loc.get("x", 0.0), loc.get("y", 0.0))
            elem_type = elem.get("type", "Node")
            elem_id = elem.get("id")
            name = elem.get("name")
            properties = elem.get("properties", {})

            nodes_layer = self.get_or_create_nodes_layer()
            feature = QgsFeature(nodes_layer.fields())
            feature.setGeometry(QgsGeometry.fromPointXY(pt))
            feature.setAttribute("id", elem_id or self.generate_next_id(elem_type))
            feature.setAttribute("name", name or "Element")
            feature.setAttribute("type", elem_type)
            feature.setAttribute("properties", json.dumps(properties))

            nodes_layer.dataProvider().addFeatures([feature])

        if self.nodes_layer:
            self.nodes_layer.updateExtents()
            self.nodes_layer.triggerRepaint()

        # Pass 2: Import Branch connections
        for branch in branch_elems:
            from_id = branch.get("from_element") or branch.get("upstream")
            to_id = branch.get("to_element") or branch.get("downstream")
            branch_id = branch.get("id")
            name = branch.get("name")
            properties = branch.get("properties", {})

            from_elem = self.get_element(from_id)
            to_elem = self.get_element(to_id)

            if from_elem and to_elem:
                pt_from = QgsPointXY(from_elem["location"]["x"], from_elem["location"]["y"])
                pt_to = QgsPointXY(to_elem["location"]["x"], to_elem["location"]["y"])

                branches_layer = self.get_or_create_branches_layer()
                feature = QgsFeature(branches_layer.fields())
                feature.setGeometry(QgsGeometry.fromPolylineXY([pt_from, pt_to]))
                feature.setAttribute("id", branch_id or self.generate_next_id("Branch"))
                feature.setAttribute("name", name or "Branch")
                feature.setAttribute("type", "Branch")
                feature.setAttribute("from_element", from_id)
                feature.setAttribute("to_element", to_id)
                feature.setAttribute("properties", json.dumps(properties))

                branches_layer.dataProvider().addFeatures([feature])

        if self.branches_layer:
            self.branches_layer.updateExtents()
            self.branches_layer.triggerRepaint()

        self._sync_counter()
        self.modelCleared.emit()
        return True

    def export_to_modelica(self, file_path, model_name=None):
        """Constructs and exports a Modelica (*.mo) file compatible with RTC-Tools models."""
        import re

        def sanitize_identifier(raw_name):
            s = re.sub(r'[\s\-]+', '_', str(raw_name).strip())
            s = re.sub(r'[^\w]', '', s)
            if s and s[0].isdigit():
                s = f"elem_{s}"
            return s or "elem"

        if not model_name:
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            model_name = sanitize_identifier(base_filename)
        else:
            model_name = sanitize_identifier(model_name)

        points = self.get_point_elements()
        branches = self.get_branch_elements()

        # Build unique Modelica identifiers map for elements
        id_to_var = {}
        used_vars = set()

        for elem in points + branches:
            raw_name = elem.get("name") or elem.get("id")
            var_name = sanitize_identifier(raw_name)

            base_var = var_name
            counter = 1
            while var_name in used_vars:
                var_name = f"{base_var}_{counter}"
                counter += 1

            used_vars.add(var_name)
            id_to_var[elem["id"]] = var_name

        point_ids = {p["id"]: p for p in points}

        # 1. Categorize declarations
        node_lines = []
        res_lines = []
        inflow_lines = []
        term_lines = []
        branch_lines = []

        for p in points:
            pid = p["id"]
            ptype = p.get("type")
            var_name = id_to_var[pid]

            if ptype == "Node":
                nin = sum(1 for b in branches if (b.get("from_element") or b.get("upstream")) and (b.get("to_element") or b.get("downstream")) == pid)
                node_lines.append(
                    f"  Deltares.ChannelFlow.SimpleRouting.Nodes.Node {var_name}(nin = {nin}, nout = 1, n_QForcing = 0);"
                )

            elif ptype == "Reservoir":
                props = p.get("properties", {})
                min_val = props.get("Minimum", props.get("minimum", 0))
                max_val = props.get("Maximum", props.get("maximum", 0))
                nom_val = props.get("Nominal", props.get("nominal", 0))

                res_lines.append(
                    f"  Deltares.ChannelFlow.SimpleRouting.Reservoir.Reservoir {var_name}(V(min = {min_val}, max = {max_val}, nominal = {nom_val}), n_QForcing = 0);"
                )

            elif ptype == "Inflow":
                inflow_lines.append(
                    f"  Deltares.ChannelFlow.SimpleRouting.BoundaryConditions.Inflow {var_name};"
                )

            elif ptype in ["Terminal", "Level"]:
                term_lines.append(
                    f"  Deltares.ChannelFlow.SimpleRouting.BoundaryConditions.Terminal {var_name};"
                )

        for b in branches:
            var_name = id_to_var[b["id"]]
            branch_lines.append(
                f"  Deltares.ChannelFlow.SimpleRouting.Branches.Steady {var_name};"
            )

        # 2. Build equation connect statements
        conn_lines = []
        node_in_counter = {pid: 0 for pid in point_ids if point_ids[pid].get("type") == "Node"}

        for b in branches:
            branch_var = id_to_var[b["id"]]
            from_id = b.get("from_element") or b.get("upstream")
            to_id = b.get("to_element") or b.get("downstream")

            from_elem = point_ids.get(from_id)
            to_elem = point_ids.get(to_id)

            if not from_elem or not to_elem:
                continue

            from_var = id_to_var[from_id]
            to_var = id_to_var[to_id]
            from_type = from_elem.get("type")
            to_type = to_elem.get("type")

            # Determine upstream element output port
            if from_type == "Node":
                from_port = f"{from_var}.QOut[1]"
            else:
                from_port = f"{from_var}.QOut"

            # Determine downstream element input port
            if to_type == "Node":
                node_in_counter[to_id] = node_in_counter.get(to_id, 0) + 1
                in_idx = node_in_counter[to_id]
                to_port = f"{to_var}.QIn[{in_idx}]"
            else:
                to_port = f"{to_var}.QIn"

            conn_lines.append(f"  connect({from_port}, {branch_var}.QIn);")
            conn_lines.append(f"  connect({branch_var}.QOut, {to_port});")

        # 3. Assemble full Modelica code
        mo_blocks = [
            f"model {model_name}",
            "  import SI = Modelica.Units.SI;\n"
        ]

        if node_lines:
            mo_blocks.append("  // Nodes\n" + "\n".join(node_lines) + "\n")
        if res_lines:
            mo_blocks.append("  // Reservoirs\n" + "\n".join(res_lines) + "\n")
        if inflow_lines:
            mo_blocks.append("  // Inflows\n" + "\n".join(inflow_lines) + "\n")
        if term_lines:
            mo_blocks.append("  // Terminals\n" + "\n".join(term_lines) + "\n")
        if branch_lines:
            mo_blocks.append("  // Branches\n" + "\n".join(branch_lines) + "\n")

        mo_blocks.append("equation")
        mo_blocks.append("  // Connections")
        if conn_lines:
            mo_blocks.append("\n".join(conn_lines))
        else:
            mo_blocks.append("  // (No connections)")

        mo_blocks.append(f"\nend {model_name};\n")

        mo_content = "\n".join(mo_blocks)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(mo_content)

        return True
