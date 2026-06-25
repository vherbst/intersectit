# -----------------------------------------------------------
#
# Intersect It is a QGIS plugin to place observations (distance or orientation)
# with their corresponding precision, intersect them using a least-squares solution
# and save dimensions in a dedicated layer to produce maps.
#
# Copyright    : (C) 2013 Denis Rouzaud
# Email        : denis.rouzaud@gmail.com
#
# -----------------------------------------------------------
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
# ---------------------------------------------------------------------

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (Qgis, QgsFeatureRequest, QgsFeature, QgsGeometry, QgsProject,
                       QgsPointXY, QgsRectangle)
from qgis.gui import QgsMapTool, QgsRubberBand

from ..core.mysettings import MySettings
from ..core.memory_layers import MemoryLayers
from ..core.arc import Arc

from .my_settings_dialog import MySettingsDialog
from .intersection_dialog import IntersectionDialog


class AdvancedIntersectionMapTool(QgsMapTool):
    def __init__(self, iface):
        self.iface = iface
        self.mapCanvas = iface.mapCanvas()
        QgsMapTool.__init__(self, self.mapCanvas)
        self.settings = MySettings()
        self.rubber = QgsRubberBand(self.mapCanvas)
        self.line_layer = None
        self.layerId = None

        self.tolerance = self.settings.value("selectTolerance")
        units = self.settings.value("selectUnits")
        if units == "pixels":
            self.tolerance *= self.mapCanvas.mapUnitsPerPixel()

    def activate(self):
        QgsMapTool.activate(self)
        self.rubber.setWidth(self.settings.value("rubberWidth"))
        self.rubber.setColor(self.settings.value("rubberColor"))
        line_layer = MemoryLayers(self.iface).line_layer()
        # unset this tool if the layer is removed
        line_layer.willBeDeleted.connect(self.unsetMapTool)
        self.layerId = line_layer.id()
        self.line_layer = line_layer

    def unsetMapTool(self):
        self.mapCanvas.unsetMapTool(self)

    def deactivate(self):
        self.rubber.reset()
        line_layer = QgsProject.instance().mapLayer(self.layerId)
        if line_layer is not None:
            try:
                line_layer.willBeDeleted.disconnect(self.unsetMapTool)
            except TypeError:
                pass
        QgsMapTool.deactivate(self)

    def canvasMoveEvent(self, mouseEvent):
        # put the observations within tolerance in the rubber band
        self.rubber.reset()
        for f in self.getFeatures(mouseEvent.pos()):
            self.rubber.addGeometry(f.geometry(), None)

    def canvasPressEvent(self, mouseEvent):
        pos = mouseEvent.pos()
        observations = self.getFeatures(pos)
        point = self.toMapCoordinates(pos)
        self.doIntersection(point, observations)

    def _tolerance_map_units(self):
        tol = self.settings.value("selectTolerance")
        if self.settings.value("selectUnits") == "pixels":
            tol *= self.mapCanvas.mapUnitsPerPixel()
        return tol

    def getFeatures(self, pixPoint):
        # collect features from the memory line layer whose geometry is within
        # the configured tolerance of the cursor (in map units).
        if self.line_layer is None or not self.line_layer.isValid():
            return []
        map_point = self.toMapCoordinates(pixPoint)
        tol = self._tolerance_map_units()
        bbox = QgsRectangle(map_point.x() - tol, map_point.y() - tol,
                            map_point.x() + tol, map_point.y() + tol)
        click_geom = QgsGeometry.fromPointXY(QgsPointXY(map_point))
        features = []
        seen = set()
        request = QgsFeatureRequest().setFilterRect(bbox).setFlags(QgsFeatureRequest.ExactIntersect)
        for f in self.line_layer.getFeatures(request):
            if f.id() in seen:
                continue
            if click_geom.distance(f.geometry()) <= tol:
                seen.add(f.id())
                features.append(QgsFeature(f))
        return features

    def doIntersection(self, initPoint, observations):
        nObs = len(observations)
        if nObs < 2:
            return
        self.rubber.reset()
        self.dlg = IntersectionDialog(self.iface, observations, initPoint)
        if not self.dlg.exec() or self.dlg.solution is None:
            return
        intersectedPoint = self.dlg.solution
        self.saveIntersectionResult(self.dlg.report, intersectedPoint)
        self.saveDimension(intersectedPoint, self.dlg.observations)

    def saveIntersectionResult(self, report, intersectedPoint):
        # save the intersection result (point) and its report
        # check first
        while True:
            if not self.settings.value("advancedIntersectionWritePoint"):
                break  # if we do not place any point, skip
            layerid = self.settings.value("advancedIntersectionLayer")
            message = QCoreApplication.translate("IntersectIt",
                                                 "To place the intersection solution,"
                                                 " you must select a layer in the settings.")
            status, intLayer = self.checkLayerExists(layerid, message)
            if status == 2:
                continue
            if status == 3:
                return
            if self.settings.value("advancedIntersectionWriteReport"):
                reportField = self.settings.value("reportField")
                message = QCoreApplication.translate("IntersectIt",
                                                     "To save the intersection report, please select a field for it.")
                status = self.checkFieldExists(intLayer, reportField, message)
                if status == 2:
                    continue
                if status == 3:
                    return
            break
        # save the intersection results
        if self.settings.value("advancedIntersectionWritePoint"):
            f = QgsFeature()
            f.setFields(intLayer.fields())
            f.initAttributes(intLayer.fields().size())
            if self.settings.value("advancedIntersectionWriteReport"):
                f[reportField] = report
            f.setGeometry(QgsGeometry.fromPointXY(intersectedPoint))
            intLayer.dataProvider().addFeatures([f])
            intLayer.updateExtents()
            self.mapCanvas.refresh()

    def saveDimension(self, intersectedPoint, observations):
        # check that dimension layer and fields have been set correctly
        if not self.settings.value("dimensionDistanceWrite") and not self.settings.value("dimensionOrientationWrite"):
            return  # if we do not place any dimension, skip
        obsTypes = ("Distance", "Orientation")
        recheck = True
        while recheck:
            # settings might change during checking,
            # so recheck both observation types whenever the settings dialog is shown
            recheck = False
            for obsType in obsTypes:
                while True:
                    if not self.settings.value("dimension"+obsType+"Write"):
                        break
                    # check layer
                    layerId = self.settings.value("dimension"+obsType+"Layer")
                    message = QCoreApplication.translate("IntersectIt",
                                                         "To place dimensions, "
                                                         "you must define a layer in the settings.")
                    status, dimLayer = self.checkLayerExists(layerId, message)
                    if status == 2:
                        recheck = True
                        continue
                    if status == 3:
                        return
                    # check fields
                    if self.settings.value("dimension"+obsType+"ObservationWrite"):
                        obsField = self.settings.value("dimension"+obsType+"ObservationField")
                        message = QCoreApplication.translate("IntersectIt",
                                                             "To save the observation in the layer,"
                                                             " please select a field for it.")
                        status = self.checkFieldExists(dimLayer, obsField, message)
                        if status == 2:
                            recheck = True
                            continue
                        if status == 3:
                            return
                    if self.settings.value("dimension"+obsType+"PrecisionWrite"):
                        precisionField = self.settings.value("dimension"+obsType+"PrecisionField")
                        message = QCoreApplication.translate("IntersectIt",
                                                             "To save the precision of observation,"
                                                             " please select a field for it.")
                        status = self.checkFieldExists(dimLayer, precisionField, message)
                        if status == 2:
                            recheck = True
                            continue
                        if status == 3:
                            return
                    break
        # save the intersection results
        for obsType in obsTypes:
            if self.settings.value("dimension"+obsType+"Write"):
                layerid = self.settings.value("dimension"+obsType+"Layer")
                layer = QgsProject.instance().mapLayer(layerid)
                if layer is None:
                    continue
                initFields = layer.fields()
                features = []
                for obs in observations:
                    if obs["type"] != obsType.lower():
                        continue
                    f = QgsFeature()
                    f.setFields(initFields)
                    f.initAttributes(initFields.size())
                    if self.settings.value("dimension"+obsType+"ObservationWrite"):
                        f[self.settings.value("dimension"+obsType+"ObservationField")] = obs["observation"]
                    if self.settings.value("dimension"+obsType+"PrecisionWrite"):
                        f[self.settings.value("dimension"+obsType+"PrecisionField")] = obs["precision"]
                    p0 = QgsPointXY(obs["x"], obs["y"])
                    p1 = intersectedPoint
                    if obs["type"] == "distance":
                        geom = Arc(p0, p1).geometry()
                    elif obs["type"] == "orientation":
                        geom = QgsGeometry.fromPolylineXY([p0, p1])
                    else:
                        raise NameError("Invalid observation %s" % obs["type"])
                    f.setGeometry(geom)
                    features.append(QgsFeature(f))
                ok, _added = layer.dataProvider().addFeatures(features)
                if not ok:
                    self.iface.messageBar().pushMessage("Could not commit %s observations" % obsType,
                                                        Qgis.Critical)
                layer.updateExtents()
        self.mapCanvas.refresh()

    def checkLayerExists(self, layerid, message):
        # returns:
        # 1: layer exists
        # 2: does not exist, settings has been open, so loop once more (i.e. continue)
        # 3: does not exist, settings not edited, so cancel
        layer = QgsProject.instance().mapLayer(layerid)
        if layer is not None:
            return 1, layer

        reply = QMessageBox.question(self.iface.mainWindow(), "Intersect It",
                                     message + " Would you like to open settings?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if MySettingsDialog().exec():
                return 2, None
        return 3, None

    def checkFieldExists(self, layer, field, message):
        # returns:
        # 1: field exists
        # 2: does not exist, settings has been open, so loop once more (i.e. continue)
        # 3: does not exist, settings not edited, so cancel
        if layer.fields().lookupField(field) != -1:
            return 1

        reply = QMessageBox.question(self.iface.mainWindow(), "Intersect It",
                                     message + " Would you like to open settings?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if MySettingsDialog().exec():
                return 2
        return 3
