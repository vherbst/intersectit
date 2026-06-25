#-----------------------------------------------------------
#
# Intersect It is a QGIS plugin to place observations (distance or orientation)
# with their corresponding precision, intersect them using a least-squares solution
# and save dimensions in a dedicated layer to produce maps.
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from qgis.core import Qgis, QgsFeature, QgsGeometry, QgsProject, QgsPointLocator, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand

from ..core.mysettings import MySettings
from ._snap import snap_to_edge_all


class SimpleIntersectionMapTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.mapCanvas = iface.mapCanvas()
        QgsMapTool.__init__(self, self.mapCanvas)
        self.settings = MySettings()
        self.rubber = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PointGeometry)

    def deactivate(self):
        self.rubber.reset()
        QgsMapTool.deactivate(self)

    def activate(self):
        QgsMapTool.activate(self)
        self.rubber.setWidth(self.settings.value("rubberWidth"))
        self.rubber.setColor(self.settings.value("rubberColor"))
        self.checkLayer()

    def canvasMoveEvent(self, mouseEvent):
        # put the observations within tolerance in the rubber band
        self.rubber.reset(QgsWkbTypes.PointGeometry)
        match = self.snap_to_intersection(mouseEvent.pos())
        if match.type() == QgsPointLocator.Vertex and match.layer() is None:
            self.rubber.addPoint(match.point())

    def canvasPressEvent(self, mouseEvent):
        self.rubber.reset()
        match = self.snap_to_intersection(mouseEvent.pos())
        if match.type() != QgsPointLocator.Vertex or match.layer() is not None:
            return

        layer = self.checkLayer()
        if layer is None:
            return
        f = QgsFeature()
        initFields = layer.fields()
        f.setFields(initFields)
        f.initAttributes(initFields.size())
        f.setGeometry(QgsGeometry.fromPointXY(match.point()))
        layer.addFeature(f)
        layer.triggerRepaint()

    def snap_to_intersection(self, pos):
        return snap_to_edge_all(self.canvas(), self.toMapCoordinates(pos), snap_on_intersections=True)

    def checkLayer(self):
        # check output layer is defined
        layerid = self.settings.value("simpleIntersectionLayer")
        layer = QgsProject.instance().mapLayer(layerid)
        if not self.settings.value("simpleIntersectionWritePoint") or layer is None:
            self.iface.messageBar().pushMessage("Intersect It",
                                                "You must define an output layer for simple intersections",
                                                Qgis.Warning, 3)
            self.mapCanvas.unsetMapTool(self)
            return None
        if not layer.isEditable():
            self.iface.messageBar().pushMessage("Intersect It",
                                                "The output layer <b>%s must be editable</b>" % layer.name(),
                                                Qgis.Warning, 3)
            self.mapCanvas.unsetMapTool(self)
            return None
        return layer
