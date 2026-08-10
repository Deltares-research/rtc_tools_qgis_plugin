"""
RTC-Tools QGIS Plugin
Entry point for QGIS plugin loader.
"""

def classFactory(iface):
    """Load RTCToolsPlugin class from file plugin.py.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .plugin import RTCToolsPlugin
    return RTCToolsPlugin(iface)
