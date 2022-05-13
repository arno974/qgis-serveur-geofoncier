# -*- coding: utf-8 -*-

"""
***************************************************************************
    geofoncier.py
    ---------------------
    Date                 : 22/04/2022
    Copyright            : (C) 2022 Arnaud Vandecasteele
    Email                : arnaud dot sig at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Arnaud Vandecasteele'
__date__ = 'April 2022'
__copyright__ = '(C) 2022, Arnaud Vandecasteele'

import xml.etree.ElementTree as ET

from typing import Generator, Tuple
import json

from PyQt5 import QtNetwork
from PyQt5.QtCore import QUrl, QEventLoop
from qgis.server import QgsServerFilter
from qgis.core import QgsNetworkAccessManager

from .logger import Logger

class GeoFoncierServerFilter(QgsServerFilter):
    def __init__(self, serverIface):
        super(GeoFoncierServerFilter, self).__init__(serverIface)
        self.logger = Logger()
        self.eventloop = None
        self.nam = QgsNetworkAccessManager.instance()
        
    def requestReady(self):
        pass

    def sendResponse(self):
        pass

    def responseComplete(self):
        """ Intercept the GetFeatureInfo for GE layers and add the form maptip if needed."""
        request = self.serverInterface().requestHandler()
        params = request.parameterMap( )
        
        xml = request.body().data().decode("utf-8")
        root = ET.fromstring(xml)

        ##Lizmap is only processing INFO_FORMAT=TEXT/XML        
        if (params.get('SERVICE', '').upper() == 'WMS' \
                and params.get('REQUEST', '').upper() == 'GETFEATUREINFO' \
                and params.get('INFO_FORMAT', '').upper() == 'TEXT/XML' \
                and 'DOSSIERS DES GÉOMÈTRES EXPERTS' in params.get('QUERY_LAYERS', '').upper()
            ):
            
            for layer in root:    
                if 'name' in  layer.attrib:
                    if layer.attrib['name'] == 'Dossiers des Géomètres Experts':
                        ##Get enr_api ID and query GeoFoncier website to get additional informations 
                        enr_api = layer.find("Attribute[@name='enr_api']")                
                        geoFoncierAPIurl = 'https://api2.geofoncier.fr/api/dossiersoge/dossiers/mini/{}'.format(enr_api.attrib['value'])
                        geoFoncierRequest = QtNetwork.QNetworkRequest(QUrl(geoFoncierAPIurl))  
                        reply = self.nam.get(geoFoncierRequest)     
                        ##asynchronous
                        eventloop = QEventLoop()             
                        reply.finished.connect(eventloop.quit)         
                        eventloop.exec_()
                        response_data = reply.readAll().data()
                        json_response_data = json.loads(response_data)
                        geofoncier_xml = self.create_xml_response(json_response_data)  
                        ##Remove previous GetFeatureInfo response and add our custom resonse                     
                        root.remove(layer)
                        root.append(geofoncier_xml)   

            _xml = ET.tostring(root, method='xml').decode("utf-8").split('\n')
            _xml = '\n'.join(_xml[0:])
            #return xml with custom values
            request.clear()
            request.setResponseHeader('Content-Type', 'text/xml')
            request.appendBody(bytes(_xml, 'utf-8'))

    def create_xml_response(self, json_response):
        ##pretty name
        geofoncier_dict = {
            'enr_ref_dossier' : 'Référence du dossier',
            'dmpc_ref' : 'Référence DMPC',
            'operation': 'Opération',
            'nom_cabcreateur' : 'Cabinet GE',
            'contact_cabdetenteur' : 'Contact'
        }
        xml = ET.Element("Layer", name="Dossiers des Géomètres Experts")
        feature = ET.SubElement(xml, "Feature")        
        
        for field in geofoncier_dict:
            if field in json_response:                
                if field == 'dmpc_ref':
                    if 'dmpc_ref' in json_response['dmpc_ref'] :                
                        json_response[field] = json_response[field]['dmpc_ref']
                    else:
                        continue
                if field == 'contact_cabdetenteur':
                    json_response[field] = '<a href="{contact_ge}">Contact du cabinet GE</a>'.format(contact_ge=json_response[field])
                if field == 'operation':
                    json_response[field] = ', '.join(json_response[field])                
                ET.SubElement(feature, 'Attribute', name=geofoncier_dict[field], value=json_response[field])        
        return xml

    def html_table_from_response(self, json_response):
        geofoncier_dict = {
            'enr_ref_dossier' : 'Référence du dossier',
            'dmpc_ref' : 'Référence DMPC',
            'operation': 'Opération',
            'nom_cabcreateur' : 'Cabinet GE',
            'contact_cabdetenteur' : 'Contact'
        }
        table_template = """<table class="table table-condensed table-striped table-bordered lizmapPopupTable">
                            <tbody>
                                {fields_template}
                            </tbody>
                            </table>
                        """
        field_template = """    
                            <tr>
                                <th>{name}</th>
                                <td>{value}</td>
                            </tr>        
                        """
        fields = ""
        for field in geofoncier_dict:
            if field in json_response:
                if field == 'dmpc_ref'  and len(json_response[field])==0:
                    continue
                if field == 'contact_cabdetenteur':
                    json_response[field] = '<a href="{contact_ge}">Contact du cabinet GE</a>'.format(contact_ge=json_response[field])
                if field == 'dmpc_ref':
                    json_response[field] = json_response[field]['dmpc_ref']
                if field == 'operation':
                    json_response[field] = ', '.join(json_response[field])
                
                fields += field_template.format(name=geofoncier_dict[field], value=json_response[field])
        result = table_template.format(fields_template=fields)
        return result    

class GeoFoncierServer:
    def __init__(self, serverIface):  
        self.serverIface = serverIface        
        serverIface.registerFilter(GeoFoncierServerFilter(serverIface), 1)