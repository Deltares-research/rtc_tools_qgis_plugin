from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand
from qgis.core import QgsPointXY, QgsGeometry, Qgis
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QCursor, QColor

class AddElementMapTool(QgsMapToolEmitPoint):
    """Map tool that captures click coordinates on canvas to place point elements or Branch connections."""

    elementPlaced = pyqtSignal(object)
    deactivated = pyqtSignal()

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
                    f"Selected upstream element: '{nearest_elem['name']}'. Now click the downstream element.",
                    level=Qgis.MessageLevel.Info,
                    duration=5
                )

            # Create rubber band line for visual feedback
            self._init_rubber_band()
            pt_from = QgsPointXY(nearest_elem["location"]["x"], nearest_elem["location"]["y"])
            self.rubber_band.setToGeometry(QgsGeometry.fromPolylineXY([pt_from, click_pt]), None)

        else:
            # Second click: select downstream element
            from_name = self.selected_from_element["name"]
            to_name = nearest_elem["name"]

            is_valid, err_msg = self.model_manager.validate_branch_connection(from_name, to_name)
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

            branch_data = self.model_manager.add_branch(from_name, to_name)
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
        self.deactivated.emit()
        super().deactivate()


class MoveNodeMapTool(QgsMapTool):
    """Map tool that allows a user to interactively move a node/element on the map canvas
    via either click-and-drag or pick-and-place, dynamically updating connecting branches.
    """

    nodeMoved = pyqtSignal(object)
    deactivated = pyqtSignal()

    def __init__(self, canvas, model_manager, iface=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.model_manager = model_manager
        self.iface = iface
        self.setCursor(QCursor(Qt.OpenHandCursor))

        self.moving_element = None
        self.is_dragging = False
        self.drag_start_pos = None
        self.node_rubber_band = None
        self.branch_rubber_bands = []

    def canvasPressEvent(self, e):
        """Called when user presses mouse button on map canvas."""
        if e.button() == Qt.RightButton:
            if self.moving_element:
                self._cancel_move()
                if self.iface:
                    self.iface.messageBar().pushMessage(
                        "RTC-Tools",
                        "Move cancelled.",
                        level=Qgis.MessageLevel.Info,
                        duration=3
                    )
            return

        if e.button() != Qt.LeftButton:
            return

        click_pt = self.toMapCoordinates(e.pos())

        if self.moving_element is None:
            # First interaction: try to pick an element
            target_elem = self._find_target_element(click_pt)
            if not target_elem:
                if self.iface:
                    self.iface.messageBar().pushMessage(
                        "RTC-Tools",
                        "No node or element found near click. Click directly on a node to select and move it.",
                        level=Qgis.MessageLevel.Warning,
                        duration=4
                    )
                return

            self.moving_element = target_elem
            self.drag_start_pos = e.pos()
            self.is_dragging = False
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self._init_rubber_bands(click_pt)
        else:
            # Destination click in pick-and-place mode
            self._finish_move(click_pt)

    def canvasMoveEvent(self, e):
        """Called when mouse moves over the map canvas."""
        curr_pt = self.toMapCoordinates(e.pos())

        if self.moving_element is not None:
            if not self.is_dragging and self.drag_start_pos is not None:
                if (e.pos() - self.drag_start_pos).manhattanLength() > 3:
                    self.is_dragging = True
                    self.setCursor(QCursor(Qt.ClosedHandCursor))

            self._update_rubber_bands(curr_pt)
        else:
            target = self._find_target_element(curr_pt)
            if target:
                self.setCursor(QCursor(Qt.OpenHandCursor))
            else:
                self.setCursor(QCursor(Qt.CrossCursor))

    def canvasReleaseEvent(self, e):
        """Called when mouse button is released."""
        if e.button() != Qt.LeftButton:
            return

        if self.moving_element is not None:
            if self.is_dragging:
                # Drag completed: place at release position
                release_pt = self.toMapCoordinates(e.pos())
                self._finish_move(release_pt)
            else:
                # Clicked without dragging: remain selected in pick-and-place mode
                if self.iface:
                    self.iface.messageBar().pushMessage(
                        "RTC-Tools",
                        f"Selected '{self.moving_element['name']}'. Click on map to place it at the new location, or press Esc to cancel.",
                        level=Qgis.MessageLevel.Info,
                        duration=5
                    )

    def keyPressEvent(self, e):
        """Handles keyboard events (e.g. Escape to cancel move)."""
        if e.key() == Qt.Key_Escape:
            if self.moving_element is not None:
                self._cancel_move()
                if self.iface:
                    self.iface.messageBar().pushMessage(
                        "RTC-Tools",
                        "Move cancelled.",
                        level=Qgis.MessageLevel.Info,
                        duration=3
                    )
            e.accept()
        else:
            super().keyPressEvent(e)

    def start_moving_element(self, elem_data):
        """Pre-selects an element to move (e.g. initiated from the elements table)."""
        if not elem_data:
            return
        self._clear_rubber_bands()
        self.moving_element = elem_data
        self.is_dragging = False
        self.drag_start_pos = None

        loc = elem_data.get("location", {})
        start_pt = QgsPointXY(loc.get("x", 0.0), loc.get("y", 0.0))
        self._init_rubber_bands(start_pt)
        self.setCursor(QCursor(Qt.ClosedHandCursor))

        if self.iface:
            self.iface.messageBar().pushMessage(
                "RTC-Tools",
                f"Selected '{elem_data['name']}'. Click on the map to place it at the new location, or press Esc to cancel.",
                level=Qgis.MessageLevel.Info,
                duration=5
            )

    def _find_target_element(self, pt):
        if not self.model_manager:
            return None
        tol = 1000.0
        if self.canvas:
            mupp = self.canvas.mapUnitsPerPixel()
            if mupp and mupp > 0:
                tol = mupp * 25
            else:
                extent = self.canvas.extent()
                if extent and extent.width() > 0:
                    tol = extent.width() * 0.08
        return self.model_manager.find_nearest_element(pt, max_distance=tol)

    def _init_rubber_bands(self, start_pt):
        self._clear_rubber_bands()
        if not self.moving_element or not self.canvas:
            return

        # Marker for node position
        self.node_rubber_band = QgsRubberBand(self.canvas, Qgis.GeometryType.Point)
        self.node_rubber_band.setColor(QColor(230, 126, 34, 220))
        self.node_rubber_band.setIcon(QgsRubberBand.ICON_CIRCLE)
        self.node_rubber_band.setIconSize(10)
        self.node_rubber_band.setWidth(2)
        self.node_rubber_band.setToGeometry(QgsGeometry.fromPointXY(start_pt), None)

        # Lines for connected branches
        elem_name = self.moving_element["name"]
        branches = self.model_manager.get_branch_elements()
        self.branch_rubber_bands = []

        for b in branches:
            from_name = b.get("from_element") or b.get("upstream")
            to_name = b.get("to_element") or b.get("downstream")

            if from_name == elem_name or to_name == elem_name:
                band = QgsRubberBand(self.canvas, Qgis.GeometryType.Line)
                band.setColor(QColor(44, 62, 80, 180))
                band.setWidth(2)

                other_name = to_name if from_name == elem_name else from_name
                other_elem = self.model_manager.get_element(other_name)
                other_pt = None
                if other_elem and "location" in other_elem:
                    other_pt = QgsPointXY(other_elem["location"]["x"], other_elem["location"]["y"])

                if other_pt:
                    self.branch_rubber_bands.append({
                        "band": band,
                        "from_is_moving": (from_name == elem_name),
                        "other_pt": other_pt
                    })
                    if from_name == elem_name:
                        band.setToGeometry(QgsGeometry.fromPolylineXY([start_pt, other_pt]), None)
                    else:
                        band.setToGeometry(QgsGeometry.fromPolylineXY([other_pt, start_pt]), None)

    def _update_rubber_bands(self, curr_pt):
        if self.node_rubber_band:
            self.node_rubber_band.setToGeometry(QgsGeometry.fromPointXY(curr_pt), None)

        for item in self.branch_rubber_bands:
            band = item["band"]
            other_pt = item["other_pt"]
            if item["from_is_moving"]:
                band.setToGeometry(QgsGeometry.fromPolylineXY([curr_pt, other_pt]), None)
            else:
                band.setToGeometry(QgsGeometry.fromPolylineXY([other_pt, curr_pt]), None)

    def _clear_rubber_bands(self):
        if self.node_rubber_band:
            self.node_rubber_band.reset()
            self.node_rubber_band = None

        for item in self.branch_rubber_bands:
            band = item.get("band")
            if band:
                band.reset()
        self.branch_rubber_bands = []

    def _finish_move(self, dest_pt):
        if not self.moving_element:
            return
        elem_name = self.moving_element["name"]
        updated_data = self.model_manager.move_element(elem_name, dest_pt)

        self._clear_rubber_bands()
        self.moving_element = None
        self.is_dragging = False
        self.drag_start_pos = None
        self.setCursor(QCursor(Qt.OpenHandCursor))

        if updated_data:
            self.nodeMoved.emit(updated_data)
            if self.iface:
                self.iface.messageBar().pushMessage(
                    "RTC-Tools",
                    f"Moved '{elem_name}' to ({dest_pt.x():.4f}, {dest_pt.y():.4f})",
                    level=Qgis.MessageLevel.Success,
                    duration=3
                )

    def _cancel_move(self):
        self._clear_rubber_bands()
        self.moving_element = None
        self.is_dragging = False
        self.drag_start_pos = None
        self.setCursor(QCursor(Qt.OpenHandCursor))

    def deactivate(self):
        """Called when map tool is deactivated."""
        self._cancel_move()
        self.deactivated.emit()
        super().deactivate()
