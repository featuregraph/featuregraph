# TEP reactor-pressure transfer study

## Question

Does the reactor-pressure construction selected on Tennessee Eastman Process
Fault 2, simulation run 10, transfer unchanged to other Fault 2 runs, normal
operation, and contrasting fault classes?

## Frozen construction

The development construction was not changed during transfer:

- signal: `reactor_pressure`
- 50-sample rolling maximum
- 50-sample rolling mean
- offline alignment: `shift(-50)`
- rising/falling/inactive states from the sign of the aligned pressure rate
- peak event: valid-to-valid exit from the rising state
- object identity: half-open peak-to-peak intervals `[peak_i, peak_i+1)`
- leading and trailing intervals retained as incomplete boundary fragments

Run 10 was the development run. Runs 1–9 were held-out Fault 2 replications.
The negative control was the 500-hour normal Mode 1 record divided into ten
non-overlapping 50-hour windows. Specificity was provisionally assessed using
simulation run 10 from each of the other 20 fault classes.

The construction produced 32 peak events and 31 complete cycles on the
development run. All structural validations passed.

## Fault 2 replication

| Run | Peak events | Maximum aligned peak | Peak index | Peak excess over run median | Maximum preceding-trough prominence |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 28 | 2806.300 | 641 | 4.639 | 4.822 |
| 2 | 24 | 2807.414 | 644 | 5.621 | 6.318 |
| 3 | 26 | 2806.804 | 630 | 5.001 | 4.623 |
| 4 | 24 | 2805.597 | 687 | 3.914 | 2.645 |
| 5 | 29 | 2807.597 | 650 | 5.876 | 6.704 |
| 6 | 30 | 2806.187 | 631 | 4.599 | 5.365 |
| 7 | 27 | 2804.962 | 645 | 3.258 | 3.071 |
| 8 | 27 | 2807.028 | 645 | 5.336 | 5.773 |
| 9 | 24 | 2805.790 | 650 | 4.106 | 4.225 |
| 10 (development) | 32 | 2806.578 | 637 | 4.825 | 4.029 |

The maximum aligned peak occurs between indices 630 and 687 in every Fault 2
run. This is a reproducible Fault 2-associated reactor-pressure response under
the frozen representation.

## Normal-operation transfer

| Property | Fault 2 minimum | Fault 2 median | Fault 2 maximum | Normal-window minimum | Normal-window median | Normal-window maximum | Complete separation? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| Maximum aligned peak | 2804.962 | 2806.439 | 2807.597 | 2803.047 | 2803.132 | 2803.689 | Yes |
| Peak excess over run median | 3.258 | 4.732 | 5.876 | 1.294 | 1.482 | 1.950 | Yes |
| Maximum preceding-trough prominence | 2.645 | 4.723 | 6.704 | 1.875 | 2.256 | 3.060 | No |
| Peak-event count | 24 | 27 | 32 | 25 | 28 | 31 | No |

Maximum aligned peak pressure and peak excess separate all ten Fault 2 runs
from all ten normal windows in this cohort. Prominence and event count do not.
This means the transferred representation detects a repeatable abnormal
pressure level, not simply an unusually prominent ordinary cycle.

## Contrasting fault classes

The following run-10 fault classes produced peak excess equal to or greater
than Fault 2 run 10 (4.825):

| Fault | Maximum aligned peak | Peak excess | Peak index |
| ---: | ---: | ---: | ---: |
| 13 | 2842.259 | 40.646 | 1963 |
| 8 | 2831.157 | 28.993 | 1833 |
| 20 | 2819.763 | 15.138 | 2582 |
| 1 | 2811.575 | 9.889 | 648 |
| 11 | 2812.141 | 7.732 | 1878 |
| 17 | 2810.201 | 7.041 | 2487 |
| 7 | 2807.739 | 6.045 | 653 |
| 18 | 2807.277 | 5.259 | 1915 |
| 12 | 2807.922 | 4.870 | 1420 |
| 2 | 2806.578 | 4.825 | 637 |

Faults 1 and 7 also create large early reactor-pressure peaks near the Fault 2
peak time. Consequently, neither peak magnitude nor timing on this signal is
sufficient for Fault 2 identification.

## Supported conclusion

The frozen FeatureGraph construction transfers across all ten Fault 2 runs and
separates their dominant reactor-pressure peak from ten matched normal-operation
windows. It therefore identifies a repeatable Fault 2-associated pressure
response in this cohort.

It does **not** identify Fault 2 specifically. Reactor-pressure peak magnitude
is a broader fault-sensitive representation shared by multiple fault classes.

## Next discriminative study

Keep this pressure construction frozen. Add independently motivated objects
from the variables that distinguish the Stream 4 composition faults, then test
relationships among those objects and the pressure response. Candidate
properties should be selected before evaluating the remaining runs from the
other fault classes. The next evaluation should use all available runs per
contrasting class and report a run-level confusion matrix and detection latency.

## Scope limitations

- The normal control consists of ten windows from one continuous 500-hour
  normal record, not ten independent simulations.
- Cross-fault specificity currently uses one matched run per contrasting class.
- The selected signal and development run were chosen with knowledge of the
  Fault 2 label.
- These results support deterministic representation and transfer, not causal
  diagnosis or operational deployment.
