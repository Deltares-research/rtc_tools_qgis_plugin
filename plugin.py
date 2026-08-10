import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .model_manager import ModelManager
from .map_tool import AddElementMapTool
from .dock_widget import RTCToolsDockWidget

class RTCToolsPlugin:
    """Main QGIS Plugin class for RTC-Tools integration."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.action = None
        self.dock_widget = None
        self.model_manager = None
        self.map_tool = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "RTC-Tools Model Builder", self.iface.mainWindow())
        self.action.setStatusTip("Open RTC-Tools Model Builder dock panel")
        self.action.triggered.connect(self.run)

        # Add to QGIS Plugins menu and toolbar
        self.iface.addPluginToMenu("&RTC-Tools", self.action)
        self.iface.addToolBarIcon(self.action)

        # Initialize model components
        self.model_manager = ModelManager(self.iface)
        
        # Initialize map tool
        self.map_tool = AddElementMapTool(
            self.iface.mapCanvas(),
            self.model_manager,
            element_type_callback=self._get_active_element_type
        )

        # Initialize dock widget
        self.dock_widget = RTCToolsDockWidget(
            self.iface,
            self.model_manager,
            self.map_tool,
            parent=self.iface.mainWindow()
        )
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.hide()  # Hidden by default until action clicked or opened by user

    def _get_active_element_type(self):
        if self.dock_widget:
            return self.dock_widget.get_selected_element_type()
        return "Node"

    def unload(self):
        """Remove plugin menu items, toolbar buttons, and dock widgets from QGIS."""
        if self.action:
            self.iface.removePluginMenu("&RTC-Tools", self.action)
            self.iface.removeToolBarIcon(self.action)
            del self.action

        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

        if self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self.map_tool = None

    def run(self):
        """Show and raise the RTC-Tools dock widget when the toolbar/menu item is clicked."""
        if self.dock_widget:
            self.dock_widget.show()
            self.dock_widget.raise_()
