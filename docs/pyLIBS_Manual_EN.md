# pyLIBS - Complete User Manual

Manual version: 1.2 - 29 September 2026  
Software: pyLIBS 1.0.3  
Origin: LIBS++ by Vincenzo Palleschi and collaborators

> This manual describes the interface and scientific workflow actually implemented in pyLIBS. Command names are reproduced exactly as they appear in the program. Read at least Chapters 1-4 before performing the first quantitative analysis.

## Operating contents

1. Purpose and limitations
2. Essential concepts
3. Quick start: a complete measurement
4. Initial configuration
5. Main interface
6. Spectral files and loading
7. Dark signal, background and instrumental response
8. Wavelength calibration
9. Main analytical-line library and selected lines
10. Peak detection and identification
11. Automatic and manual Voigt fitting
12. Electron density from H-alpha
13. Saha-Boltzmann temperature
14. Self-absorption and IRSAC
15. CF-LIBS concentrations
16. Theoretical spectrum
17. Reports, saving and batch operations
18. Quality control and repeatability
19. Troubleshooting
20. Complete menu and field reference
21. Equations and glossary

<!-- pagebreak -->

## 1. Purpose and limitations

pyLIBS can:

- load one or more spectral windows;
- subtract the dark signal and background according to the configuration;
- divide each window by its own radiometric response;
- calibrate the wavelength axis of each window separately;
- merge and display windows, including overlapping windows;
- locate maxima that are actually observed;
- associate peaks with atomic lines from the offline database;
- perform single or multiple Voigt fits and integrate their areas;
- obtain Ne from the H-alpha width;
- estimate temperature with Saha-Boltzmann analysis;
- assess and, when supported, correct self-absorption;
- calculate atomic and mass percentages with CF-LIBS;
- assess robustness, exclusions and result sensitivity;
- produce reports and Excel results.

pyLIBS cannot make a measurement valid automatically. Reliable quantification requires, at a minimum, a suitable radiometric response, wavelength calibration, interference-free lines, checked Voigt areas, measured Ne, a temperature supported by a sufficient energy interval, and successful quality checks.

> Do not accept a displayed percentage when the CF-LIBS window reports a block, an unsafe correction or strong sensitivity to the removal of a single line.

## 2. Essential concepts

### 2.1 Three different wavelengths

Three distinct values may appear in the program:

- `wavelen`: analytical or NIST wavelength used for identification;
- `fitwavelen`: observed center obtained from the Voigt fit;
- spectral axis: wavelength read from the file and possibly changed by calibration.

The main line library should preferably contain NIST wavelengths. The fit searches for the observed maximum nearby and determines its center. Do not systematically replace the NIST value with the observed center.

### 2.2 Area, height and width

Boltzmann and CF-LIBS calculations use the integrated Voigt-profile area, not peak height alone. The main parameters are:

- `wg`: Gaussian width component;
- `wl`: Lorentzian width component;
- `fitwavelen`: profile center;
- `inte` or corrected area: integrated area used in the calculations.

When two lines are close, the program uses a multiple-Voigt fit and assigns an area to each component. The integration region must include the return to baseline on both sides.

### 2.3 Observed lines and database lines

A database line is a possible transition. It becomes a usable analytical line only when:

1. it falls within an actually acquired window;
2. a compatible measured maximum exists;
3. its element was requested in `Trace Lines`;
4. the atomic assignment is complete;
5. the Voigt fit is valid;
6. it passes the Aki threshold and quality checks.

### 2.4 Wavelength units

The program can work in nm or Angstrom. The files used by the system described in this manual are normally in nm. Do not press `Utilities > Signal Processing > Convert nm to Å` when the data and lists are already consistent in nm. H-alpha is normally specified as 656.28 nm or 6562.8 Angstrom.

### 2.5 Correct scientific sequence

The reference sequence is:

`dark/background -> radiometric response -> wavelength calibration -> window merging -> peak selection -> identification -> Voigt fit -> Ne -> Saha-Boltzmann -> self-absorption assessment -> CF-LIBS -> diagnostic theoretical spectrum`

Do not reverse IRSAC and Voigt fitting. IRSAC corrects intensities or areas that have already been measured; it does not create peaks and does not replace integration.

<!-- pagebreak -->

## 3. Quick start: a complete measurement

### 3.1 First run

The program directory must contain at least `pyLIBS.py`, the `pylibs` directory, the distributed databases and the `docs` directory. Python 3.11 or later and the packages listed in `requirements.txt` are required (`NumPy`, `SciPy`, `Matplotlib`, `OpenPyXL` and dependencies). For a new installation, open a terminal in the pyLIBS directory and run `python -m pip install -r requirements.txt`; then start the program with `python pyLIBS.py` or the supplied shortcut. If an error appears before the main window opens, do not start an analysis: retain the complete error text and check the Python environment, dependencies and program-file integrity.

On first launch, open `Help > User Manual > English` to verify that this document is available, then configure `Edit > Options...`. The program remembers the most recently used working directory, but this is not a substitute for an orderly experimental archive.

### 3.2 Quick procedure

This is the minimum procedure for an unknown sample.

1. Start `pyLIBS.py`.
2. Open `Edit > Options...` and check the database, dark subtraction, response, units and fitting parameters.
3. Load all sample windows with `File > Load independent windows...` when joins must be avoided completely. Use `File > Append...` only when a merged spectrum is explicitly required.
4. Confirm that the graph shows only the ranges that were actually acquired and that no oblique segments bridge gaps between windows.
5. Open `Utilities > Instrument Calibration > Instrument Response...`, load all response curves and apply `signal / response` if they are not already stored.
6. Open `Utilities > Instrument Calibration > Wavelength Calibration...`, load or paste known NIST lines, estimate every window and use `Apply and remember`.
7. Open `Utilities > Analytical Line Lists > Main Analytical-Line Library...` and confirm that the main line library is loaded.
8. In `Analyse > Spectral Fitting > Automatic Fit...`, use `Find visible peaks`; add any missing measured maxima with `Add peak from graph`.
9. Open `Analyse > Peak and Line Detection > Trace Lines...`, enter one element at a time, keep `Only near selected peaks` enabled, choose the ionization state and tolerance, then press `OK` and `Assign`.
10. Repeat Step 9 only for the elements to be analyzed. If an element was added by mistake, select it and press `Delete` or `Remove element (Del)`.
11. Return to `Auto Fit`, set or verify the ROIs and press `Fit selected peaks (Voigt)`. Check centers, areas, widths, replicate CV and quality.
12. Load H-alpha separately with `Analyse > Plasma Diagnostics > Electron Density from Hα...`; verify the correct maximum, run the fit and confirm Ne.
13. Open `Analyse > Plasma Diagnostics > Saha-Boltzmann Plot...`, select `Most reliable element` or an explicit species and calculate. Check the number of lines, levels, Delta Ek, R2 and leave-one-out stability.
14. Open `Analyse > Plasma Diagnostics > Self-Absorption / IRSAC...`. Read the diagnosis first. Apply the correction only when experimental evidence supports it.
15. Open `Analyse > Quantitative Analysis > CF-LIBS...`, use the current T and Ne, calculate, and inspect `Robustness` and `Show Report` before accepting the percentages.
16. Save the report with all measurement information.

