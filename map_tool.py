from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.core import QgsPointXY, QgsGeometry, Qgis
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QCursor, QColor

class AddElementMapTool(QgsMapToolEmitPoint):
    """Map tool that captures click coordinates on canvas to place point elements or Branch connections."""

    elementPlaced = pyqtSignal(object)

    def __init__(self, canvas, model_manager, iface=None, element_type_callback=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.model_manager = model_manager
        self.iface = iface
        self.element_type_callback = element_type_callback
        self.setCursor(QCursor(Qt.CrossCursor))

        self.selected_from_element = None
        self.rubber_band = None

    def canvasReleaseEvent(self, e):
        """Called when user releases mouse button on map canvas."""
        if e.button() != Qt.LeftButton:
            return

        click_pt = self.toMapCoordinates(e.pos())
        elem_type = "Node"
        if callable(self.element_type_callback):
            elem_type = self.element_type_callback()

        if elem_type == "Branch":
            self._handle_branch_click(click_pt)
        else:
            # Point element placement
            added_data = self.model_manager.add_element(click_pt, element_type=elem_type)
            self.elementPlaced.emit(added_data)

    def _handle_branch_click(self, click_pt):
        nearest_elem = self.model_manager.find_nearest_element(click_pt)

        if not nearest_elem:
            if self.iface:
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    "No element found near click. Please click directly on an element (Inflow, Reservoir, Level, Node) to start/end a Branch.",
                    level=Qgis.MessageLevel.Warning,
                    duration=4
                )
            return

        if self.selected_from_element is None:
            # First click: select upstream element
            self.selected_from_element = nearest_elem
            if self.iface:
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Selected upstream element: '{nearest_elem['name']}' ({nearest_elem['id']}). Now click the downstream element.",
                    level=Qgis.MessageLevel.Info,
                    duration=5
                )

            # Create rubber band line for visual feedback
            self._init_rubber_band()
            pt_from = QgsPointXY(nearest_elem["location"]["x"], nearest_elem["location"]["y"])
            self.rubber_band.setToGeometry(QgsGeometry.fromPolylineXY([pt_from, click_pt]), None)

        else:
            # Second click: select downstream element
            from_id = self.selected_from_element["id"]
            to_id = nearest_elem["id"]

            is_valid, err_msg = self.model_manager.validate_branch_connection(from_id, to_id)
            if not is_valid:
                if self.iface:
                    self.iface.messageBar().pushMessage(
                        "RTC-Tools",
                        f"Cannot create branch: {err_msg}",
                        level=Qgis.MessageLevel.Warning,
                        duration=5
                    )
                self._reset_branch_selection()
                return

            branch_data = self.model_manager.add_branch(from_id, to_id)
            self._reset_branch_selection()

            if branch_data:
                self.elementPlaced.emit(branch_data)

    def canvasMoveEvent(self, e):
        """Draws dynamic rubberband line during branch creation."""
        if self.selected_from_element and self.rubber_band:
            curr_pt = self.toMapCoordinates(e.pos())
            from_loc = self.selected_from_element["location"]
            from_pt = QgsPointXY(from_loc["x"], from_loc["y"])
            self.rubber_band.setToGeometry(QgsGeometry.fromPolylineXY([from_pt, curr_pt]), None)

    def _init_rubber_band(self):
        self._clear_rubber_band()
        self.rubber_band = QgsRubberBand(self.canvas, Qgis.GeometryType.Line)
        self.rubber_band.setColor(QColor(44, 62, 80))
        self.rubber_band.setWidth(2)

    def _clear_rubber_band(self):
        if self.rubber_band:
            self.rubber_band.reset()
            self.rubber_band = None

    def _reset_branch_selection(self):
        self.selected_from_element = None
        self._clear_rubber_band()

    def deactivate(self):
        """Called when map tool is deactivated."""
        self._reset_branch_selection()
        super().deactivate()
