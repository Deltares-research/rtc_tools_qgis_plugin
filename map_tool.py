from qgis.gui import QgsMapToolEmitPoint
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QCursor

class AddElementMapTool(QgsMapToolEmitPoint):
    """Map tool that captures click coordinates on canvas to place an RTC-Tools element."""

    elementPlaced = pyqtSignal(object)

    def __init__(self, canvas, model_manager, element_type_callback=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.model_manager = model_manager
        self.element_type_callback = element_type_callback
        self.setCursor(QCursor(Qt.CrossCursor))

    def canvasReleaseEvent(self, e):
        """Called when user releases mouse button on map canvas."""
        if e.button() == Qt.LeftButton:
            point = self.toMapCoordinates(e.pos())
            elem_type = "Node"
            if callable(self.element_type_callback):
                elem_type = self.element_type_callback()

            added_data = self.model_manager.add_element(point, element_type=elem_type)
            self.elementPlaced.emit(added_data)

    def deactivate(self):
        """Called when map tool is deactivated."""
        super().deactivate()