> Do not use `OPC` as a mandatory step for an unknown sample. OPC is a calibration with a known standard and is useful only when a reliable nominal composition is available.

## 4. Initial configuration

Open `Edit > Options...`. Press `Save Options` when settings must remain available after restarting the program. `OK` applies them to the current session; `Cancel` discards unsaved changes.

### 4.1 Atomic library

- `LIBS++`: historical database of the original program.
- `NIST ASD 5.12`: offline database built from NIST ASD 5.12 data.
- `Browse...`: selects a compatible SQLite database.

For the workflow described here, normally use `NIST ASD 5.12`. The database is offline; Internet access is not required during analysis.

### 4.2 Dark-signal subtraction

- `Automatic from auxiliary columns`: uses one column as signal and compatible additional columns as dark data, according to the file structure.
- `Constant dark level`: subtracts the value entered in `Constant`.
- `Dark-spectrum file`: subtracts the trace selected with `Dark file...`.
- `No dark subtraction`: does not subtract a dark signal.

`Signal col. (0=auto)` selects the signal column. With 0, the program selects it automatically. `Dark cols.` specifies the dark columns. Always inspect the result on the graph: an incorrect dark signal changes the background, area and signal-to-noise ratio.

### 4.3 Correction and Global Correction

`Correction > Apply` enables the radiometric response. `Load files...` accepts multiple curves, one per window.

- `Apply Before`: divides the data by the response before fitting. This is the recommended workflow for obtaining radiometrically corrected areas directly.
- `Apply After`: retains the fit in the detector domain and subsequently corrects the analytical intensity. Use it only when the workflow has deliberately been defined this way.

Do not apply the response twice. The report states the domain and correction that were actually used.

### 4.4 Data Fit

- `Voigt baseline model = Local linear baseline` (default): uses a local baseline with a free intercept and slope.
- `Adaptive baseline-to-baseline limits`: automatically estimates the limits at which the profile returns to baseline.
- `Local constant baseline`: uses a constant local baseline.
- `Fix wg`, `Fix wl`, `Fix wavelength`: lock fitting parameters. Leave them disabled unless there is a specific experimental reason.
- `Iterations`: maximum optimizer work.
- `Instr. FWHM @ H-alpha`: global instrumental Gaussian width, not the total H-alpha peak width.

### 4.5 Boltzmann analysis and Aki threshold

Under `Boltzmann analysis > Intensity convention`, select the convention that matches the instrumental response:

- `Energy-domain response (convert with λ/hc)`: use when correction returns an energy-domain intensity, for example a quantity proportional to `W·m^-2`. The program converts energy to the equivalent photon number through `λ/(h·c)`;
- `Photon-counting response (original pyLIBS)`: use when the corrected intensity is already in photons or in counts with a photon-domain response. In this mode, `λ/(h·c)` must not be applied a second time.

Energy mode remains the default to preserve the current configuration. Changing convention invalidates existing Saha-Boltzmann, IRSAC and CF-LIBS results, which must be recalculated. Select the mode from the response units and calibration procedure, never from the expected result.

`Aki threshold` filters weak analytical lines. The default operating value is 1e5 s^-1. `Theory Aki threshold` controls the theoretical-spectrum threshold. Raising the threshold reduces weak lines and fragile identifications, but may leave too few energy levels for temperature determination.

### 4.6 Wavelength calibration

- `Legacy global Delta lambda`: single historical translation. It is not suitable when the shift differs among windows.
- `Use saved per-window calibration`: applies the stored profile independently to each window.
- `Per-window calibration...`: opens the procedure described in Chapter 8.

### 4.7 H-alpha parameters

The `wl1`, `dl1`, `Delta`, `wl2`, `dl2` and `kT` fields belong to the historical electron-density calculation. `Keep active Ne after Clear Graph` explicitly retains Ne between measurements in the same series. Leave it disabled when a new sample or laser condition requires a new Ne value.

### 4.8 Quantitative validation

`Suppress composition results that fail validation` prevents percentages without minimum supporting evidence from being presented as quantitative. The thresholds check, among other quantities:

- number of temperature lines and levels;
- Delta Ek interval and R2;
- slope error and leave-one-out sensitivity;
- dispersion of line populations;
- H-alpha quality and SNR;
- McWhirter margin;
- fraction of the observed ionization stage;
- relative Ne uncertainty;
- replicate Voigt-area CV, used as a precision warning rather than an automatic line filter;
- composition sensitivity to lines, replicates, T and Ne.

Do not relax thresholds simply to make a percentage appear. Correct the acquisition, lines, fits or physical parameters first.

### 4.9 Other Options fields

| Field | Meaning and use |
|---|---|
| Username | operator name stored in the configuration; it does not change calculations |
| Auto Offset | historical automatic-offset option; always verify the resulting background |
| Convert to Angstrom | multiplies an axis in nm by 10 during import; do not enable it for data already in Angstrom |
| Wavelength Limits | limits mainly used when importing historical formats; they must contain the acquired interval |
| Temperature Range | permitted kT range in eV; a boundary result requires investigation, not automatic range expansion |
| Electron Density Range | permitted Ne range in cm^-3; it is not the measured Ne value |
| Threshold | historical general detection threshold; it does not replace local peak and SNR checks |
| Delta min. | minimum half-width used by search/association functions; excessive values increase ambiguous assignments |
| Range | historical search interval around the expected position |
| Echelle | compatibility with the echelle workflow; leave disabled for ordinary linear windows |
| Self-absorption Mode | selects `Combined Stark-width and IRSAC correction`, `Stark-linewidth correction` or `IRSAC internal-reference correction`; see Chapter 14 |
| Thermometric species | species from which IRSAC first derives raw T and then its frozen corrected T; when empty, it uses the Saha reference or the species with the widest Ek interval |
| Fallback T | value used only when the thermometric species cannot provide a valid raw slope |

The ranges are validity limits, not values to adjust to improve a result artificially. After changing a scientific setting, press `Save Options` only when it should also become the default for later sessions.

### 4.10 Full reset

`Edit > Restore Factory Settings...` removes application customizations and restores the distributed values. Use it when old settings may be affecting a new analysis. After resetting, recheck the database, instrumental response and calibrations.

<!-- pagebreak -->

## 5. Main interface

The main window contains the menus, quick-access toolbar, graph and status bar.

### 5.1 Essential toolbar

- `Open`: opens one spectrum as the main spectrum.
- `Append`: loads multiple files or windows into the same session.
- `Clear`: clears the graph and measurement state; the persistent line library is reloaded.
- `Active Spectra`: displays, hides, scales or combines loaded spectra.
- `Response`: manages radiometric-response curves.
- `Full Scale`: restores the complete view.
- `Selected Lines`: opens the working analytical-line list.
- `Trace`: identifies lines for the requested elements.
- `Ne from H`: calculates Ne from H-alpha.
- `Auto Fit` and `Manual Fit`: perform Voigt fitting.
- `Saha-Boltzmann`: calculates temperature.
- `CF-LIBS`: calculates concentrations.

