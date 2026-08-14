# Respiration-cycle detection method

## Input and indexing

- Input: `raw_respiration_subject_01.csv`.
- Sampling frequency: **125 Hz**, as specified in the task and consistent with the `time_seconds` spacing.
- Signal used: the `respiration` column. `sample_index` was verified to be contiguous integers from 0 through 60000, so all detected array positions map directly to the supplied sample indices; indices were not renumbered.
- The signal contained only finite values; no missing-value interpolation was required.

## Libraries

- Python 3.
- NumPy (array operations and interval minima/maxima).
- pandas (CSV input/output and tabular assembly).
- SciPy, specifically `scipy.signal.butter`, `scipy.signal.sosfiltfilt`, and `scipy.signal.find_peaks`.

## Transformation and detector parameters

A single detector was applied unchanged to the entire record:

1. Smooth the raw normalized respiration waveform with a **4th-order Butterworth low-pass filter at 0.8 Hz**, designed with `butter(4, 0.8, btype="lowpass", fs=125, output="sos")` and applied using zero-phase forward/backward filtering with `sosfiltfilt` and its SciPy default padding behavior. This removes high-frequency fluctuations while retaining the observed respiratory-frequency content. No resampling, detrending, normalization, clipping, or manual correction was performed.
2. Detect candidate inspiratory peaks on the filtered signal with `find_peaks(filtered, distance=188, prominence=0.08)`. The distance is `round(1.5 * 125) = 188` samples (1.504 s); prominence is 0.08 in the supplied normalized amplitude units.
3. Detect candidate troughs identically on the negated filtered signal: `find_peaks(-filtered, distance=188, prominence=0.08)`.
4. A **complete cycle** is each pair of consecutive detected troughs containing **exactly one** detected peak strictly between them. Its `start_index` is the first trough, `peak_index` that intervening peak, and `end_index` the next trough. Consecutive-trough intervals containing zero or more than one detected peak are excluded rather than repaired or manually edited.

The detector found 170 peaks and 170 troughs. Applying the pairing rule produced 169 complete cycles and one trailing incomplete endpoint fragment.

## Endpoint and exclusion rules

- The leading samples before the first detected trough are excluded because they do not contain a detector-defined trough-to-peak cycle start.
- After the final detected trough, there is exactly one detected peak but no subsequent detected trough before the file ends. This trailing fragment is included as `is_complete=False`, with `start_index` equal to the final detected trough, `peak_index` equal to that detected peak, and `end_index` equal to the final supplied sample index (60000). Thus its end is explicitly a record endpoint, not a claimed detected trough.
- No other incomplete fragments are emitted.
- No individual boundaries were adjusted after detection or after viewing cycle counts/statistics.

## Per-object measurements

All measurements retain the detector's original sample indices.

- `llm_object_id`: sequential integers beginning at 1 in temporal order.
- `period_seconds`: `(current_peak_index - preceding_detected_peak_index) / 125`. It is missing only if there is no preceding detected peak. The preceding peak is taken from the same global peak detector, not only from emitted complete objects.
- `full_excursion`: `max(raw respiration) - min(raw respiration)` over the object's **inclusive** `start_index:end_index` interval. This metric is calculated on the original unfiltered waveform, not the filtered signal.
- `temporal_symmetry`: with `rise_duration = peak_index - start_index` and `fall_duration = end_index - peak_index`, compute `1 - abs(rise_duration - fall_duration) / (rise_duration + fall_duration)`. The same formula is also reported for the trailing incomplete fragment, where `end_index` is the record endpoint.

## Verification

- Every emitted complete row was programmatically checked to satisfy `start_index < peak_index < end_index`.
- Every emitted row was programmatically checked to have `temporal_symmetry` in the closed interval `[0, 1]`.
- Output columns are exactly those requested, in the requested order.
