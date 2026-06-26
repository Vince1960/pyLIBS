# pyLIBS Architecture

## Overview

pyLIBS is the Python rewrite of the historical LIBS++ software.

The objective is to reproduce the behaviour of the original application while
keeping the code maintainable and progressively modernising the implementation.

The current implementation is intentionally organised around the same workflow
used in LIBS++.

------------------------------------------------------------

MAIN WORKFLOW

        Spectrum
            │
            ▼
      Peak detection
            │
            ▼
    Line identification
            │
            ▼
      Line fitting
            │
            ▼
 Electron density (Ne)
            │
            ▼
 Plasma temperature
            │
            ▼
      CF-LIBS analysis
            │
            ▼
   Self absorption
            │
            ▼
    Final composition

------------------------------------------------------------

Project files

pyLIBS_python_prototype_v8_18_incremental_template_update.py

Current monolithic implementation.

Future versions may split this into modules.

------------------------------------------------------------

Databases

LIBS.db

Main atomic database.

Contains:

- atomic transitions
- wavelengths
- Aki
- gi
- gk
- Ei
- Ek
- partition functions
- certified lines

Stark.db

Database of Stark broadening coefficients.

Future versions should integrate it more completely.

------------------------------------------------------------

Configuration

pyLIBS.ini

Stores persistent program options.

Current items include:

- wavelength limits
- fitting parameters
- response correction
- last directory
- GridX
- GridY
- LogX
- LogY
- background colour

Compatibility with the historical positional format must be preserved.

------------------------------------------------------------

Main logical objects

Spectrum

Represents one spectrum.

Contains

- wavelength
- intensity
- visibility
- colour
- scaling
- response correction

------------------------------------------------------------

Template

Represents the list of detected spectral lines.

Each TemplateLine may contain

- measured wavelength
- assigned wavelength
- element
- ion stage
- peak intensity
- integrated intensity
- Gaussian width
- Lorentzian width
- Voigt parameters
- Aki
- gi
- gk
- Ek

------------------------------------------------------------

Database layer

LibsDatabase

Responsibilities

- wavelength search
- Trace Lines
- identification
- atomic parameters
- partition functions

------------------------------------------------------------

GUI

MainWindow

Coordinates the entire application.

Responsible for

- menus
- toolbar
- plotting
- spectrum management
- template management
- dialogs

------------------------------------------------------------

Current implemented analyses

✓ Find Peaks

✓ Manual peak marking

✓ Manual identification

✓ Trace Lines

✓ Voigt fitting

✓ Multi-Gaussian fitting

✓ Electron density

✓ Saha-Boltzmann

✓ CF-LIBS

✓ Standard correction

------------------------------------------------------------

Known architectural issues

The program still contains:

- duplicate helper functions

- monkey-patching of MainWindow

- a single Python file (~15000 lines)

These should be addressed only after behavioural compatibility has been verified.

------------------------------------------------------------

Future modular architecture

pyLIBS/

    gui.py

    spectrum.py

    database.py

    template.py

    fitting.py

    cf_libs.py

    saha.py

    stark.py

    plotting.py

    options.py

    io.py

MainWindow should become only the GUI coordinator.

Scientific algorithms should be isolated from the interface.

------------------------------------------------------------

Development principles

Always preserve:

- historical behaviour
- database compatibility
- template compatibility
- INI compatibility

Never introduce behavioural changes unless explicitly requested.

Small commits.

One feature at a time.

Behaviour first.

Refactoring later.