Move the pointer over an icon to display its name.

### 5.2 Graph navigation

Use the Matplotlib tools for zoom and pan. `View > Zoom and Scale > Fit X Axis`, `Fit Y Axis` and `Show Full Spectrum` restore the axes. `Utilities > Go To Wavelength...` centers the graph on a common or manually entered wavelength.

### 5.3 Status bar

The lower bar reports loading, corrections, active Ne, saved files and errors. Read it after each operation. A command that produces no visible change may have written a message to the status bar.

## 6. Spectral files and loading

### 6.1 Supported formats

The file selector supports TXT, DAT, ROH, TRT, MCH, JND, ASC and CSV, including uppercase extensions. ASCII files must contain at least two numerical columns: wavelength and intensity. Spaces, tabs or semicolons are accepted as separators; decimal commas are handled in files separated by spaces, tabs or semicolons.

### 6.2 Open, Append and Compare

- `File > Open...`: replaces the main spectrum with one file.
- `File > Append...`: loads multiple windows together and builds the merged spectrum.
- `File > Load independent windows...`: loads all windows from one measurement without joining, interpolating or averaging overlaps.
- `File > Compare...`: adds a spectrum for visual comparison.

To avoid joining artefacts, use `Load independent windows...` and select all windows from the same averaged acquisition at once. Every file keeps its own samples, wavelength calibration and instrumental response. Auto Fit and Manual Fit use one real detector window for each line group. If two windows contain the same line, the window selected in `Active Spectra` wins; otherwise the best-centred window is used. A fit that would require samples from two different windows is rejected.

`Append` remains available for compatibility and builds the merged spectrum. Source windows are still retained, but the main displayed curve contains the linear overlap transition.

### 6.3 Overlapping windows and missing intervals

In `Append` mode, overlapping windows are merged with a linear transition in the common region. In independent mode no transition is calculated: curves may overlap visually, but their samples remain separate. Unacquired intervals remain empty, and an atomic line outside every acquired window cannot enter the calculations.

### 6.4 Active Spectra

Open `Edit > Spectrum Management > Show Active Spectra`.

- double-click: shows or hides a secondary spectrum;
- right-click: selects a spectrum for multiple operations;
- `Shift copy`: creates a vertically shifted copy by the value in `Offset`;
- `Scale copy`: creates a copy multiplied by `Scale`;
- `Average selected`: averages selected spectra point by point;
- `Max selected` and `Min selected`: calculate maximum and minimum envelopes;
- `Delete selected`: deletes selected copies, never the main spectrum.

### 6.5 Clear Graph and session memory

`Edit > Spectrum Management > Clear Graph` removes spectra, fits, markers and results from the current measurement. The persistent main line library remains available and is restored. Ne is cleared unless `Keep active Ne after Clear Graph` was explicitly enabled for a homogeneous series.

## 7. Dark signal, background and instrumental response

### 7.1 Correction order

For each window, the workflow is:

1. select the signal column;
2. subtract the configured dark signal or background;
3. divide by the radiometric response of that window;
4. calibrate the wavelength axis;
5. merge with the other windows.

### 7.2 Loading the radiometric response

1. Open `Utilities > Instrument Calibration > Instrument Response...`.
2. Press `1. Load response files...`.
3. Select all curves measured with tungsten/deuterium together.
4. In the `Matched window(s)` table, verify that each curve is associated with the correct window.
5. Press `2. Apply signal / response`.
6. Check the graph and status message.

The curves must represent spectral sensitivity to be divided out. They are not line-broadening profiles.

### 7.3 Response boundaries

The program removes unreliable curve edges and does not artificially extrapolate the response outside its range. It reports any window for which no compatible curve is available. The only intentional exception is the dedicated H-alpha loader for Ne, which can ignore the radiometric response because it primarily uses the line width.

### 7.4 Global instrumental width

`Global width @ 656 nm...` stores an independently determined instrumental FWHM. Palleschi's original H-alpha method uses it to correct the measured Lorentzian width:

`FWHM_L,corr = max(FWHM_L,fit - FWHM_instrument^2 / FWHM_L,fit, 0)`

The same value remains available as a global approximation for theoretical-spectrum synthesis. Do not enter the total H-alpha FWHM dominated by Stark broadening. If the instrumental width is unknown, use 0.

## 8. Wavelength calibration

Open `Utilities > Instrument Calibration > Wavelength Calibration...` before automatic identification.

### 8.1 Preparing reference lines

Use reliable NIST wavelengths that are present in the sample. You can:

- press `Load NIST line list...` and load a file;
- paste a series of values into `or paste wavelengths` and press `Add`;
- use NIST lines already present in the selected-line list.

Values with a decimal point or comma are accepted. A list may include element and ionization-state headers.

### 8.2 Estimating calibration

1. Set `Maximum initial shift`, for example 0.8 nm when the expected shift is smaller.
2. Select `Model = auto`.
3. Press `Estimate from selected NIST lines`.
4. For each window, check the number of lines, Delta lambda at center, scale `b`, RMS and `Quality`.
5. If reliable Voigt centers are already available, use `Use identified Voigt fits`.

With one or two lines, the automatic model applies only an offset. A linear scale `lambda_corrected = a + b * lambda_raw` requires at least three coherent lines spanning at least 5 nm.

### 8.3 Excluding an incorrect reference

Select a window in the upper table. In the lower table, select the suspect line and press `Include / exclude selected line`, or double-click it. Repeat the estimate and confirm that RMS and residuals improve for physical, not merely numerical, reasons.

### 8.4 Applying and remembering

- `Apply to loaded spectra`: applies calibration only to the current data.
- `Apply and remember`: applies and stores the profiles for later measurements with compatible windows.
- `Clear saved calibration`: deletes persistent profiles.

Per-window calibration is preferable to a global shift when the displacement varies among detectors.

### 8.5 Manual shift and other axis operations

`Utilities > Instrument Calibration > Manual Wavelength Shift...` provides a controlled correction when one known line is available. Enter the observed position in `Move Point at` and the reference position in `to`. The program applies `shift = reference - observed`.

1. Press `Pick` and click the observed point, then the destination position, or enter both values.
2. Enable `Shift all spectra` only when the same offset is valid for every displayed spectrum.
3. Enable `Shift Identifications` only when markers, assigned lines and fit centers must also follow the displacement.
4. Press `OK`, check a second independent line and save a per-window profile whenever possible.

`Utilities > Signal Processing > Intensity Offset...` applies the vertical displacement `desired value - current value` to the main spectrum. This is not a physical dark subtraction and must not be used to conceal an incorrect background.

`Utilities > Signal Processing > Smooth Spectrum` changes the Y values of the main spectrum: it uses a Savitzky-Golay filter with window 11 and order 4 when SciPy is available, otherwise a moving average. Smoothing can alter height and width; normally start quantitative area measurements from unsmoothed data.

