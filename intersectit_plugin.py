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


import os

from qgis.PyQt.QtCore import QUrl, QCoreApplication, QFileInfo, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QAction

from .core.memory_layers import MemoryLayers

from .gui.my_settings_dialog import MySettingsDialog
from .gui.dimension_edit_maptool import DimensionEditMapTool
from .gui.distance_maptool import DistanceMapTool
from .gui.orientation_maptool import OrientationMapTool
from .gui.advanced_intersection_maptool import AdvancedIntersectionMapTool
from .gui.simple_intersection_maptool import SimpleIntersectionMapTool

PLUGIN_DIR = os.path.dirname(__file__)


def _icon(name):
    return QIcon(os.path.join(PLUGIN_DIR, "icons", name))


class IntersectIt():
    def __init__(self, iface):
        self.iface = iface
        self.mapCanvas = iface.mapCanvas()

        # Translation: a plugin-level override takes precedence over the QGIS
        # locale. This lets the plugin show Lao even when QGIS itself runs in
        # English (the common case in Laos, where there is no QGIS Lao build).
        # The override is stored as a String setting under "intersectit/language";
        # we read it via QSettings directly to avoid importing MySettings (which
        # transitively pulls in qgis.core) at the very top of __init__.
        from qgis.PyQt.QtCore import QSettings as _QS
        override = _QS().value("intersectit/language", "", type=str)
        qgis_locale = _QS().value("locale/userLocale") or ""
        myLocale = override[0:2] if override else qgis_locale[0:2]
        qm_path = os.path.join(PLUGIN_DIR, "i18n", "intersectit_{}.qm".format(myLocale))
        if myLocale and QFileInfo(qm_path).exists():
            self.translator = QTranslator()
            self.translator.load(qm_path)
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self.toolBar = self.iface.addToolBar("IntersectIt")
        self.toolBar.setObjectName("IntersectIt")

        # settings
        self.uisettingsAction = QAction(_icon("settings.svg"),
                                        QCoreApplication.translate("IntersectIt", "settings"), self.iface.mainWindow())
        self.uisettingsAction.triggered.connect(self.showSettings)
        self.iface.addPluginToMenu("&Intersect It", self.uisettingsAction)
        # distance
        self.distanceAction = QAction(_icon("distance.svg"),
                                      QCoreApplication.translate("IntersectIt", "place distance"), self.iface.mainWindow())
        self.distanceAction.setCheckable(True)
        self.distanceMapTool = DistanceMapTool(self.iface)
        self.distanceMapTool.setAction(self.distanceAction)
        self.toolBar.addAction(self.distanceAction)
        self.iface.addPluginToMenu("&Intersect It", self.distanceAction)
        # prolongation
        self.orientationAction = QAction(_icon("prolongation.svg"),
                                         QCoreApplication.translate("IntersectIt", "place orientation"),
                                         self.iface.mainWindow())
        self.orientationAction.setCheckable(True)
        self.orientationMapTool = OrientationMapTool(self.iface)
        self.orientationMapTool.setAction(self.orientationAction)
        self.toolBar.addAction(self.orientationAction)
        self.iface.addPluginToMenu("&Intersect It", self.orientationAction)
        # separator
        self.toolBar.addSeparator()
        # simple intersection
        self.simpleIntersectionAction = QAction(_icon("intersection_simple.svg"),
                                                QCoreApplication.translate("IntersectIt", "simple intersection of 2 objects"),
                                                self.iface.mainWindow())
        self.simpleIntersectionAction.setCheckable(True)
        self.simpleIntersectionMapTool = SimpleIntersectionMapTool(self.iface)
        self.simpleIntersectionMapTool.setAction(self.simpleIntersectionAction)
        self.toolBar.addAction(self.simpleIntersectionAction)
        self.iface.addPluginToMenu("&Intersect It", self.simpleIntersectionAction)
        # advanced intersection
        self.advancedIntersectionAction = QAction(_icon("intersection_advanced.svg"),
                                                  QCoreApplication.translate("IntersectIt", "advanced intersection of 2+ observations"),
                                                  self.iface.mainWindow())
        self.advancedIntersectionAction.setCheckable(True)
        self.advancedIntersectionMapTool = AdvancedIntersectionMapTool(self.iface)
        self.advancedIntersectionMapTool.setAction(self.advancedIntersectionAction)
        self.toolBar.addAction(self.advancedIntersectionAction)
        self.iface.addPluginToMenu("&Intersect It", self.advancedIntersectionAction)
        # separator
        self.toolBar.addSeparator()
        # dimension distance edit
        self.dimensionDistanceAction = QAction(_icon("dimension_distance.svg"),
                                               QCoreApplication.translate("IntersectIt", "edit distance dimension"),
                                               self.iface.mainWindow())
        self.dimensionDistanceAction.setCheckable(True)
        self.dimensionDistanceMapTool = DimensionEditMapTool(self.iface, "distance")
        self.dimensionDistanceMapTool.setAction(self.dimensionDistanceAction)
        self.toolBar.addAction(self.dimensionDistanceAction)
        self.iface.addPluginToMenu("&Intersect It", self.dimensionDistanceAction)
        # dimension orientation edit
        self.dimensionOrientationAction = QAction(_icon("dimension_orientation.svg"),
                                                  QCoreApplication.translate("IntersectIt", "edit orientation dimension"),
                                                  self.iface.mainWindow())
        self.dimensionOrientationAction.setCheckable(True)
        self.dimensionOrientationMapTool = DimensionEditMapTool(self.iface, "orientation")
        self.dimensionOrientationMapTool.setAction(self.dimensionOrientationAction)
        self.toolBar.addAction(self.dimensionOrientationAction)
        self.iface.addPluginToMenu("&Intersect It", self.dimensionOrientationAction)
        # separator
        self.toolBar.addSeparator()
        # cleaner
        self.cleanerAction = QAction(_icon("eraser.svg"),
                                     QCoreApplication.translate("IntersectIt", "erase construction features"),
                                     self.iface.mainWindow())
        self.cleanerAction.triggered.connect(self.clean_memory_layers)
        self.toolBar.addAction(self.cleanerAction)
        self.iface.addPluginToMenu("&Intersect It", self.cleanerAction)
        # help
        self.helpAction = QAction(_icon("help.svg"),
                                  QCoreApplication.translate("IntersectIt", "help"), self.iface.mainWindow())
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToMenu("&Intersect It", self.helpAction)

        self.toolBar.actionTriggered.connect(self.setMapTool)

    def help(self):
        QDesktopServices().openUrl(QUrl("https://github.com/3nids/intersectit/wiki"))

    def unload(self):
        self.iface.removePluginMenu("&Intersect It", self.distanceAction)
        self.iface.removePluginMenu("&Intersect It", self.orientationAction)
        self.iface.removePluginMenu("&Intersect It", self.simpleIntersectionAction)
        self.iface.removePluginMenu("&Intersect It", self.advancedIntersectionAction)
        self.iface.removePluginMenu("&Intersect It", self.dimensionDistanceAction)
        self.iface.removePluginMenu("&Intersect It", self.dimensionOrientationAction)
        self.iface.removePluginMenu("&Intersect It", self.uisettingsAction)
        self.iface.removePluginMenu("&Intersect It", self.cleanerAction)
        self.iface.removePluginMenu("&Intersect It", self.helpAction)
        self.iface.removeToolBarIcon(self.distanceAction)
        self.iface.removeToolBarIcon(self.orientationAction)
        self.iface.removeToolBarIcon(self.simpleIntersectionAction)
        self.iface.removeToolBarIcon(self.advancedIntersectionAction)
        self.iface.removeToolBarIcon(self.dimensionDistanceAction)
        self.iface.removeToolBarIcon(self.dimensionOrientationAction)
        self.iface.removeToolBarIcon(self.uisettingsAction)
        self.iface.removeToolBarIcon(self.cleanerAction)
        self.iface.removeToolBarIcon(self.helpAction)
        del self.toolBar
        MemoryLayers(self.iface).remove_layers()

    def setMapTool(self, action):
        if action == self.distanceAction:
            self.mapCanvas.setMapTool(self.distanceMapTool)
        if action == self.orientationAction:
            self.mapCanvas.setMapTool(self.orientationMapTool)
        if action == self.simpleIntersectionAction:
            self.mapCanvas.setMapTool(self.simpleIntersectionMapTool)
        if action == self.advancedIntersectionAction:
            self.mapCanvas.setMapTool(self.advancedIntersectionMapTool)
        if action == self.dimensionDistanceAction:
            self.mapCanvas.setMapTool(self.dimensionDistanceMapTool)
        if action == self.dimensionOrientationAction:
            self.mapCanvas.setMapTool(self.dimensionOrientationMapTool)

    def clean_memory_layers(self):
        MemoryLayers(self.iface).clean_layers()

    def showSettings(self):
        MySettingsDialog().exec()
