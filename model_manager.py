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
    QgsSingleSymbolRenderer,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
)
from qgis.PyQt.QtCore import QObject, pyqtSignal, QVariant
from qgis.PyQt.QtGui import QColor

class ModelManager(QObject):
    """Manages the RTC-Tools model vector layer, features, and file import/export."""

    # Signals
    elementAdded = pyqtSignal(dict)
    elementUpdated = pyqtSignal(dict)
    elementRemoved = pyqtSignal(str)
    modelCleared = pyqtSignal()
    layerCreated = pyqtSignal(object)

    LAYER_NAME = "RTC-Tools Elements"

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.layer = None
        self._element_counter = 0

    def get_canvas_crs(self):
        """Returns current canvas CRS auth ID (e.g. 'EPSG:4326')."""
        if self.iface and self.iface.mapCanvas():
            return self.iface.mapCanvas().mapSettings().destinationCrs().authid()
        return "EPSG:4326"

    def get_or_create_layer(self):
        """Retrieves or creates the RTC-Tools memory vector layer in QGIS."""
        # Check if layer already exists in current QGIS project
        if self.layer and QgsProject.instance().mapLayer(self.layer.id()):
            return self.layer

        existing_layers = QgsProject.instance().mapLayersByName(self.LAYER_NAME)
        if existing_layers:
            self.layer = existing_layers[0]
            self._sync_counter_from_layer()
            return self.layer

        crs_str = self.get_canvas_crs()
        self.layer = QgsVectorLayer(f"Point?crs={crs_str}", self.LAYER_NAME, "memory")
        
        provider = self.layer.dataProvider()
        provider.addAttributes([
            QgsField("id", QVariant.String),
            QgsField("name", QVariant.String),
            QgsField("type", QVariant.String),
            QgsField("properties", QVariant.String),
        ])
        self.layer.updateFields()

        # Apply custom styling and labeling
        self._setup_layer_style()

        # Add to QGIS project map layer registry
        QgsProject.instance().addMapLayer(self.layer)
        self.layerCreated.emit(self.layer)
        return self.layer

    def _setup_layer_style(self):
        """Applies a distinct symbol renderer and labels to the layer."""
        if not self.layer:
            return

        # Simple blue marker symbol
        symbol = QgsMarkerSymbol.createSimple({
            "name": "circle",
            "color": "#1E508C",
            "outline_color": "#FFFFFF",
            "outline_width": "0.6",
            "size": "4.0"
        })
        renderer = QgsSingleSymbolRenderer(symbol)
        self.layer.setRenderer(renderer)

        # Labels showing element name
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = "name"
        label_settings.enabled = True

        text_format = QgsTextFormat()
        text_format.setSize(9)
        text_format.setColor(QColor("#0A2850"))
        label_settings.setFormat(text_format)

        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        self.layer.setLabeling(labeling)
        self.layer.setLabelsEnabled(True)

    def _sync_counter_from_layer(self):
        """Synchronizes element counter to prevent ID duplication."""
        if not self.layer:
            return
        max_idx = 0
        for feat in self.layer.getFeatures():
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
        """Adds a new element feature to the memory layer at point location."""
        layer = self.get_or_create_layer()

        elem_id = self.generate_next_id(element_type)
        if not name:
            name = f"{element_type} {self._element_counter}"
        if properties is None:
            properties = {}

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttribute("id", elem_id)
        feature.setAttribute("name", name)
        feature.setAttribute("type", element_type)
        feature.setAttribute("properties", json.dumps(properties))

        layer.dataProvider().addFeatures([feature])
        layer.updateExtents()
        layer.triggerRepaint()

        elem_data = {
            "id": elem_id,
            "name": name,
            "type": element_type,
            "location": {"x": point.x(), "y": point.y()},
            "properties": properties
        }
        self.elementAdded.emit(elem_data)
        return elem_data

    def update_element(self, element_id, new_name=None, new_type=None, new_properties=None):
        """Updates attributes of an existing element by ID."""
        if not self.layer:
            return False

        for feat in self.layer.getFeatures():
            if feat.attribute("id") == element_id:
                attr_updates = {}
                fields = self.layer.fields()

                if new_name is not None:
                    attr_updates[fields.indexFromName("name")] = new_name
                if new_type is not None:
                    attr_updates[fields.indexFromName("type")] = new_type
                if new_properties is not None:
                    attr_updates[fields.indexFromName("properties")] = json.dumps(new_properties)

                if attr_updates:
                    self.layer.dataProvider().changeAttributeValues({feat.id(): attr_updates})
                    self.layer.triggerRepaint()

                updated_data = self.get_element(element_id)
                if updated_data:
                    self.elementUpdated.emit(updated_data)
                return True
        return False

    def remove_element(self, element_id):
        """Deletes an element by ID."""
        if not self.layer:
            return False

        for feat in self.layer.getFeatures():
            if feat.attribute("id") == element_id:
                self.layer.dataProvider().deleteFeatures([feat.id()])
                self.layer.triggerRepaint()
                self.elementRemoved.emit(element_id)
                return True
        return False

    def get_element(self, element_id):
        """Retrieves dictionary representation of an element by ID."""
        if not self.layer:
            return None

        for feat in self.layer.getFeatures():
            if feat.attribute("id") == element_id:
                return self._feature_to_dict(feat)
        return None

    def get_all_elements(self):
        """Returns list of dictionaries for all features in layer."""
        if not self.layer:
            return []

        elements = []
        for feat in self.layer.getFeatures():
            elements.append(self._feature_to_dict(feat))
        return elements

    def _feature_to_dict(self, feat):
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

    def clear_all(self):
        """Clears all features from layer."""
        if not self.layer:
            return

        fids = [feat.id() for feat in self.layer.getFeatures()]
        if fids:
            self.layer.dataProvider().deleteFeatures(fids)
            self.layer.triggerRepaint()
        self._element_counter = 0
        self.modelCleared.emit()

    def export_to_json(self, file_path):
        """Exports the model data to a JSON file format."""
        crs_str = self.layer.crs().authid() if self.layer else self.get_canvas_crs()
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
        """Imports model data from a JSON file into the memory layer."""
        if not os.path.exists(file_path):
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        elements = data.get("elements", [])
        self.clear_all()

        for elem in elements:
            loc = elem.get("location", {})
            pt = QgsPointXY(loc.get("x", 0.0), loc.get("y", 0.0))
            elem_type = elem.get("type", "Node")
            elem_id = elem.get("id")
            name = elem.get("name")
            properties = elem.get("properties", {})

            layer = self.get_or_create_layer()
            feature = QgsFeature(layer.fields())
            feature.setGeometry(QgsGeometry.fromPointXY(pt))
            feature.setAttribute("id", elem_id or self.generate_next_id(elem_type))
            feature.setAttribute("name", name or "Element")
            feature.setAttribute("type", elem_type)
            feature.setAttribute("properties", json.dumps(properties))

            layer.dataProvider().addFeatures([feature])

        if self.layer:
            self.layer.updateExtents()
            self.layer.triggerRepaint()

        self._sync_counter_from_layer()
        self.modelCleared.emit()  # Refresh GUI view
        return True
