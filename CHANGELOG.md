# Changelog

## [0.9.0] - 2024-03-14

### Changed
- Reorganized the code into an installable package.
- Moved the example from from the top-level docstring in `mms_curvature.py` to `mms_curvature.mms_Curvature()`.

### Added
- An example and install instructions to the `README.md`.
- A `CHANGELOG.md` (this file).
- A `__init__.py` file to import the relevant functions in the top-level namespace. For example, you can calculate the curvature by calling `mms_curvature.mms_Curvature(...)`.

### Removed
- `mms_load_data_shims.py` because pyspedas has this functionality already.


## [0.8.0] - 2022-04-09

### Added
Harvey curvature vector is calculated.  Returns numpy arrays of:

- *t_master* => time series in unix time of the interpolated times for which the curvature is calculated
- *grad_Harvey* => grad(B/|B|) ordered in GSM coordinates
- *curve_Harvey* => k-vector of magnetic field line curvature in GSM coordinates and units of (1/km)

Radius of curvature calculation will be added shortly for greater application in the same way as the IDL version. 