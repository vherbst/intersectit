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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QDialog, QComboBox, QLabel,
                                 QHBoxLayout, QGridLayout, QBoxLayout,
                                 QMessageBox)
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox, QgsColorButton

from ..qgissettingmanager import SettingDialog

from ..core.mysettings import MySettings

from ..ui.ui_settings import Ui_Settings


# (label shown in the combo, language code stored in settings)
LANGUAGES = [
    ("Auto (follow QGIS)", ""),
    ("English",            "en"),
    ("ລາວ (Lao)",          "lo"),
    ("Español",            "es"),
    ("Deutsch",            "de"),
    ("Français",           "fr"),
]


class MySettingsDialog(QDialog, Ui_Settings, SettingDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        self.settings = MySettings()

        self._build_language_selector()
        # qgissettingmanager v3 only supports QgsColorButton for Color settings;
        # the .ui still has rubberColor as a QLabel from the Qt4 era. Swap it
        # in place so init_widgets() can bind to a supported widget type.
        self._swap_color_label_for_button("rubberColor")

        # distance combos
        self.dimensionDistanceLayer.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.dimensionDistanceLayer.layerChanged.connect(self.dimensionDistanceObservationField.setLayer)
        self.dimensionDistanceLayer.layerChanged.connect(self.dimensionDistancePrecisionField.setLayer)

        # orientation combos
        self.dimensionOrientationLayer.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.dimensionOrientationLayer.layerChanged.connect(self.dimensionOrientationObservationField.setLayer)
        self.dimensionOrientationLayer.layerChanged.connect(self.dimensionOrientationPrecisionField.setLayer)

        # other combos
        self.simpleIntersectionLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.advancedIntersectionLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.advancedIntersectionLayer.layerChanged.connect(self.reportField.setLayer)

        SettingDialog.__init__(self, self.settings)
        # qgissettingmanager v3 separated configuration from binding: SettingDialog
        # only registers the dialog; init_widgets() is what actually walks the
        # form, attaches setting<->widget binders, and loads stored values.
        self.init_widgets()

    def _swap_color_label_for_button(self, object_name):
        old = getattr(self, object_name, None)
        if old is None:
            return
        parent = old.parentWidget()
        layout = parent.layout() if parent is not None else None
        new = QgsColorButton(parent)
        new.setObjectName(object_name)
        new.setAllowOpacity(True)
        if isinstance(layout, QGridLayout):
            idx = layout.indexOf(old)
            if idx >= 0:
                row, col, rowspan, colspan = layout.getItemPosition(idx)
                layout.removeWidget(old)
                old.deleteLater()
                layout.addWidget(new, row, col, rowspan, colspan)
        elif isinstance(layout, QBoxLayout):
            idx = layout.indexOf(old)
            layout.removeWidget(old)
            old.deleteLater()
            layout.insertWidget(idx, new)
        else:
            old.deleteLater()
        setattr(self, object_name, new)

    def _build_language_selector(self):
        # The language setting is read once at plugin load (translators install
        # globally), so changing it here only takes effect after reloading
        # Intersect It. We add the combo to the "General" tab via the existing
        # QTabWidget; structure of the .ui file is fixed in code so we don't
        # have to regenerate ui_settings.py.
        self._lang_combo = QComboBox(self)
        for label, code in LANGUAGES:
            self._lang_combo.addItem(label, code)
        current = self.settings.value("language") or ""
        idx = next((i for i, (_, c) in enumerate(LANGUAGES) if c == current), 0)
        self._lang_combo.setCurrentIndex(idx)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Plugin language"), self))
        row.addWidget(self._lang_combo, 1)

        # The General tab is a QGridLayout; append the language row at the
        # bottom spanning all columns. Fall back to QBoxLayout.insertLayout or
        # addLayout for any other layout type, just in case the .ui changes.
        general_tab = self.tabWidget.widget(0)
        layout = general_tab.layout()
        if isinstance(layout, QGridLayout):
            row_idx = layout.rowCount()
            col_span = max(1, layout.columnCount())
            layout.addLayout(row, row_idx, 0, 1, col_span)
        elif isinstance(layout, QBoxLayout):
            layout.insertLayout(0, row)
        elif layout is not None:
            try:
                layout.addLayout(row)
            except TypeError:
                pass

    def accept(self):
        # Persist the language override and warn the user that a reload is
        # required for it to take effect (QTranslator is installed at load).
        new_code = self._lang_combo.currentData() or ""
        old_code = self.settings.value("language") or ""
        if new_code != old_code:
            self.settings.set_value("language", new_code)
            QMessageBox.information(
                self, "Intersect It",
                self.tr("Language changed. Disable and re-enable the plugin "
                        "(or restart QGIS) for the new language to take effect."),
            )
        QDialog.accept(self)