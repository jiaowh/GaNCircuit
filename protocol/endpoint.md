# Endpoint and uncertainty specification

Frozen consolidation, 9 September 2026. This file is the sole operational definition of verification. Historical plans are background only.

## 1. Population and physical event

The population is the final sizing from each independent generator run that passes its registered schematic specification. Trajectory designs may train models but never increase the headline population count. Fixed topologies, Sky130A, a pinned toolchain, and two separately reported layout policies (ALIGN and the OSIRIS baseline) are retained. No result is called measured silicon yield.

Each topology manifest must contain the netlist and testbench hashes, device models, exposed parameters, property units and thresholds, inequality direction, source/load values, grid, legal geometry ranges, seeds, tool versions, and layout policy. Missing fields fail preflight. Use the benchmark's thresholds; OSIRIS thresholds are explicitly labelled study-defined and frozen from its reference sizing before harvesting. Report phase margin everywhere; constrain it only if the registered specification does.

The corner set is tt/ss/ff × {1.62, 1.80, 1.98 V} × {-40, 27, 125 °C}, plus sf/fs at 1.80 V and 27 °C: 29 points. Only compatible 1.8 V topologies enter this manifest. Global random process variation is off; the registered kit mismatch terms are on. Verify the installed model switches, units, bin slopes, and explicit-offset patch before generating data.

A chip draw is one independent vector of standardised per-device mismatch offsets. Reuse that vector across all corners and all constrained properties of that chip; apply the kit's corner-specific transformations to it. This coupling is part of the stated model, not an inferred fabrication distribution. Device identity must persist across corners. Distinct chip vectors are IID. Common vectors across candidates are allowed for paired evaluation, with design-clustered inference.

For a structurally valid extracted design d, define:

* N(d): every constrained property passes at every corner with mismatch set to zero.
* B(d,z): every constrained property passes at every corner for chip vector z.
* p(d) = P_z[B(d,z)=1]. This is an all-corner, joint-property chip-pass probability, **not** the minimum of per-corner yields.
* Physical feasibility: N(d)=1 and p(d) >= 0.90.

The reference endpoint is `PCM_FULL_JOINT_250`. The nominal-worst-corner event is a separate diagnostic. It never certifies this endpoint. There is no shortcut-validation switch, no 40/60-design agreement claim licensing its substitution, and no endpoint change after seeing outcomes. Report per-corner and worst-corner results from the same full draws where available. This deliberate simplification costs more; the manifest includes that cost.

## 2. Parameters, margins, and numerical status

Continuous coordinates are log10(W), log10(L), and log10 of positive passive values exposed to sizing; signed/zero source variables use asinh(v/v0) with v0 frozen per source class. Tied devices share coordinates. Multiplicity and fingers are discrete. Supply, load, corner, temperature, testbench and layout policy are context.

Range-check, quantise to the verified manufacturing grid, then recheck legality and identify the model bin. Never snap to model bins. Record requested and realised displacement, grid no-ops and bin crossings. Continuous finite-change labels use realised endpoints. Smooth derivatives use unquantised schematic endpoints, remain inside one bin, and are reported separately. Use central differences in a rank-deficient derivative training subspace; comparisons on its orthogonal complement use the same frozen scaled-coordinate metric for every arm. Reject and count directions rotated more than 5 degrees by quantisation; do not call the resulting asymmetric chord a central derivative.

For a positive ratio-scale property, margin is s*log10(value/threshold), where s=+1 for a lower bound and -1 for an upper bound. Convert dB gains to linear ratios before this calculation. For signed properties use s*(value-threshold)/Delta, with registered Delta (phase margin: 10 degrees; offset: 1 mV). Represent two-sided constraints as two inequalities. A nonpositive value on a property defined to be positive is an invalid/failed measurement, never clipped into the logarithm. The design's nominal margin is the minimum across constraints and corners, with stable property/corner ID breaking equal minima.

Use an equivalence-group schematic/extracted device map. Preserve devices with independent mismatch draws as distinct instances. Splitting with a shared offset must preserve the registered effective-area law and be verified on reference circuits. Ambiguous mapping blocks that design's mismatch evaluation; scalar aggregation is not assumed to preserve response.

Outcomes distinguish geometric/DRC/LVS failure, extraction failure, simulator failure, measured constraint failure, and pass. Structural failures fail physical verification. Infrastructure timeouts are unresolved, not evidence that the circuit is physically impossible. A measurement timeout is 600 simulator seconds per corner job; layout/extraction timeouts are 1,800 seconds per job. Retry at most twice with the same chip vector under a frozen solver-option ladder. Never redraw a failed chip. Record all attempts and elapsed/core time. Remaining ambiguous chips are unresolved. A definite failing property suffices to label a chip failed even if another property is unresolved.

