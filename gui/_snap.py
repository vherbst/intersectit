# Snapping helper for QGIS 3 LTS / QGIS 4.
# Temporarily overrides the canvas snapping configuration to snap to vertices
# (and optionally edges/intersections) of any vector layer on the canvas
# regardless of the user's project-wide snapping settings.

from qgis.core import (
    QgsSnappingConfig,
    QgsTolerance,
    QgsVectorLayer,
)


# QgsSnappingConfig.SnappingTypeFlag is a Q_FLAG; its members are
# VertexFlag, SegmentFlag (called EdgeFlag in some 3.x builds),
# AreaFlag, CentroidFlag, MiddleOfSegmentFlag, LineEndpointFlag.
# We resolve at import time to tolerate the rename.
_VERTEX_FLAG = QgsSnappingConfig.VertexFlag
_EDGE_FLAG = getattr(QgsSnappingConfig, "SegmentFlag",
                     getattr(QgsSnappingConfig, "EdgeFlag", None))


def _layer_settings(tol, snap_flag):
    # Stable since 3.14:
    #   IndividualLayerSettings(enabled, type, tolerance, units, minScale, maxScale)
    return QgsSnappingConfig.IndividualLayerSettings(
        True, snap_flag, tol, QgsTolerance.ProjectUnits, 0.0, 0.0,
    )


def _snap_temporarily(canvas, map_point, layers, snap_flag, snap_on_intersections=False):
    tol = QgsTolerance.vertexSearchRadius(canvas.mapSettings())
    snap_util = canvas.snappingUtils()
    old_config = QgsSnappingConfig(snap_util.config())
    new_config = QgsSnappingConfig(snap_util.config())
    new_config.setEnabled(True)
    new_config.setMode(QgsSnappingConfig.AdvancedConfiguration)
    new_config.setIntersectionSnapping(snap_on_intersections)
    new_config.clearIndividualLayerSettings()
    settings = _layer_settings(tol, snap_flag)
    for layer in layers:
        new_config.setIndividualLayerSettings(layer, settings)
    snap_util.setConfig(new_config)
    try:
        return snap_util.snapToMap(map_point)
    finally:
        snap_util.setConfig(old_config)


def vector_layers(canvas):
    return [l for l in canvas.layers() if isinstance(l, QgsVectorLayer)]


def snap_to_vertex_all(canvas, map_point, snap_on_intersections=True):
    return _snap_temporarily(
        canvas, map_point, vector_layers(canvas),
        _VERTEX_FLAG, snap_on_intersections,
    )


def snap_to_edge_all(canvas, map_point, snap_on_intersections=False):
    return _snap_temporarily(
        canvas, map_point, vector_layers(canvas),
        _EDGE_FLAG, snap_on_intersections,
    )


def snap_to_edge_layer(canvas, map_point, layer):
    return _snap_temporarily(
        canvas, map_point, [layer],
        _EDGE_FLAG, False,
    )
