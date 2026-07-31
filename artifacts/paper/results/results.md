## Results

### Exact recovery and structural diagnostics

FeatureGraph exactly recovered the 12 analytical oscillations in the clean-signal verification. All 12 detected objects matched the 12 ground-truth objects, giving precision, recall, and F1 of 1.00. Mean interval IoU was 1.00, and the mean absolute errors for start, peak, end, duration, amplitude, and temporal symmetry were all zero. This result verifies that, when the state construction preserves the generating signal's reversals, the alpha pipeline can carry those reversals through object identification and property calculation without introducing error.

The separate completeness diagnostic produced eight object identifiers in each of the two phase-offset sequences. In both sequences, six objects were classified as complete and two as partial. The repeated result across the two groups showed that the alpha completeness rule distinguished boundary-supported objects from edge constructions and did not join objects across sequence boundaries.

### Parameter selection and sensitivity

At the tuning noise level of 0.20, the highest FeatureGraph mean F1 was 0.889 for a smoothing window of 9 samples, a difference lag of 10 samples, and epsilon of 0.03. Across the 20 tuning replicates, this operating point had mean precision 0.862, mean recall 0.921, and a mean interval IoU of 0.787. The F1 standard deviation was 0.078, corresponding to a 95% half-width of 0.034.

Performance varied substantially across the FeatureGraph grid. The two adjacent epsilon settings at the selected smoothing window and lag produced mean F1 values of 0.879 for epsilon 0.01 and 0.877 for epsilon 0, whereas many short-lag or unsmoothed constructions fragmented the noisy signal into large numbers of candidate waves and achieved F1 near zero. The best three FeatureGraph settings all used a smoothing window of 9 and a difference lag of 10. Epsilon affected results within this local region, but smoothing and lag produced the larger separation across the grid.

The selected SciPy operating point used a minimum distance equal to 0.60 of the known period and prominence 0.10. Its mean tuning F1 was 0.998, with mean precision 1.00, mean recall 0.996, and mean interval IoU 0.925. The SciPy grid was also parameter sensitive: reducing the distance constraint admitted additional noise-induced extrema, and the lowest-ranked combination had a mean F1 of 0.251. Within the tested sinusoidal setting, however, the selected SciPy detector was substantially more robust than the selected alpha FeatureGraph construction at the tuning noise level.

### Detection robustness

Both methods detected all held-out objects at noise standard deviation 0, producing mean precision, recall, and F1 of 1.00. FeatureGraph also maintained F1 of 1.00 at noise levels 0.05 and 0.10. The SciPy baseline had mean F1 of 0.981 at 0.05 and 0.997 at 0.10; these small departures from monotonicity reflect variation across finite noise realizations rather than a systematic improvement with added noise.

Above noise standard deviation 0.10, the two methods diverged. At 0.20, FeatureGraph mean F1 declined to 0.882, with precision 0.850 and recall 0.919. At 0.30, its mean F1 was 0.706, with precision 0.638 and recall 0.800. At 0.40, mean F1 was 0.595, precision was 0.504, and recall was 0.736. The widening difference between precision and recall indicates that false positive objects increased more rapidly than missed true objects. This pattern is consistent with local noise reversals fragmenting the directional state sequence and creating additional candidate oscillations.

The SciPy baseline remained above mean F1 0.90 at every tested noise level. Its mean F1 values were 0.989 at noise 0.20, 0.957 at 0.30, and 0.910 at 0.40. At the highest noise level, its precision and recall were both approximately 0.91. For the present sinusoidal detection task, the peak detector therefore retained object identities under noise more successfully than the alpha FeatureGraph directional construction.

Replicate variability also increased with noise. FeatureGraph's F1 standard deviation rose from zero at noise levels 0 through 0.10 to 0.083 at 0.20, 0.131 at 0.30, and 0.134 at 0.40. The corresponding 95% half-widths were 0.030, 0.047, and 0.048. SciPy F1 standard deviations at the same levels were 0.029, 0.064, and 0.087, with half-widths of 0.010, 0.023, and 0.031. Thus, degradation at higher noise levels was accompanied by greater sensitivity to the particular noise realization for both methods, but more strongly for FeatureGraph.