`Utilities > Signal Processing > Convert nm to Å` multiplies the axis by 10. Use it once only, and only when the current axis is actually in nanometers. `Go To Wavelength...` changes only the graph view.

## 9. Main analytical-line library and selected lines

Open `Utilities > Analytical Line Lists > Main Analytical-Line Library...` or press `Selected Lines`.

### 9.1 Contents of the main library

The persistent main library contains candidate analytical lines, normally with NIST wavelengths and atomic metadata. The open table is the workspace for the current measurement: in addition to assignments, it may contain observed Voigt centers, widths and areas.

### 9.2 Main commands

- `Import lines...`: imports a list for the current analysis.
- `Save lines`: saves the current lines.
- `Clear fit`: deletes Voigt results but retains the lines.
- `Delete row`: deletes the selected row.
- `Saha-Boltzmann`: opens temperature analysis directly.
- `More > Line summary`: displays a summary.
- `More > Clear selected lines`: clears the current workspace.
- `More > Close line list`: closes the active list according to the historical workflow.
- `More > Delete saved list`: deletes the selected saved list.

### 9.3 Managing the persistent library

The `Manage library` menu contains:

- `Reload main library`: reloads the main library from disk;
- `Add secondary list...`: merges an additional list while avoiding duplicates;
- `Replace main library...`: replaces the main library;
- `Save current lines as main`: makes the current lines persistent after removing fit results and measurement-specific intensities;
- `Restore included library`: restores the list distributed with the program.

The main library does not automatically authorize all its elements for quantification. The set of analyzed elements is explicitly defined by `Trace Lines` in the current session.

## 10. Peak detection and identification

### 10.1 Find Peaks

`Analyse > Peak and Line Detection > Find Peaks` locates local maxima in the visible spectrum. It builds a set of observed candidates; by itself, it does not assign an element or ionization state.

### 10.2 Trace Lines: correct procedure

1. If necessary, zoom into the interval to be analyzed.
2. Open `Analyse > Peak and Line Detection > Trace Lines...`.
3. Enter the symbol in `Trace Species`, for example `Cu`, `Sn` or `Pb`.
4. Select `I`, `II`, `Both` or `All`.
5. Keep `Only near selected peaks` enabled so that only transitions near previously selected observed maxima are accepted.
6. Set `Tolerance` in the displayed unit.
7. Press `OK` and inspect the table.
8. Press `Assign` only when the lines are consistent.
9. Repeat for every element that is actually required.

`Max Lines (all mode)` limits the number of lines while exploring `All`. Disable `Only near selected peaks` only to inspect the database: expected transitions without a measured maximum must not become analytical areas.

### 10.3 Removing an incorrect element

If an element was traced by mistake, select one of its lines in the table and press `Delete`, or use `Remove element (Del)`. The markers and assignments for that element are removed without destroying the Voigt fits of other elements.

### 10.4 Identifications

The identification window supports a targeted search:

1. enable the database with `Use LIBS.db` or load an atomic CSV;
2. select `Datalibs` or `Daticerti`;
3. enter lambda and `range`;
4. press `Search`;
5. double-click the correct transition to assign it to the nearest selected peak.

Always check `Aki`, energies `Ei/Ek`, statistical weights `gi/gk` and ionization state. Wavelength proximity alone does not establish an identification.

### 10.5 Auto Element Identification

This function ranks candidate elements using spectral matches and database intensities. It is an exploratory tool, not a replacement for `Trace Lines`, fitting and scientific review. Do not automatically use the first results for unknown-sample quantification without verification.

## 11. Automatic and manual Voigt fitting

### 11.1 Auto Fit

1. Set the graph to the useful range or use the complete view.
2. Open `Analyse > Spectral Fitting > Automatic Fit...`.
3. Press `1. Find visible peaks` to select measured maxima.
4. If an evident peak is missing, press `Add peak from graph` and click the maximum.
5. Normally let Auto Fit locate the baseline returns in the current sample. Use `Select ROI limits` only to correct a problematic region manually, clicking its left and right boundaries on the graph.
6. Press `2. Fit selected peaks (Voigt)`.
7. Check the results table and overlaid profile.

Automatic search must not place a point merely because the database predicts a line. If no compatible local maximum exists, the line is not an observed peak.

### 11.2 ROI and baseline

- `Select ROI limits`: manually sets both boundaries.
- `Save current zoom`: uses the current X limits as the ROI.
- `Reset ROI`: removes the stored ROI for the region.

The ROI must contain sufficient baseline on both sides, but not distant regions dominated by other peaks or background curvature. Auto Fit derives it again from the current spectrum; a manual ROI applies only to the session that created it because peak shift and shape can change between samples. The default quantitative result uses the local linear baseline. With `Adaptive baseline-to-baseline limits`, the reported limits may contract to the profile feet; the Voigt fit is still defined over the region used by the optimizer.

Baseline selection does not change the quantitative area definition: every component is a normalized Voigt and its amplitude parameter is its complete integral. The limits displayed in the graph diagnose the return to baseline; they do not truncate the area used by Boltzmann and CF-LIBS.

### 11.3 Double or multiple peaks

When multiple lines fall within the same region, add all of them before fitting. The model is the sum of Voigt components and a baseline. Verify that:

- centers remain close to the maxima or assigned transitions;
- no component artificially fills the entire ROI;
- residuals do not retain a second structured maximum;
- the selected line's area is not assigned to the wrong neighbor.

Only explicitly selected lines enter the quantitative result. The program does not automatically add unassigned Voigt components: a structured residual maximum means that the region must be checked and, when physically justified, the interfering line must be selected explicitly before repeating the multiple fit.

### 11.4 Manual Fit

`Analyse > Spectral Fitting > Manual Fit...` allows the center, Gaussian component and Lorentzian component to be changed and individual parameters to be fixed. Use it for problematic regions, not to force a desired result.

- `Fit`: fits the current region.
- `Next Region` and `Previous Region`: move through the regions in the line list.
- `Refresh`: rereads the current data.
- `Show Residuals`: opens the fit residuals.
- `Fix` beside a parameter: prevents the optimizer from changing it.

Random residuals around zero are preferable. Structure, residual peaks or curvature indicate missing components, an unsuitable baseline or an incorrect ROI.

### 11.5 Original Gaussian fit

`Analyse > Spectral Fitting > Manual Fit...` opens the historical panel with both choices. `Fit Gaussian` uses a sum of Gaussian profiles and a linear baseline:

`G(lambda) = H exp[-((lambda-lambda0)/sigma)^2]`

and stores the area `A = H sigma sqrt(pi)` for each line. This is an explicit alternative: `Auto Fit` and `Manual Fit` continue to use the normalized Voigt model. Do not mix Gaussian and Voigt areas in the same Boltzmann plot.

### 11.6 Fit table

For every line, inspect:

- `Fit Center Wavelength`;
- `Fit Intensity` and `Fit Integral`;
- `Fit Lorentzian Width` and `Fit Gaussian Width`;
- `Replicate area CV`;
- `Quality`.

