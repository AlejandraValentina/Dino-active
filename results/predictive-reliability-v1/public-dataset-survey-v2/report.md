# Public experimental references — bounded update, 2026-10-26

**SELF_REVIEW. No validation reference adopted, engine configuration created or
measurement invented.** Primary material inspected directly; bibliography alone
does not establish data completeness. Source PDFs remain outside Git, with hashes
and locations in `receipt.json`.

## Corrected coverage of the existing X30 evidence

`results/x30-preparation-v1/figure10-digitized.json` already contains 20 readings
of the measured line in Ortenzi/Bossaglia Figure 10, with a digitization bound of
0.3 kW and horizontal bound 20 RPM. Those are approximate readings of published
measurements, not original experimental samples or a dynamometer uncertainty.
`results/x30-public-reconstruction-v1/` adds nominal geometry, but the assembled
crankcase free volume/convention and matching test details remain unresolved.
The previous narrow inventory did not represent all of this partial evidence;
its conclusion that a **complete matched input/test package is not established**
remains valid. Historical inventories/digitization were not rewritten.

## Newly inspected candidate with actual component measurements

[Ohigashi, Hamamoto & Tanabe, 1971, primary publication](https://www.jstage.jst.go.jp/article/jsme1958/14/71/14_71_470/_article)
provides inlet oscillation measurements and a crankcase volume. The machine-
readable candidate preserves measured versus author-calculated periods
separately. PDF pp. 1–6 inspected visually, especially Tables 1/2 and Figures 1/4.
**Promising for an inlet subsystem comparison; not adopted as a complete-engine
power reference.** Boundary/thermal conditions, remaining geometry and uncertainty
must be established before simulation. No unreported quantity was filled.

## Other primary sources and actual access/quality findings

| Candidate | Evidence actually available | Decision |
|---|---|---|
| [Zhang 1995, Yamaha MT-110S](https://vuir.vu.edu.au/18232/1/ZHANG_1995compressed.pdf) | Complete 169-page thesis downloaded, instrument description and measured pressure/torque curves; Table 5.1 visually checked. It lists 52×50 mm, rod 101 mm and capacity 100 cm³. The geometric displacement is 106.186 cm³, so the convention/discrepancy needs clarification. A complete crankcase/duct input package was not established by the bounded inspection. | Useful experimental literature; not an executable validated fixture. Original recordings/uncertainty not established. Do not silently choose between inconsistent dimensions. |
| [Cahoon 1971, QUB](https://pure.qub.ac.uk/en/studentTheses/unsteady-gas-flow-through-a-naturally-aspirated-two-stroke-intern/) | Institutional abstract describes measured pressures in several paths and three engine configurations; linked thesis returned HTTP403 in this session. | Promising, but full methods/geometry not inspected. Do not infer completeness or bypass access controls. |
| [Gore, NC State, KT100](https://repository.lib.ncsu.edu/bitstreams/24433484-a6eb-4ad8-80f1-a18fa75c4ef6/download) | Existing historical survey plus current repository search record. Full PDF request timed out; official content endpoint presented bot detection. | Access unresolved in this session. Neither reject its scientific quality nor claim its missing inputs are supplied. No legacy KT100 task reopened. |
| [Bath, DOI 10.15125/BATH-01083](https://researchdata.bath.ac.uk/1083/) | Public MATLAB files advertised, but repository explicitly classifies them as GT-SUITE simulation output for opposed-piston geometry. | Not independent experimental validation of Dino. Machine-readable data are not automatically measured data. |
| [NACA TM446, 1928](https://ntrs.nasa.gov/citations/19930090756) | Original report openly readable: gas-analysis/scavenging experiments on a hot-bulb engine, with sampling and measurement limitations. | Potential historical subsystem context; not a matched gasoline SI power dataset. |

## Decision and finite next requirement

There is a more directly useful **component-data candidate**, rather than a newly
established full-engine validation dataset. The next bounded reference check is
the completeness of the Ohigashi Engine A inlet case: resolve the reported case's
geometry, boundary/thermal assumptions, measurement convention and uncertainty.
If essential inputs cannot be established, keep it partial. Do not fit absent
quantities to its measured periods and then call that fit a blind validation.

The X30 stays partial, separate from the synthetic engine, without execution or
arbitrary crankcase volume. No new reference is substituted for it automatically.
No emails, purchases, experiments, raw-data digitization or campaigns were made.
P9's frozen contract and point-count requirements are untouched: a component
comparison could validate its limited subsystem only, not pass P9 or prove an
entire periodic power curve. This bounded survey does not assert that no complete
public dataset exists elsewhere.
