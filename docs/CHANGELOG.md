# pyLIBS Changelog

------------------------------------------------------------

## Unreleased

### Changed

- The OPC window now accepts nominal compositions as either `Mass %` or `Number %`. Mass input is converted internally to Number % with database atomic masses before the unchanged Palleschi OPC ratio is evaluated.
- Authoritative Voigt fitting now defaults to Palleschi's local-linear baseline. The optional BIC comparison is diagnostic only and never replaces Palleschi areas with a constant-baseline result.
- Only explicitly selected analytical lines enter the quantitative multi-Voigt model. Residual neighbouring peaks are no longer inserted automatically and must be selected deliberately before refitting.
- Added `File > Load independent windows...`: detector windows can now remain analytically separate, with no interpolation or cross-fade in overlaps. Voigt fitting selects one real window per line group, honours the `Active Spectra` choice in overlaps and rejects groups that would bridge windows.
- Saha-Boltzmann, ordinary Boltzmann, IRSAC observations and their diagnostic points now use the assigned NIST transition wavelength for the radiometric ordinate and Apply After response lookup; the observed Voigt center is retained only for peak localization, coverage and fit diagnostics.
- Boltzmann, Saha-Boltzmann, CF-LIBS, OPC and theoretical synthesis now share the radiometric ordinate `ln[5.0341166e15 * Icorr * lambda_nm / abs(Aki*gk)]`; the theoretical and OPC paths use its exact inverse.
- `pyLIBS.ini` now stores option groups as INI sections instead of `//` comment separators, while still reading legacy files.
- The Help > Manual command now opens `docs/pyLIBS_Manual.pdf` through the system PDF viewer and shows a clear warning if the file is missing or cannot be opened.
- Voigt line fitting now requires exactly as many spectrum points as free model parameters, and it keeps expanding the current X window by 50% until that condition is met.
- Added View menu commands to save and load window positions for the main window, fit windows, Trace, Template, Saha-Boltzmann, Show SA, and CF-LIBS.
- Saha-Boltzmann now builds and plots fitted template-line points with session electron-density input, Unit27 temperature iteration, and safe Apply After response correction.
- Saha-Boltzmann mean temperature can exclude/include individual elements without changing their fitted temperatures.
- Saha-Boltzmann now auto-excludes out-of-range element temperatures and redraws fixed-temperature intercept-only fit lines.
- Saha-Boltzmann fixed-temperature fit lines now span the full usable plot x-range.
- Saha-Boltzmann now computes automatically on window open and applies plot margins.
- Added a Single Fit command and toolbar button for fitting only the currently visible template lines.
- Added the first auto-populated CF-LIBS analysis window with fixed-temperature Boltzmann plots and concentration output.
- CF-LIBS results table was simplified and can now be saved as a text report.
- CF-LIBS reports now export a complete HTML/text analysis report with spectrum metadata, a spectrum PNG, response-normalization details, template contents, H-alpha information, Saha-Boltzmann temperatures, plasma parameters, and final concentrations.
- CF-LIBS concentration display and reports now show normalized Number % and Mass % values instead of raw concentration fractions.
- CF-LIBS reports are now generated through a single Report Preview window with Save and Close actions, and no longer include the H-alpha electron-density formula/source field.
- CF-LIBS Show Report now opens temporary HTML reports in the system default HTML viewer and falls back to source preview if the viewer cannot be launched.
- Saha-Boltzmann and CF-LIBS plots now support LIBS++-style Shift-click analytical point exclusion/reactivation using the sign of template Aki.
- CF-LIBS includes Palleschi's One Point Calibration on nominal number percentages and saves wavelength-dependent `.opc` response calibration files. OPC number references remain separate from the mass percentages stored by Standard Correction in `.STD` files.
- Manual Fit now stores residuals after a successful Voigt fit and shows them in a single compact LIBS++-style Residuals plot window on request.
- Manual Fit and Automatic Fit no longer show the legacy Expand button.
- Voigt fitting now automatically expands the current X window by 50% and retries when too few spectrum points are available.
- Spectrum open dialogs now use a shared filter list with lowercase/uppercase extensions for TXT, DAT, ROH, TRT, MCH, JND, ASC, and CSV files.
- Toolbar buttons now use the newly supplied PNG icons for Clear, Active Spectra, templates, H-alpha, and fit actions.
- Remaining Italian user-visible messages in dialogs and status text were translated to English.
- File > Save with Labels now exports the main spectrum as CSV with nearest-point template identification labels.
- Batch Average now loads saved average and optional standard-deviation spectra into the comparison view after saving.
- Drop-down menus now show and activate LIBS++-style keyboard accelerators and small menu icons where matching pyLIBS icons are available.

------------------------------------------------------------

## v8.18

### Added

- Git repository
- AGENTS.md
- project documentation
- TODO list
- architecture documentation
- project state

### Fixed

- legacy pyLIBS.ini positional parsing
- GridX persistence
- GridY persistence
- LogX persistence
- LogY persistence
- background color persistence

### Internal

- Codex development workflow introduced

------------------------------------------------------------

Future releases should be added at the top of this file.
