# Critical review and independent development plan

**Review date:** 2026-09-28. **Source:** Soyeon Park, *Contributions to
ML-Metaheuristics for structural, material optimizations and energy consistent
particle-based simulations*, doctoral dissertation, Korea University, August 2025.
This is a technical review of the supplied 111-page dissertation, not an assessment
of its author. Body page numbers below use the printed numbering; add 19 for the PDF
page number. No original implementation, training data or checkpoints were supplied.

The source copy is marked CC BY-NC-ND 2.0 KR. We do not redistribute its PDF,
figures or an edited derivative. This document is independent commentary. The new
code is independently written and is **not an exact reproduction** of the thesis.
Scientific ideas remain attributed; our projections are standard constrained
least-change mathematics, not an asserted new discovery.

## Overall assessment

The strongest contribution is a complete engineering workflow: define a physical
problem, generate or calibrate data, use a surrogate for expensive searches, and
check selected designs experimentally. Chapter 2 includes fabricated patterned
tubes and measured stiffness. Chapter 3 combines manufactured ferrite samples with
an electromagnetic/ML model rather than treating a generic dataset as physical truth.
Chapter 4's interesting move is to learn a *numerical algorithm setting*, rather
than predict only a design response.

The evidence is more limited than a claim of a generally accurate, conservative,
fast computational-mechanics solver. My assessment is: valuable application-led
research, with substantial further verification needed before extending its broad
claims. This is not an inference that the source code is wrong. Several concerns
are about the printed definition, experimental protocol or strength of inference;
without code and data they remain reproduction questions.

### Cost correction

Printed p.81 explicitly reports **187 hours for offline data generation and 13 hours
for training**, 200 hours in total (8 days 8 hours). It reports inference within
2 ms per time step and about **30% more total simulation time**. It does not report
70 or 140 days for this MPM procedure. Physical simulated time, computer wall time,
training-sample count and wall time of the surrogate-only search are different.

In Chapter 2, p.15 gives about 700 seconds per FE sample and 855 cases. Multiplying
those figures gives 166.25 serial compute hours, not an observed end-to-end duration;
parallelism and overhead are unspecified. The reported 900-second optimization is
not the full data-generation-plus-training pipeline. Similarly, the Chapter 3
700-second search does not include manufacturing and model construction.

## 1. Tubular robots: good experiments, insufficient feasibility margin

**Keep:** topology-inspired pattern selection, a compact three-variable surrogate,
FE rechecks and actual laser-machined specimens. These are stronger than merely
reporting an optimizer's convergence curve. Sources: pp.9-15, 20-23.

**Concern R1: the final manufactured designs do not strictly meet the stated bounds
in the displayed measurements.** Table 3, p.23, lists a bending-stiffness bound of
B* >= 0.3 for CASE1 but experimental B*=0.281 for its optimum. CASE3 requires B* >=
0.1 but its optimum measures 0.093. Manufacturing variation and model error are
acknowledged on pp.22-24, but saying that experimental feasibility is established
without qualification is too strong. A useful next method would optimize a lower
confidence bound or a manufacturing-tolerance margin, then validate independent
specimens. This does not discard the demonstrated stiffness-ratio improvements.

**Concern R2: convergence is not a proof of global optimality.** Three design
variables include one integer. A fair baseline can enumerate that integer and use
multi-start constrained local optimization in the remaining two variables, alongside
Bayesian optimization or differential evolution. Use equal *true FE evaluation*
budgets, repeated seeds, final FE feasibility and wall-clock cost. Nearby perturbations
on p.15 support local robustness, not global-optimum certification.

**Concern R3: quantities and tables need editorial reconciliation.** Equation (7)
minimizes B*/T*, and the stability criterion on p.7 uses EI/GJ. Wording that reverses
bending/torsional order should be aligned with those definitions. A lower bound on
stiffness is not a lower bound on compliance. Table 1, p.18, lists CASE2 B*=0.100
under a 0.2 bound, whereas Table 2, p.20, lists 0.2. These are printed inconsistencies,
not values that this review silently replaces with guessed corrections.

**Development direction:** retain the small surrogate, introduce geometry-family
holdouts and fabrication uncertainty, and use robust feasibility as an objective
of the research. A much larger neural network is not the first missing ingredient.

## 2. Ferrite composition: useful hybrid modeling, adaptive test reuse

**Keep:** physical manufacturing, a fabrication-specific simulator, coefficient
calibration, and final experimental checks. The measured-noise discussion is also
valuable. Sources: pp.31-45 and 54-56.