### Boundary localization and interval agreement

The exact-recovery check and the held-out zero-noise run answer different questions. Exact recovery used a construction aligned with the clean analytical reversals. The held-out robustness experiment instead used the operating point chosen at noise standard deviation 0.20 and retained its 9-sample smoothing window and 10-sample difference lag at every noise level. Consequently, the tuned FeatureGraph run detected all clean objects but did not place their landmarks at the analytical sample indices.

At noise standard deviation 0, tuned FeatureGraph achieved mean interval IoU 0.790. Its start, peak, and end MAEs were 9.67, 8.00, and 9.00 samples, respectively. Duration MAE was only 0.67 samples because the start and end boundaries were displaced in broadly similar directions. These offsets remained relatively stable through moderate noise: at noise 0.20, mean IoU was 0.787, peak MAE was 7.69 samples, start MAE was 9.69 samples, and end MAE was 9.23 samples. The result shows that the selected smoothing and lag changed boundary semantics systematically even when object count remained correct.

At noise 0.30 and 0.40, FeatureGraph mean IoU declined modestly to 0.783 and 0.767 among matched objects. Peak MAE decreased to 7.33 and 6.86 samples, while start and end errors remained near 9 to 10 samples. This apparent improvement in peak MAE should not be interpreted as improved overall performance: F1 declined sharply at the same noise levels, and localization metrics were calculated only for detections that still met the matching criteria. The worsening unmatched detections were expressed through precision and recall rather than through the conditional MAE.

SciPy had exact boundaries at noise 0 and mean interval IoU values of 0.958, 0.941, 0.918, 0.904, and 0.896 as noise increased from 0.05 to 0.40. Peak MAE rose from 1.68 samples at noise 0.05 to 3.94 samples at 0.40. Start and end MAEs similarly increased from approximately 1.7 samples to approximately 4.4 samples. The baseline therefore showed gradual localization degradation, while retaining greater interval overlap than FeatureGraph throughout the noisy tests.

### Object-property error

FeatureGraph's tuned construction preserved duration more accurately than its individual landmark errors might suggest. Duration MAE was 0.67 samples without noise, 0.98 at noise 0.05, 1.46 at 0.10, 3.03 at 0.20, 4.34 at 0.30, and 7.51 at 0.40. SciPy duration MAE increased from zero without noise to 2.63, 3.56, 4.86, 5.71, and 6.19 samples over the same nonzero noise levels. Among matched objects, FeatureGraph therefore had lower mean duration error through noise 0.30, despite its lower detection F1 at the two higher levels. At noise 0.40, its duration error exceeded the SciPy baseline.

FeatureGraph amplitude MAE remained comparatively small, increasing from 0.020 without noise to 0.087 at noise 0.40. SciPy amplitude MAE increased from zero to 0.679 over the same range. Temporal-symmetry MAE increased from 0.034 to 0.148 for FeatureGraph and from zero to 0.124 for SciPy. These conditional property results show that the alpha construction could still measure several properties of the objects it matched even as its detection precision deteriorated. They do not compensate for unmatched objects and should therefore be interpreted together with F1.

### Summary of the synthetic evaluation

The synthetic experiments establish two distinct results. First, the alpha implementation can reproduce known oscillation boundaries and properties exactly under clean, construction-aligned conditions. This verifies the deterministic transformation from state evidence to object tables. Second, its directional detector is sensitive to noise and to the smoothing and lag used to stabilize that noise. The selected parameters preserved all low-noise object identities and yielded small conditional errors for duration and amplitude, but higher noise increasingly fragmented the state sequence and reduced precision.

SciPy was the stronger detector for the synthetic sinusoidal benchmark, especially above noise standard deviation 0.10. This is a useful limitation rather than a contradiction of the framework's principal contribution. FeatureGraph does not derive its value from replacing specialized peak detectors in every setting. Its contribution is the explicit behavioral representation built after a construction has been specified: bounded object identity, retained state and event evidence, reproducible properties, completeness, composition, and object-level queryability. The evaluation shows that the reliability of that representation remains conditional on the reliability and semantics of the detector used to construct its boundaries.