`Mean only` indicates that not enough individual replicates are available to estimate dispersion. In the `Auto Fit` and `Manual Fit` workflows, the quantitative area is the Voigt integral fitted on the mean spectrum. Replicate CV measures repeatability: when it exceeds the configured threshold a warning is shown, but the line remains in the Boltzmann plot if the mean-spectrum fit is valid. Only a genuinely invalid Voigt fit is marked `ERROR` and excluded from quantification.

## 12. Electron density from H-alpha

H-alpha is used for electron density through Stark broadening. The 656 nm file can be loaded without a radiometric-response curve exclusively within this procedure.

### 12.1 Procedure

1. Open `Analyse > Plasma Diagnostics > Electron Density from Hα...`.
2. Check that `wl1` corresponds to 6562.8 A when the interface uses Angstrom, or to the value consistent with the current unit.
3. Press `Load H-alpha spectrum (no radiometric response)`.
4. Confirm on the graph that the selected maximum is genuinely H-alpha.
5. If the spectrum is shifted by 0.3-0.4 nm, first apply the stored calibration or confirm the observed displacement when prompted.
6. Run `Fit Hα and estimate Ne`, the only available method and the one corresponding to Palleschi's original workflow.
7. Read Ne, fit quality, SNR and uncertainty.

### 12.2 Width used for Ne

Palleschi's method fits one or two Lorentzian components. The FWHM of the primary H-alpha component is corrected with the configured instrumental width and then used in the Stark relation for Ne. Radiometric response is not required for width alone, but the dark signal, background and wavelength axis must be correct.

### 12.3 Ne used by the program

The session holds an active Ne value with an explicit source. Saha-Boltzmann and CF-LIBS use the current Ne, not an arbitrary value. `Clear Graph` clears it by default; retaining it is correct only for a homogeneous experimental series.

> Recalculate Ne whenever laser power, delay, gate, geometry, matrix or plasma conditions change.

## 13. Saha-Boltzmann temperature

### 13.1 Prerequisites

Before opening the graph, the following are required:

- elements admitted with `Trace Lines`;
- assigned lines with the correct ionization state;
- complete atomic data;
- valid Voigt areas;
- an active Ne value;
- a consistent radiometric response.

### 13.2 Calculation

1. Open `Analyse > Plasma Diagnostics > Saha-Boltzmann Plot...`.
2. Leave `Initial kT (eV) = 1` unless better information is available.
3. Select the `Temperature` mode.
4. Press `Compute Plot`.

The radiometric ordinate exclusively uses the assigned NIST wavelength (`asswavelen`, falling back to the preselected NIST wavelength). The observed Voigt center (`fitwavelen`) is used only to locate and validate the peak. When instrumental response is applied after fitting, its factor is also evaluated at the NIST wavelength.

Available modes:

- `Most reliable element`: selects the thermometric species best supported by the data;
- `Single element temperature`: uses the element selected in the table;
- `Mean temperature`: combines accepted temperatures.

### 13.3 Thermometric-species criterion

The criterion favors a broad energy distribution with at least the minimum number of lines and levels, good R2 and leave-one-out stability. For equal quality, a larger `dEk eV` provides more information on the slope. A species with only a few points at nearly the same Ek is not a good thermometer even when its R2 is high.

### 13.4 Meaning of the columns

- `Use / role`: Fit, Reference, No or a diagnostic role.
- `lines`: usable lines.
- `levels`: distinct upper energy levels.
- `dEk eV`: interval between minimum and maximum Ek.
- `kT eV`: electron temperature expressed as energy.
- `R2`: coefficient of determination of the fit.
- `LOO dT/T`: maximum variation when removing one line at a time.
- `q`, `Z I`, `Z II`: Saha parameters and partition functions.

Double-click or press Space on a row to include or exclude an element where supported. `Check Lines` explains why each line was used or rejected.

### 13.5 Before and after IRSAC

Before correction, species can have different slopes and the program displays them diagnostically. After the common temperature has been chosen, CF-LIBS imposes the slope `-1/kT` on the other species and refits only their intercepts. Do not interpret parallel post-correction lines as independent temperature measurements.

### 13.6 Conversion

The relationship is:

`T(K) = kT(eV) * 11604.518`

A variation of 0.02 eV corresponds to approximately 232 K.

## 14. Self-absorption and IRSAC

Self-absorption must not be corrected automatically for every sample. Evidence is assessed first; correction is selected only afterwards.

### 14.1 Modes

- `Combined Stark-width and IRSAC correction`: combines the Stark-linewidth check with IRSAC for supported lines.
- `Stark-linewidth correction`: uses only the correction based on predicted and observed Stark width.
- `IRSAC internal-reference correction`: applies IRSAC to internal references for each species; the thermometric species determines the frozen corrected temperature used by subsequent corrections.

The Stark-linewidth correction requires a line-specific match in `Stark.db`. The absence of that line does not prove the absence of self-absorption; it means that this check is unavailable for that transition.

### 14.2 Diagnosis before correction

Open `Check SA` from Saha-Boltzmann or `Analyse > Plasma Diagnostics > Self-Absorption / IRSAC...`. Check:

- consistency of lines sharing the same upper level;
- behavior of the ordinate as a function of Ek;
- observed width and available Stark width;
- fit quality and interferences;
- physically plausible correction factors;
- the result `No significant evidence`, `Self-absorption compatible`, `Not assessable` or `Correction unsafe`.

`Not assessable` does not mean `no self-absorption`. It means the data do not support a sound decision.

### 14.3 Initial-temperature fallback

`Initial-T fallback` can be:

- `Auto (from Saha)`: reuses the reference selected by Saha-Boltzmann only when a fallback initial T is needed;
- an explicit species, such as `Cd I`, `Sn I` or `Pb I`.

The selected thermometric species supplies both the raw T and the corrected T that is then frozen during IRSAC. `Auto (from Saha)` reuses the Saha-Boltzmann reference species; an explicit choice such as `Cd I` remains fixed. Prefer a species with a broad Ek interval, at least three independent upper levels and a stable fit. Other species cannot move the IRSAC temperature.

### 14.4 IRSAC reference line

One line acts as the internal reference for every neutral or ionic species. `Automatic line references` applies Yang Eq. (7): it rejects Aki uncertainties above 50%, keeps candidates with the best reported accuracy, and gives weight 0.5 to ascending Ei rank and 0.5 to descending Aki rank. To force a line, select it in the table and press `Use selected line as IRSAC reference`. A manual selection must be documented and makes quantitative checks stricter.

### 14.5 IRSAC with a frozen thermometric temperature

The quantitative mode is `Staged Aslam IRSAC (internal references)`. It preserves the measured integrated areas and applies this sequence once:

