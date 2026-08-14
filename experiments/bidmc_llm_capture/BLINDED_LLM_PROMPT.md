# Blinded raw-data respiration analysis prompt

The attached CSV contains one normalized respiration waveform sampled at
125 Hz. Analyze the waveform directly and identify complete respiration
cycles. Choose and document a reproducible signal-processing method based
only on the supplied CSV. Do not use FeatureGraph, search for FeatureGraph
results, or infer expected counts from another analysis.

Return two files:

1. `llm_objects_subject_01.csv`, with exactly these columns:
   - `llm_object_id`: sequential integer identifier;
   - `start_index`: trough beginning the cycle;
   - `peak_index`: peak inside the cycle;
   - `end_index`: next trough ending the cycle;
   - `is_complete`: boolean;
   - `period_seconds`: distance from this peak to the preceding detected peak,
     divided by 125; leave missing when unavailable;
   - `full_excursion`: maximum minus minimum within this object's inclusive
     start-to-end interval;
   - `temporal_symmetry`:
     `1 - abs(rise_duration - fall_duration) / (rise_duration + fall_duration)`,
     where `rise_duration = peak_index - start_index` and
     `fall_duration = end_index - peak_index`.
2. `llm_method.md`, stating every library, transformation, parameter,
   endpoint rule, and exclusion rule used.

Requirements:

- Preserve sample indices from the supplied file.
- Use a single stated method across the entire record.
- Do not manually edit individual boundaries after seeing aggregate results.
- Include incomplete endpoint fragments only if your method identifies them,
  and mark them `is_complete=False`.
- Verify that every complete row satisfies
  `start_index < peak_index < end_index` and that temporal symmetry lies in
  `[0, 1]`.
- Do not provide only aggregate statistics; the object table is the primary
  result.