## 3. Certification: one fixed sample

1. Canonicalise, layout, independently run Magic DRC, run LVS, and extract R and C. Cache by complete design/policy/tool hash.
2. Run all 29 nominal corners. If N=0, return `FAIL_NOMINAL`; if N is unresolved, return `INDETERMINATE_NUMERICAL`.
3. If N=1, evaluate exactly **250** fresh chip vectors. There is no 50-draw look or sample escalation. Evaluate corners in a fixed registered order; stopping a chip at its first definite failure is permitted for certification because its conjunction is then known. It changes the number of simulator jobs, not the 250-chip denominator. Full-property ranking/propagation datasets do not use this early exit.
4. Let S be definite chip passes, F definite failures, U unresolved, with S+F+U=250. Construct [L_CP(S,250), U_CP(S+U,250)] from equal-tailed 95% Clopper–Pearson limits. Return `PASS` if L>=0.90, `FAIL_YIELD` if U<0.90, otherwise `INDETERMINATE_YIELD`. Nominal and yield statuses remain separate columns; unmeasured yield is never inferred from nominal failure.

For alpha=0.05, L_CP(k,n)=0 if k=0, otherwise BetaQuantile(alpha/2;k,n-k+1). U_CP(k,n)=1 if k=n, otherwise BetaQuantile(1-alpha/2;k+1,n-k). These fixed-n intervals have coverage at least 1-alpha for every p in [0,1], under the IID Bernoulli model. The guarantee follows from exact binomial tail inversion, not a checked grid. Widening to the two extreme assignments of unresolved outcomes contains the interval for the unobserved complete count, without a missing-at-random assumption. Coverage does not imply a posterior probability that a particular design is feasible.

References: [R's exact binomial test](https://www.stat.math.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html), [SciPy's exact interval API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html). The repository's standard-library implementation independently inverts binomial tails and checks boundary cases. Numerical grid checks are regression checks only.

## 4. Screening and adaptive repair confirmation

Screening is optional cost control, never certification. In 3B, after the cheap schematic screen and physical construction, check the episode's original nominal-worst corner, then 20 independent chips at that corner. Reject only if the **one-sided exact 95% upper** binomial limit using S+U is <0.90. Screening data are not pooled into certification or confirmation. Screen-rejection rates and simulator costs are reported by method.

A preliminary certification triggers one fresh **250-chip** confirmation on the same full joint endpoint, with the same cached nominal/structural result. The candidate and all its predictions are frozen before these draws. For confirmation attempt j within an episode/method run, j<=25, use the one-sided exact lower limit with alpha=0.05/25=0.002. An unresolved chip counts as a failure for this lower limit. Confirmation succeeds only if this lower limit is >=0.90. Otherwise continue the repair loop; there is no second confirmation of the identical candidate.

This allocation controls the probability of at least one false confirmed acceptance at <=5% **within an episode/method run**, even with adaptive candidate selection, because each conditional test uses fresh independent draws and there are at most 25. It is not a simultaneous guarantee over the full thesis or all methods. Individual preliminary 95% intervals are likewise not simultaneous intervals for a selected collection. Report the allocation and the distinction explicitly.

One expensive check is one distinct candidate admitted to physical construction, including any screening, certification and confirmation it triggers. The cap is 25 such candidates per episode/method. Record every component separately in simulator calls, CPU seconds, wall seconds and queue time. Also cap proposal rounds at 25, with 16 proposals per round and k=2 promotions; deduplicate candidates before promotion. An episode with no confirmed success at either cap is unsolved, with restricted cost 25 for the primary analysis. Failed jobs consume actual resources and remain in the candidate's check.

## 5. Measurement cells and shortcuts

For the claim-1 factorial, evaluate schematic and extracted netlists under the same 250 chip vectors and 29 corners even for nominal-failing designs, so mechanism measurements are observed rather than inherited. Derive M/PM from the typical-corner columns, CM/PCM from the all-corner conjunctions, and nominal cells 0/P/C/PC from the nominal columns. Extraction is the only policy-dependent schematic/extracted difference; schematic results are reused across policies. Invalid layouts have physical failure labels but no invented property vectors.

The 2,000-design manifest is a maximum full-factorial allocation, not a claim that all cells will be populated. Report attempted/supported/valid denominators, policy pairing, and the number of distinct topologies separately from specifications. No separate escape subsample is needed when nominal-failing valid designs receive the full factorial. Non-monotone and unresolved factor patterns are reported directly; do not force an eight-class causal partition or drop them from the denominator.

Any future proposal to replace this endpoint with a cheaper event is a new study. It cannot be activated as an undocumented budget fallback.