1. obtains the raw temperature from the thermometric species alone, `y = ln(lambda_NIST I / Aki gk)`; the fallback value is used only when that fit is unavailable;
2. selects one internal reference for each species with Eq. (7), or uses a manually selected reference;
3. at the raw T it calculates, for every line of the thermometric species, `f_k = I_k (A_ref g_ref)/(I_ref A_k g_k) exp[-(E_ref-E_k)/(0.69503476 T)]`;
4. corrects the area with `I_corr,k = I_k/f_k`; the reference has `f_ref=1` by construction;
5. refits only the corrected Boltzmann plot of the thermometric species and obtains the final IRSAC T;
6. freezes this T and evaluates every other species with the same equation and its own internal reference;
7. never updates T from the other species and never forces their independent free slopes to be parallel;
8. in final CF-LIBS it imposes the physical common slope `m=-1/(kB T_IRSAC)` and fits only `q = mean(y_corr - m E)` for each species.

The assigned NIST wavelength is used in the Boltzmann ordinate and instrumental-response lookup, but is not inserted a second time into Eq. (6). The observed center remains a fit result and does not replace the transition wavelength. A relative multiplier `1/f_k` below 1 is allowed: it is a normalization to the chosen internal reference, not an absolute optical-depth measurement.

Comparison with an external worksheet requires the same integrated areas, instrumental response, NIST wavelength, Aki, gk, Ek, references and thermometric species.

### 14.6 Recalculation

- `Recalculate IRSAC`: reuses the measured areas and recalculates only the correction. IRSAC never refits the spectrum or changes its areas.
- If the baseline or ROI changes, repeat the fit explicitly in the fitting window before recalculating IRSAC.
- `Apply correction`: activates accepted factors.
- `Remove correction`: returns to uncorrected areas.

The window reports raw T, final IRSAC T, thermometric species, references, relative factors and diagnostic checks. If the corrected thermometric temperature cannot be calculated, the factors cannot be applied. Quality checks remain visible but never silently alter the equation or fitted areas.

### 14.7 When correction must not be used

Do not apply IRSAC when:

- the diagnosis shows no significant evidence;
- lines are interfered or the fit is unstable;
- the reference was forced without independent support;
- factors are nonphysical or marked unsafe;
- the correction worsens agreement among lines of the same element;
- the result depends almost entirely on one line.

A correction may be displayed for diagnosis but blocked from producing percentages.

### 14.8 Historical SAC window

`Analyse > Plasma Diagnostics > SAC Factors...` calculates diagnostic factors using `kT`, `Ne`, optical path `path lu` and total density `N total`. When a CF-LIBS result exists, it uses its `Number %`; otherwise it assigns equal percentages to the elements present. The table reports `SAC`, widths and the line-center coefficient.

This window does not replace `Self-Absorption / IRSAC` and does not by itself measure concentration or optical path. Use it only as a specialist tool when `lu` and `N total` are experimentally justified.

## 15. CF-LIBS concentrations

### 15.1 Prerequisites

CF-LIBS requires a valid common temperature, an explicit Ne value, corrected Voigt areas, partition functions and the set of elements defined by `Trace Lines`.

### 15.2 Procedure

1. Open `Analyse > Quantitative Analysis > CF-LIBS...`.
2. Press `Use current T / Ne` if the window was already open before the most recent calculation.
3. Check `kT eV`, `Ne cm^-3` and the source reported in the status line.
4. Leave `Intercepts` in the common-temperature quantitative mode.
5. Press `Compute CF-LIBS`.
6. Check the table, then `Robustness` and `Show Report`.

Free-slope mode is diagnostic only and does not produce quantitative percentages. With a common temperature, the program fixes the slope at `-1/kT` and estimates one intercept for each element.

### 15.3 Ionization

The ionized-to-neutral ratio is not taken as a manual NIST percentage. It is calculated automatically with Saha-Eggert using T, Ne, ionization energy and partition functions. The neutral fraction is:

`f_neutral = 1 / (1 + N_II/N_I)`

The total element population therefore combines the observed stages according to this ratio.

### 15.4 Number % and Mass %

`Number %` is the atomic or molar fraction:

`x_i = N_i / sum(N_j) * 100`

`Mass %` is calculated from atomic weights:

`w_i = N_i * M_i / sum(N_j * M_j) * 100`

Do not multiply or divide by atomic weight again after reading `Mass %`. Compare nominal molar percentages with `Number %`, and nominal mass percentages with `Mass %`.

### 15.5 Robustness columns

- `q spread factor` and `Line check`: consistency of populations obtained from individual lines;
- `LOO max %`: maximum variation when removing one line;
- `Replicate CV %`: dispersion among compositions calculated from replicates;
- `T/Ne max %`: sensitivity to temperature and electron-density uncertainties.

These checks are essential for samples containing three or more elements: closure to 100% can conceal an overestimated element that compresses all the others.

### 15.6 Line audit

`Show Report` lists the lines that were used or excluded and states the reason. Check that:

- only the requested elements appear;
- no line outside the acquired windows appears;
- the ionization state and metadata are correct;
- no result depends on lines with an `ERROR` fit;
- Aki satisfies the threshold.

### 15.7 Repository OPC

The `OPC` button in the CF-LIBS window performs One Point Calibration with a known standard. As in Palleschi's official repository, the OPC calculation compares the standard and the CF-LIBS result on the same `Number %` basis (atomic or molar percentage). The window can nevertheless accept the certified nominal composition directly as `Mass %`: pyLIBS converts it internally to `Number %` using the database atomic masses, without changing the OPC equation. The `.opc` file is the correction curve produced by the procedure. `.STD` files belong to the separate `Standard Correction` feature and must not be loaded in the OPC window.

1. Select `Apply After` and load the physical instrumental response. Loading the file no longer changes the selected mode. If the spectrum had already been corrected with `Apply Before`, pyLIBS automatically restores its raw source data and clears the previous fit measurements, which must be repeated.
2. Fit the standard lines once and complete CF-LIBS without applying SAC/IRSAC to OPC.
3. Open `OPC`, select `Nominal composition: Mass %` or `Number %`, and enter the nominal composition in the selected basis. For example, a Cd/Ni/Pb standard containing `29.72 / 15.51 / 54.77 Mass %` is converted to approximately `33.34 / 33.32 / 33.33 Number %`.
4. Press `Compute OPC`: for mass input pyLIBS evaluates `x_i=(w_i/M_i)/sum(w/M)`, then always uses the OPC ratio `nominal Number % / CF-LIBS Number %`.
5. Press `Save Calibration...`. The `.opc` file contains a traceability header and, for each line, the NIST wavelength, composite factor, element, and species.
6. For the unknown, start from the raw spectrum and fit it once. Do not apply the physical instrumental response beforehand.
7. Open `Calibration > Instrument Response`, select `Load response files...`, and select only the `.opc` file. pyLIBS automatically selects `Apply After`.
8. Recalculate Saha-Boltzmann and CF-LIBS. OPC divides the integrated areas; the spectrum, profiles, and fitted areas are not modified.

With `Apply After`, the exported file contains `physical instrumental response × residual OPC correction`. The `.opc` therefore replaces the physical curves and must not be loaded together with them. OPC is a sparse calibration on analytical lines: it must not be applied point by point to the spectrum. The program blocks `Apply Before`, mixed `.opc` and physical-response selections, and OPC generation from areas already corrected before fitting. Self-absorption remains separate.