**Concern R4: the stated test protocol is adaptive.** P.34 defines 10 test samples
from a 70-sample candidate pool, while pp.46 and 48 describe using test errors and
that pool to select extra data around poorly predicted points. P.42 also uses test
error to decide iterative refinement. Thus the repeatedly inspected set is serving
as a validation/acquisition set. Its result is not an untouched final generalization
estimate. The text supports an adaptive-reuse concern; it does not prove that test
labels were directly inserted into the training array.

Separate training, acquisition/validation and final lockbox experiments. Keep complete
manufacturing batches together and tune preprocessing and hyperparameters without
consulting the lockbox. An independent batch manufactured after freezing the optimizer
would be especially useful.

**Concern R5: generated labels are not independent measurements.** CoeffNet and
LossNet participate in the FS-FE model (pp.36-42), and simulation-driven labels are
then used to refine models. This can provide coverage and regularization, but also
propagate the teacher's systematic bias. More synthetic points alone do not create
new empirical information. Model simulator-to-experiment discrepancy explicitly,
weight observations by uncertainty, and verify selected acquisitions experimentally.

**Concern R6: improvements are regional, not uniformly monotone.** Table 8, p.51,
shows target-region accuracy improving 77.2 -> 84.8 -> 86.4%, while whole-dataset
accuracy changes 90.6 -> 95.0 -> 93.3%. That is a tradeoff worth reporting, not simply
an all-around gain. Prediction agreement at one selected optimum is not the same
metric as performance across the held-out set. These regression percentages also
need precise definitions, confidence intervals and raw errors for interpretation.

**Development direction:** cost-aware multi-fidelity acquisition with a discrepancy
model, uncertainty-calibrated constraints and a final untouched experimental batch.
It should be compared against simpler direct composition-to-response baselines.

## 3. MPM: interesting target, but conservation must be verified at deployment

**Keep:** optimize transfer parameters rather than use a fixed heuristic; use
nondimensional descriptors; distinguish an expensive offline teacher from an online
model. The limitations on p.81 explicitly acknowledge reduced out-of-domain
performance and training restricted to 2D elastic collision cases. Sources: pp.57-81.

### R7. The printed energy definition needs an audit before implementation

Equation (39), p.67, visibly includes particle mass multiplying stress, strain and
particle volume in the strain-energy sum. Under ordinary stress/strain/volume units,
that adds an extra mass dimension. A linear small-strain energy would use
0.5 * sum(V * sigma:epsilon) under the corresponding assumptions, whereas a finite
hyperelastic model normally needs the material's stored potential sum(V0 * W(F)).
This could be a typesetting error; do not infer the executable code uses it.
Ask for the original energy routine, unit convention, material energy potential and
reference/current volume convention. Then run dimensional, energy-derivative and
rigid-rotation tests before reproducing any optimization labels.

### R8. A full-step energy difference is not an isolated G2P error

Equation (38) compares total energy at consecutive times. Such a quantity combines
transfer, grid update, stress integration, boundary/contact work and physical
constitutive dissipation. The unforced elastic examples simplify the energy balance,
but do not isolate a single algorithm stage. Record stage-specific budgets as well
as a work-corrected full-step balance. A proper full-step residual is
`E_next - E_now - W_external + D_physical`; its definition is our proposed audit,
not a rewritten claim about the original source.

### R9. Reported improvement is not near-conservation in all examples

The optimized-parameter two-disk example on p.73 reports about 2.5% loss. This is
not the same as the deployed-ML validation: pp.77-81 report 26.7% loss for disk
impact and roughly 60% for the vibrating beam, versus 58.9% and 76.7% for FLIP.
Those are improvements under the reported conditions, but 60% loss is not a strong
energy-conserving result. Energy retention alone also fails to establish displacement
phase, stress accuracy, contact timing or mesh/time convergence. The new independent
harmonic-state counterexample demonstrates why a flat energy trace is insufficient.

### R10. Constrained teacher labels do not make independent ML predictions constrained

The teacher uses a global linear-momentum condition (Eq.37/40, pp.67-68), while the
student predicts local coefficients from local features. Algebraically, for a
correction `delta_v_p = alpha_p * r_p`, a uniform coefficient preserves a zero
mass-weighted sum of residuals, but varying alpha generally does not. Bounding
alpha in [0.9,1] does not impose that global equality.

This is a deployment risk, not proof of a measured momentum failure in the thesis.
The testable remedy is a conservation-aware parameterization or constrained
projection followed by rollout validation. `femlab/conservation.py` implements the
fixed-position mass-weighted least-change velocity projection as one building block.
It can change kinetic energy and may not respect contact, prescribed velocities or
the original coefficient family. It must not be advertised as solving those issues.

### R11. Labels may be ambiguous; parameter MSE is not the physical objective

