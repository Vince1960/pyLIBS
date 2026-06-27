# pyLIBS Changelog

------------------------------------------------------------

## Unreleased

### Changed

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
- Manual Fit now stores residuals after a successful Voigt fit and shows them in a single compact LIBS++-style Residuals plot window on request.
- Manual Fit and Automatic Fit no longer show the legacy Expand button.
- Spectrum open dialogs now use a shared filter list with lowercase/uppercase extensions for TXT, DAT, ROH, TRT, MCH, JND, ASC, and CSV files.
- Toolbar buttons now use the newly supplied PNG icons for Clear, Active Spectra, templates, H-alpha, and fit actions.
- Remaining Italian user-visible messages in dialogs and status text were translated to English.

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
- background colour persistence

### Internal

- Codex development workflow introduced

------------------------------------------------------------

Future releases should be added at the top of this file.