OPC is not autonomous for completely unknown samples and must not be used to force an unknown alloy toward an expected composition.

### 15.8 Standard Correction (`.STD`)

`Analyse > Quantitative Analysis > Standard Correction...` corresponds to the repository's `Unit31` window and uses `.STD` files with the current `Mass %`. `Refresh from CF-LIBS` reloads the table; double-click an element to enter its certified mass percentage. `Apply correction` uses the factor `reference Mass % / measured Mass %` and renormalizes the table to 100%. `Save .STD` and `Load .STD` store or recall reference percentages.

`Standard Correction` only corrects the current table in `Mass %`. `OPC` is a distinct procedure: it internally uses nominal `Number %` values to generate a curve that can be applied, after integration, to other spectra acquired under the same conditions. The OPC window's `Mass %` selector is only an assisted input with automatic conversion. Both require a known standard and are not part of uncalibrated CF-LIBS.

## 16. Theoretical spectrum

`Analyse > Quantitative Analysis > Theoretical Spectrum...` generates a diagnostic comparison after the self-absorption decision.

1. Complete Saha-Boltzmann and the SA assessment.
2. Open the theoretical-spectrum window.
3. Check the read-only analysis temperature.
4. Set `Aki min`.
5. Select the domain: `Auto`, `Response-corrected` or `Detector counts`.
6. Enter the global instrumental FWHM measured near H-alpha, or 0 when unknown.
7. Press `Calculate diagnostic spectrum`.

`Display-only least-squares scale` rescales the model for visual comparison and does not change CF-LIBS. In the detector domain, instrumental response is applied to the model in the forward direction; in the corrected domain, radiometric intensities are compared.

The theoretical spectrum is a downstream check. It does not replace IRSAC and does not by itself provide a quantitative self-absorption correction.

## 17. Reports, saving and batch operations

### 17.1 Saving the graph and data

- `File > Save`: saves the main spectrum as two X/Y columns.
- `File > Save with Labels`: saves a CSV with `wavelength`, `intensity` and `label` columns; the label is assigned to the nearest X sample.
- `File > Print`: exports the graph as PNG or PDF.
- `Edit > Copy`: in the current version, instructs the user to use `File > Print`; it does not copy the graph to the clipboard.

### 17.2 CF-LIBS report

`Show Report` generates an HTML/text report containing spectrum metadata, response, lines, fits, H-alpha, Saha-Boltzmann, plasma parameters, self-absorption, robustness and concentrations. Store the report with the raw data and experimental configuration.

### 17.3 Batch Operations

Open `Utilities > Batch and Statistics > Batch Operations...`.

- `Add Files`: loads a file list; all files, odd files or even files can be selected.
- `MultiFit`: applies the current line list to the files and saves an Excel workbook.
- `Join`: joins files in pairs and creates `.jnd` files.
- `Average`: interpolates onto a common grid, calculates the average and creates `.avg` files.
- `Calculate SD`: adds the standard deviation in an `.sd` file.
- `Load List` and `Save List`: manage `.lst` or historical `.fls` lists.

Averaging acquisitions is valid only when the files belong to the same window and were acquired under equivalent experimental conditions. Do not average different central windows together.

### 17.4 Minimum measurement archive

For a reproducible analysis, store together:

- raw files for all replicates and windows;
- the dark file or a description of the dark columns;
- radiometric-response curves and their measurement date;
- wavelength-calibration profiles;
- the analytical-line list and atomic-database version;
- any averaged file, without deleting the replicates;
- the CF-LIBS report, T, Ne, SA decision and options used;
- sample identifier, laser energy, delay, gate, number of shots and date.

## 18. Quality control and repeatability

### 18.1 Checklist before accepting a result

1. All required windows were loaded together.
2. The dark signal and radiometric response are correct for every window.
3. Wavelength calibration has acceptable residuals in each window.
4. The elements in the graphs are exactly those requested in Trace Lines.
5. Every analytical line coincides with an observed maximum.
6. Voigt fits reach the baseline and separate double peaks.
7. Replicates have an acceptable CV.
8. Ne comes from the relevant H-alpha measurement.
9. The thermometric species has a broad Delta Ek and stable leave-one-out behavior.
10. The SA decision is supported by the data.
11. CF-LIBS passes the quality gate and robustness audit.
12. Number % or Mass % is compared with the correct nominal quantity.

### 18.2 Multielement samples

For more than two elements, pay particular attention to closure of the selected element set, unobserved lines, dominant unmeasured ionization stages and sensitivity to removing one line. One overestimated element changes every normalized percentage.

### 18.3 Comparing laser powers

Do not automatically reuse T and Ne at different laser powers. Ionization, Stark broadening, self-absorption and the signal-to-background ratio change. Repeat Ne, Saha-Boltzmann and SA diagnosis for each condition.

### 18.4 Unknown sample, standard and series

For a completely unknown sample, use the CF-LIBS workflow without OPC or Standard Correction. For a certified standard, first run the same uncalibrated workflow, then assess OPC or Standard Correction separately. Within a series of the same sample acquired under identical conditions, the line list, response and per-window calibration can be reused; Ne can be retained only by explicit choice and must still be checked whenever the plasma changes.

<!-- pagebreak -->

## 19. Troubleshooting

| Problem | Probable cause | Action |
|---|---|---|
| A line appears where no window was acquired | unfiltered library/markers or stale session | use Clear Graph, reload the windows and inspect the report; the line must not enter calculations |
| An unrequested element appears | element traced previously or a residual assignment | in Trace Lines, select the element and press Delete; then recalculate |
| An evident peak is not selected | threshold, zoom or incomplete observed-peak list | zoom into the region, use Auto Fit > Add peak from graph, then Trace Lines |
| A line without a peak is selected | `Only near selected peaks` is disabled | enable it again and delete the assignment |
| The program appears to freeze during fitting | ROI too broad, too many parameters or insufficient information | press Stop, narrow the ROI, check components and retry |
| R2 = 1 with two points | one straight line always passes through two points | do not treat this as evidence of a good temperature; more lines and levels are required |
| Lines are parallel in CF-LIBS | common slope imposed by T | expected after selecting a common temperature |
| Lines are parallel before IRSAC | quantitative view instead of diagnostic view, or stale state | recalculate Saha-Boltzmann and check the mode/role |
| No Ne is available | Hα was not calculated or Ne was cleared | repeat `Plasma Diagnostics > Electron Density from Hα...`, or retain Ne only for the same series |
| No response exists at 656 nm | H-alpha radiometric curve is missing | use the dedicated H-alpha loader; the exception applies only to Ne |
| Temperature changes greatly after refitting | areas or ROIs changed | compare centers, baseline, areas and lines used in the report |
| IRSAC changes percentages excessively | unstable factors, unsuitable reference or lack of evidence | remove the correction, read the diagnosis and check that the worksheet uses the same equation |
| Excel and pyLIBS differ | different areas, lambda, Aki, gk, equation or neutral fraction | export the report and compare the inputs line by line |
| Molar percentages do not match Mass % | different composition bases are being compared | use Number % for moles and Mass % for mass |
| CF-LIBS blocks the percentage | the quality gate was not passed | open Robustness and Show Report; correct the data, not the threshold |
| Clear Graph loses Ne | default safety behavior | enable Keep active Ne only for the same experimental series |

