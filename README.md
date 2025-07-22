# Attrio CSV: Per-Frame Geometry Data Export & Import via CSV

**Attrio CSV** enables per-frame evaluated dependency graph data to be exported as a series of CSV files for external analysis or modification. These CSV files can later be reimported into Blender as point cloud data using custom Geometry Node trees and the **CSV Import** node - for further modification and use, or to reduce depsgraph computation complexity by referencing stored data.

---

## Exporting Data

The **active object** is always used as the data source. When the active object is of type **Mesh** or **Point Cloud**, users can choose a valid attribute domain from a contextual dropdown menu. Once a domain is selected, clicking **Refresh Attributes** will populate a list of available attributes on that domain. Users may select any combination of these attributes for export.

An optional **Export Frame Range** toggle allows for baking across a start and end frame. When enabled, a separate CSV file is written for each frame in the range.  
**Note:** Depending on frame count, selected attributes, and precision settings, this can result in large total file sizes.

When the frame range is disabled, only the current frame is exported. In either case, the output filename uses the format:

```
[name]_[####].csv
```
Where `####` is a four-digit frame number with leading zeroes.

>**Note:** Including `_` (underscore) within naming will export correctly, but will break the import parsing system, do not include underscore in `Name` if you intend to import back into Blender using Attrio import methods.

### Output Path Structure

The full path for each exported CSV follows this structure:

```
[directory]/[subfolder]/[name]_[####].csv
```

- **Directory**: The base folder for export (absolute or relative).
- **Subfolder**: A user-defined folder (String) inside the directory to organize CSVs.
- **Name**: The base name used in the filename of each CSV.
- **####**: The padded frame number (e.g. `0023`).

This system ensures exported files are grouped cleanly by run, allowing easy batch import and reuse.

---

## CSV Output Behavior

This export behaves similarly to a "spreadsheet to CSV" operation, with a few critical distinctions:

- **Data is _not_ sourced directly from the Spreadsheet editor.** Instead, all values are pulled from the **evaluated dependency graph**, ensuring stable and reliable output without context-sensitive hacks.
- Only **Mesh** and **Point Cloud** object types are supported.
- **Internal attributes** (those prefixed with `.` and hidden in the spreadsheet) are never included.
- **Vector-based attributes** (including Position, UVs, and Color) are split into separate columns:  
  e.g., `position_x`, `position_y`, `position_z`.

### Supported Attribute Types

- Floats
- Integers
- Vectors (including UV Maps)
- Colors
- Booleans

Custom-named attributes and named outputs are supported as long as they match supported types and valid domains.

---

## Data Precision

To balance file size and accuracy, two precision modes are available:

- **Full Precision (Float64)** – maximum numerical accuracy
- **Reduced Precision (Float32)** – smaller files, lower fidelity

---

## Importing Data

CSV files written by Attrio CSV can be reimported into Blender for use in Geometry Nodes. Each CSV represents a single frame of data.

Import relies on the same **Directory**, **Subfolder**, and **Name** settings used during export. If valid files are detected, import options will appear.

### 1. Import Data as Point Cloud

Creates a new `MESH` object with a Geometry Node modifier that loads point cloud data from the CSVs. Data is read from the **current scene frame**, or manually via a `Frame` input on the modifier.

### 2. Import with Position Data  
*(only shown when position attributes exist)*

Creates a mesh object with Geometry Nodes that interpret the CSV position attributes and reconstruct the point cloud per frame. This demonstrates how to parse and animate point-based position data from Attrio CSV.

An additional **Use Source Mesh** option allows transferring this position data to another mesh—effectively deforming its vertices to match the CSV frame data. This is useful for mesh-based playback while maintaining a link to other attributes.

In both import types, additional attributes can still be parsed from the point cloud and remapped to other domains as needed.

---

## Frame Syncing & Playback

By default, data is synchronized with the **scene frame**. A `Use Scene Time` toggle is available in both node groups:

- When enabled, playback is frame-locked to the timeline.
- When disabled, the user can override the frame using the `Frame` input manually.

> **Note:** Data is only valid when either:  
> - `Use Scene Time` is enabled and the current scene frame has a corresponding CSV  
> - `Use Scene Time` is disabled and the `Frame` input matches a valid frame file

---
