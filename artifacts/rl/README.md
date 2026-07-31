# FeatureGraph reinforcement-learning comparison

This experiment tests whether an explicit, causal behavioral representation
improves reinforcement-learning performance relative to raw observations.
CartPole uses pole angle as its oscillatory signal; MountainCar uses position.

## Pre-registered conditions

1. `raw`: the environment observation.
2. `raw_history`: current and previous raw observations.
3. `featuregraph`: causal phase and completed-cycle properties only.
4. `augmented`: raw observations plus the same FeatureGraph properties.

The history condition is a required control. It distinguishes value added by
behavioral construction from value added by one extra step of memory.

## Causality contract

At sample `t`, the encoder may use only observations through `t`. A phase is
completed only after its reversal is observed. A cycle is completed only after
three alternating extrema have been observed. No final amplitude, duration, or
future boundary is backfilled into earlier agent observations.

Each episode resets all state. The online representation includes direction,
reversal, elapsed phase time, displacement and signed area since the latest
extremum, the preceding completed phase, and the preceding completed cycle.

## Run

```bash
python -m pip install -e '.[rl]'

python -m experiments.rl.run_dqn --environment cartpole
python -m experiments.rl.run_dqn --environment mountaincar
```

Defaults run all four conditions with the same 20 seeds. CartPole receives
100,000 environment steps per run; MountainCar receives 200,000. Greedy
evaluation uses 20 fixed held-out episodes every 5,000 training steps.

Use a short smoke run before launching the full matrix:

```bash
python -m experiments.rl.run_dqn \
  --environment mountaincar \
  --representations raw augmented \
  --seeds 0 \
  --total-steps 2000 \
  --evaluation-interval 1000 \
  --evaluation-episodes 2
```

Results are written to `artifacts/rl/results/`. Per-run JSON preserves the full
configuration and evaluation curve; the combined CSV supports downstream
analysis. Inputs are scaled with fixed environment constants rather than
statistics estimated separately for each representation or run.

Calculate paired learning-curve effects after the full matrix completes:

```bash
python -m experiments.rl.analyze \
  artifacts/rl/results/cartpole_curves.csv \
  --output artifacts/rl/results/cartpole_analysis.json
```

## Primary analysis

The implemented primary comparison is paired-seed learning-curve area for `augmented`
versus `raw`. Secondary comparisons cover time to threshold, final return,
success rate, seed variance, `featuregraph` alone, and the `raw_history`
control. Report paired bootstrap 95% confidence intervals and paired effect
sizes. Correct inferential comparisons across the two environments.

Model parameter count is recorded at every evaluation. The experiment uses the
same optimizer, replay policy, hidden widths, training budget, evaluation
episodes, and seed schedule in every condition. Any interpretation must report
the modest input-layer parameter difference as a limitation or rerun with a
parameter-matched sensitivity analysis.

## Required follow-up robustness study

After the clean-observation comparison, evaluate frozen policies under:

- additive observation noise;
- randomly missing observations with last-value carry-forward;
- altered force, gravity, or pole dynamics where supported.

These tests are secondary and must not be used to tune the primary experiment.