## 20. Complete menu and field reference

### 20.1 File

| Command | Shortcut | Function |
|---|---|---|
| Open... | Ctrl+O | opens the main spectrum |
| Compare... | Ctrl+M | adds a comparison spectrum |
| Append... | Ctrl+A | loads multiple windows/spectra |
| Save | Ctrl+S | saves the spectrum |
| Save with Labels | Ctrl+L | exports a labeled CSV |
| Print | Ctrl+P | exports the graph as PNG or PDF |
| Exit | Ctrl+X | closes the program |

### 20.2 Edit

| Command | Shortcut | Function |
|---|---|---|
| Copy | Ctrl+C | instructs the user to export with File > Print; clipboard output is unavailable |
| Spectrum Management > Swap Spectra | Ctrl+W | exchanges comparison spectra |
| Spectrum Management > Show Active Spectra | Ctrl+Shift+A | manages loaded spectra |
| Spectrum Management > Clear Graph | Ctrl+Del | clears the current measurement |
| Options... | Ctrl+Alt+O | opens configuration |
| Restore Factory Settings... | - | restores the distributed configuration |

### 20.3 View

| Command | Shortcut | Function |
|---|---|---|
| Appearance > Background Color... | Ctrl+B | changes the graph background |
| Appearance > X-axis Grid / Y-axis Grid | Ctrl+Alt+X / Y | toggles the axis grids |
| Appearance > Logarithmic X Axis / Y Axis | Ctrl+Alt+G / L | toggles logarithmic scales |
| Zoom and Scale > Fit X Axis / Fit Y Axis | - | fits one axis to the data |
| Zoom and Scale > Expand X by 50% | F2 | expands the X view by 50% |
| Zoom and Scale > Full Y Scale | F3 | fits the Y axis |
| Zoom and Scale > Show Full Spectrum | F4 | restores the complete view |
| Window Layout > Save Window Positions | - | saves window positions |
| Window Layout > Restore Window Positions | - | restores saved positions |

### 20.4 Utilities

| Command | Shortcut | Function |
|---|---|---|
| Instrument Calibration > Instrument Response... | Ctrl+Alt+R | loads and checks response curves |
| Instrument Calibration > Apply Instrument Response | - | applies the signal-to-response ratio |
| Instrument Calibration > Wavelength Calibration... | - | calibrates each window |
| Instrument Calibration > Manual Wavelength Shift... | Ctrl+F1 | applies a selected shift |
| Signal Processing > Intensity Offset... | Ctrl+F2 | changes the vertical level |
| Signal Processing > Smooth Spectrum | Ctrl+F3 | smooths the displayed spectrum |
| Signal Processing > Convert nm to Å | Ctrl+F4 | converts nanometers to angstroms |
| Batch and Statistics > Batch Operations... | - | performs batch processing, averaging, joining and MultiFit |
| Analytical Line Lists > Import Lines for Current Analysis... | Ctrl+F5 | imports the current list |
| Analytical Line Lists > Main Analytical-Line Library... | Ctrl+F6 | manages the main library and working lines |
| Analytical Line Lists > Selected-Line Summary | Ctrl+F7 | summarizes selected lines |
| Analytical Line Lists > Clear Selected Lines | - | clears current lines |
| Batch and Statistics > Statistics | Shift+Ctrl+F4 | displays X/Y statistics |
| Go To Wavelength... | Ctrl+F9 | centers a wavelength |

### 20.5 Analyse

| Command | Function |
|---|---|
| Peak and Line Detection > Find Peaks | finds observed maxima |
| Peak and Line Detection > Trace Lines... | identifies requested elements |
| Spectral Fitting > Manual Fit... | performs controlled manual Voigt fitting |
| Spectral Fitting > Automatic Fit... | performs automatic peak selection and Voigt fitting |
| Plasma Diagnostics > Electron Density from Hα... | calculates electron density |
| Plasma Diagnostics > Saha-Boltzmann Plot... | calculates temperature and ionization stages |
| Plasma Diagnostics > Self-Absorption / IRSAC... | diagnoses and corrects self-absorption |
| Plasma Diagnostics > SAC Factors... | opens the historical SAC-factor window |
| Quantitative Analysis > CF-LIBS... | calculates concentrations and robustness |
| Quantitative Analysis > Theoretical Spectrum... | provides a diagnostic theoretical comparison |
| Quantitative Analysis > Standard Correction... | applies an external-standard correction |

`SAC Factors` and `Standard Correction` are specialist or historical tools. In the ordinary workflow, use `Self-Absorption / IRSAC`; apply standard correction only when an appropriate documented standard exists.

### 20.6 Help

| Command | Shortcut | Function |
|---|---|---|
| User Manual > Italiano / English | - | selects and opens the manual in the chosen language |
| About pyLIBS... | Ctrl+T | displays version, credits and program information |

## 21. Equations and glossary

### 21.1 Boltzmann ordinate and intensity convention

For an energy-domain response, the program uses:

`y = ln[(1e-9/(h*c)) * I_corr * lambda_NIST,nm / |Aki * gk|]`

The constant `1e-9/(h*c) = 5.0341166e15 J^-1 nm^-1` and `lambda_NIST,nm` convert radiant energy into the equivalent photon number. For a response already expressed in photons or corrected counts, the program instead uses the original pyLIBS convention:

`y = ln[I_corr / |Aki * gk|]`

In both equations, `I_corr` is the Voigt area corrected by the instrumental response, `Aki` is in s^-1 and `gk` is the statistical weight of the upper level. A multiplicative constant common to all lines shifts the plot vertically without changing its slope; the wavelength-dependent factor must instead be applied exactly once and consistently with the response domain.

The linear relationship is:

`y = intercept - Ek/kT`

therefore the slope is `m = -1/kT`.

### 21.2 Saha-Eggert

The ratio between ionized and neutral populations depends on T, Ne, ionization energy and partition functions. pyLIBS calculates it automatically for every element and uses it to reconstruct the total population.

### 21.3 Terms

| Term | Operational meaning |
|---|---|
| Aki | transition probability in s^-1 |
| Ei / Ek | lower / upper energy |
| gi / gk | lower / upper statistical weights |
| kT | electron temperature expressed in eV |
| Ne | electron density in cm^-3 |
| FWHM | full width at half maximum |
| Voigt | convolution of Gaussian and Lorentzian contributions |
| ROI | interval used for fitting and integration |
| IRSAC | iterative self-absorption correction |
| SA | self-absorption |
| LOO | leave-one-out recalculation after removing one line |
| CV | coefficient of variation |
| OPC | One-Point Calibration with a known standard |
