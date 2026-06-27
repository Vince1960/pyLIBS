# pyLIBS Changelog

------------------------------------------------------------

## Unreleased

### Changed

- Saha-Boltzmann now builds and plots fitted template-line points with session electron-density input, Unit27 temperature iteration, and safe Apply After response correction.
- Saha-Boltzmann mean temperature can exclude/include individual elements without changing their fitted temperatures.
- Added a Single Fit command and toolbar button for fitting only the currently visible template lines.
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