There are two coefficients per particle and a small number of aggregate conservation
criteria. Distinct coefficient fields may attain similar objectives. A local state
can also omit nonlocal information that the global teacher used. Therefore a noisy
or non-unique label map is a plausible hypothesis to test, not an established defect.
Use repeated teacher runs, inspect label dispersion and compare achieved physical
cost for different labels. Consider minimum-change regularization, spatial/temporal
coherence and a short rollout objective rather than just one-step energy matching.

The p.74 dataset has 14,000 rows and a 70/20/10 split, but the documented split does
not establish separation by independent trajectories or resolution. The p.75 model
uses seven 256-unit hidden layers. Neither size nor row count proves overfitting;
whole-trajectory holdouts and simple baselines are needed. Small relative coefficient
errors can still matter when the allowed coefficient interval is narrow.

### R12. Reproducibility and cost claims need more evidence

The data/model/code needed for exact reproduction are not in the supplied source.
Appendix A, p.90, visibly states an acceptance inequality `F_new > F_old` despite
the minimization framing. It should be clarified against the actual implementation,
not copied blindly into a new optimizer. Equations, constraints and indexing need a
source-to-code audit, including double mapping and stress-update order.

With the p.81 cost figures, the learned transfer is not a speedup over its fixed
baseline on an equal-resolution run. Faster time-to-accuracy could still be possible
if a baseline needs substantially finer resolution, but that requires matched-error
benchmarks. Count offline labels, hyperparameter search, inference, rejected proposals
and final verification, not only a 2-ms model call.

## 4. My proposed development: constrained assistance, not a bigger black box

**H1:** a projection or conservation-compatible output representation will reduce
momentum defects of local transfer proposals. First test it on controlled synthetic
states, then full rollouts. Reject H1's usefulness if the correction damages stress,
phase or stability enough to negate the benefit. Projection is not automatically a
better solver.

**H2:** physically meaningful short-rollout losses and deterministic teacher
regularization will generalize better than imitation of one arbitrary coefficient
label. Evaluate on held-out trajectories, rotated configurations, material regimes
and grid/particle resolutions. Report failures rather than censoring them.

**H3:** a small residual model with active data acquisition can approach the target
accuracy with fewer expensive labels than a large unconstrained MLP. Compare constant
settings, ridge/small MLP, GNN and teacher search under equal evaluation budgets.
Include inference/training cost. No improvement is claimed until measured.

**H4:** for design optimization, robust constraints and final physical rechecks will
improve feasible-design yield compared with optimizing mean surrogate predictions
right at a nominal boundary. The experimental shortfalls in Table 3 motivate this
hypothesis; new independent fabrication data would test it.

### Current literature context, not a claim that 2025 research is obsolete

Two relevant 2026 preprints were checked at the abstract/method-overview level:

- Choi and Macedo, *Differentiable Graph Neural Network Simulator for the Back-Analysis
  of Post-Liquefaction Residual Strength from Flow Failure Runout*, arXiv:2602.11621,
  12 February 2026. It links MPM-generated training data, graph simulation and
  gradient-based inverse analysis. This motivates a downstream inverse-design task;
  it does not establish exact energy conservation for learned transfers.
  https://arxiv.org/abs/2602.11621
- Fu, Jiang and Li, *An Implicit Compact-Kernel Material Point Method for Computational
  Solid Mechanics*, arXiv:2604.18917, 20 April 2026. It assesses compact-kernel implicit
  MPM on bending, contact and impact problems. A stronger **non-ML** baseline matters:
  an ML method should not win merely because its comparator is unnecessarily weak.
  https://arxiv.org/abs/2604.18917

These sources are not a comprehensive literature review or an independent validation
of their reported results. Neither method has been implemented in this update.

## 5. What this repository actually adds

The update adds a tested momentum-projection primitive, an explicit work-balance
metric, counterexample experiments, a bounded checkpoint/resume MPM runner,
source/config/environment checks, progress records, a read-only dashboard, a short
GitHub workflow and an opt-in workstation/HPC worker. Tests cover interrupted versus
uninterrupted replay, corrupted states, mismatched config/source, exclusive writing,
stop requests, persistent budgets and failure-state handling.

This is a foundation for the hypotheses, not evidence that FEMlab reproduces the
thesis or outperforms it. The existing broad bootstrap remains small: its GNN only
learns a fixed spring-chain example, its MPM has no full multi-body contact, and
its earlier static ML guard performs a full baseline solve. The next best investment
is a narrow, independently verified experiment rather than more placeholder modules.

**Conclusion:** keep the physical engineering workflow and algorithm-assistance
idea. Strengthen the definitions, constraint enforcement, independent validation and
cost accounting. Scientific progress should be measured by reproducible physical
accuracy and robust feasibility, not by neural-network size or how many days a job
has been running.
