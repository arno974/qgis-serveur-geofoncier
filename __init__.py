# -*- coding: utf-8 -*-
"""
 This script initializes the plugin, making it known to QGIS.
"""

def serverClassFactory(serverIface):
    from .geofoncier import GeoFoncierServer
    return GeoFoncierServer(serverIface)

