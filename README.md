# Intersect It

A QGIS plugin to **reconstruct points from survey-style measurements** —
distances and bearings — and to draw the corresponding dimensions on the map.

Typical use case: rebuilding a cadastral corner from a written parcel
description ("from monument A, the corner is 12.45 m at azimuth 87°30';
from monument B, 8.20 m at 162°10'"). Intersect It turns those measurements
into geometry, intersects them, and stores the result with full residuals
and a least-squares precision estimate.

> **Versions**
> - 4.x — QGIS 3.40 LTS and QGIS 4 (PyQt5/PyQt6 via `qgis.PyQt`)
> - 3.x — QGIS 3
> - 2.x and earlier — QGIS 2

`numpy` is required for the *advanced intersection* (least-squares adjustment).
It ships with QGIS, so you normally don't have to install anything.

## Concepts

Intersect It works with three kinds of objects:

| Object | Stored where | Meaning |
|---|---|---|
| **Observation** | scratch memory layers (auto-created) | One measurement: a distance circle or an orientation line. |
| **Intersection point** | a point layer *you* choose in the settings | The reconstructed point — the result of intersecting 2+ observations. |
| **Dimension** | a line layer *you* choose in the settings | A drawing element (arc for distance, segment for orientation) representing the observation on the final map. |

Observations are temporary working data and live in two memory layers the
plugin creates on first use: **IntersectIt Points** (the measurement origins)
and **IntersectIt Lines** (the distance circles and orientation rays).
You may delete them at any time with the eraser icon.

Intersection points and dimensions are the *output*: they go into vector
layers you control. The plugin will not create those for you.

## Toolbar

| Icon | Tool |
|---|---|
| Place distance | Start a distance observation from a snapped point. |
| Place orientation | Start an orientation (bearing) observation along a snapped segment. |
| Simple intersection | Snap to the geometric intersection of two existing features and write a point. |
| Advanced intersection | Pick 2+ observations near the cursor and solve their intersection (least-squares for n>2). |
| Edit distance dimension | Reshape an arc dimension (move the bulge). |
| Edit orientation dimension | Reshape an orientation dimension. |
| Eraser | Clear all observations (the two memory layers). |
| Settings | Configure layers, fields, snap tolerance, rubber-band styling. |
| Help | Open this page. |

## Quick start — cadastral example

You have a parcel description giving distances and bearings from two known
boundary monuments **A** and **B** to a corner **C** you want to reconstruct
on the map.

### 1. Prepare your layers

Before launching any tool, create (or open) the layers Intersect It will
write into. Suggested layout for a cadastral project:

| Layer | Geometry | Purpose | Suggested fields |
|---|---|---|---|
| `parcel_corners` | Point | The reconstructed corner points. | `report` (text) — receives the least-squares report; optional `pid` for the parcel id. |
| `dimensions_distance` | LineString | Arc dimensions for distances. | `obs` (double), `prec` (double) |
| `dimensions_orientation` | LineString | Line dimensions for bearings. | `obs` (double), `prec` (double) |
| `monuments` | Point | The known points A, B, …, snapped from. | whatever you already have. |

Make sure the **project CRS is a projected (metric) CRS** — distances are
interpreted in map units. A geographic CRS will give nonsense results.

Toggle editing on the three output layers before using the tools (the plugin
writes through `editBuffer`).

### 2. Configure Intersect It

Open the **Settings** dialog (gear icon) and set, at minimum:

- **Advanced intersection → write point**: ✔, layer = `parcel_corners`,
  `Write report` ✔, field = `report`.
- **Distance dimension → write**: ✔, layer = `dimensions_distance`,
  observation field = `obs`, precision field = `prec`.
- **Orientation dimension → write**: ✔, layer = `dimensions_orientation`,
  observation field = `obs`, precision field = `prec`.
- **Default precisions**: typical cadastral values are around 0.025 m for
  distance and 0.5 gon (or your unit) for orientation — adjust to your
  instrument's expected error.
- **Snap tolerance / units**: pixels for screen-relative behavior, map for
  a fixed metric tolerance.

### 3. Place the observations

1. Activate **Place distance**. Snap to monument **A**. A dialog appears —
   enter the measured distance (e.g. `12.45`) and the expected precision
   (`0.025` m). OK. A red circle appears around A.
2. Repeat for monument **B** with its distance.
3. If your description also gives bearings, use **Place orientation**: snap
   along the baseline that defines azimuth 0 (or whatever your reference is)
   from the monument, then enter the azimuth measurement.

The observations are kept in the *IntersectIt Lines* memory layer and you
can see them painted over your map.

### 4. Solve for the corner

Activate **Advanced intersection** and move the cursor near the cluster of
observations you want to combine. The observations within the configured
snap tolerance light up in the rubber band. Click.

A dialog opens showing:
- the list of observations included (you can uncheck individual rows),
- the **least-squares report** with residuals, a-posteriori sigma, and a
  precision per coordinate,
- the proposed solution point.

If two distances or one distance + one orientation are passed, the
geometric (closed-form) intersection is used. With three or more,
least-squares adjustment iterates until convergence (settings:
`advancedIntersecLSmaxIteration`, `advancedIntersecLSconvergeThreshold`).

Click **OK**. The plugin writes:
- a point in `parcel_corners` with the report stored in the `report` field,
- arc dimensions from each monument to C in `dimensions_distance`,
- line dimensions in `dimensions_orientation` if any orientations were used.

### 5. Tidy up

Once you've stored the corner and its dimensions, click the eraser to
remove the working observations. Repeat for the next corner.

## Simple intersection

For cases where the corner is already defined geometrically by two existing
lines on the map (cadastral lines, walls, etc.), use **Simple intersection**.
It snaps to the intersection of two features regardless of layer and stores
a point in the configured `simpleIntersectionLayer`. No observation is
involved.

The target layer must be **in edit mode** when you click.

## Editing dimensions

The two *Edit dimension* tools let you reshape stored dimensions without
touching the observation:

- **Edit distance dimension**: click on an existing arc and drag the bulge
  point. The arc still passes through the same two endpoints.
- **Edit orientation dimension**: click on an existing line and drag — the
  line's bearing is preserved, only its length/position is updated.

Useful for cleaning up overlapping dimensions on a finished plan.

## Files & layout

```
intersectit/
├── intersectit_plugin.py      # plugin entry: toolbar, actions
├── core/                      # geometry & math (no Qt UI)
│   ├── arc.py, distance.py, orientation.py, orientation_line.py
│   ├── observation.py, memory_layers.py
│   ├── intersections.py       # closed-form 2-observation solvers
│   └── least_squares.py       # numpy-based LS adjustment for n ≥ 3
├── gui/                       # map tools and dialogs
│   ├── _snap.py               # shared QGIS 3+ snapping override helper
│   └── *_maptool.py, *_dialog.py
├── ui/                        # Qt Designer .ui files + generated ui_*.py
├── qgissettingmanager/        # submodule: settings framework
└── icons/                     # toolbar icons
```

## Building from source

```bash
git clone <repo-url>
cd intersectit
git submodule update --init    # pulls in qgissettingmanager
make compile                    # regenerates ui/ui_*.py from .ui files
make deploy QGIS_DIR=~/Library/Application\ Support/QGIS/QGIS3/profiles/default   # macOS
# Linux default:  QGIS_DIR=~/.local/share/QGIS/QGIS3/profiles/default
```

## License

GPL v2 or later. See file headers for copyright.

## Authors

- Denis Rouzaud — original author (2013–2017)
- Volkmar Herbst — QGIS 3/4 port and current maintainer
