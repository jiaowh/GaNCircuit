# Papers index

Maps every paper in this folder to the section of the earlier research plan (v10; removed from the working tree, in git history at commit `9a8e25b`) it supports. Built 6 September 2026 from a five-agent search (spine sources; layout/parasitics/yield; ML methodology; learned circuit models; device variability and compute-in-memory). 117 papers were added to the 39 already here. All files verified as PDFs; no paywalled copies were downloaded.

Filename convention for new files: `(YYYY) Short_Title arXivNNNN.NNNNN.pdf` or `(YYYY) Short_Title Venue.pdf`. Older files keep their original names.

## 1. Spine sources cited in v10 / v9 §15

| File | What it is | Plan section |
|---|---|---|
| (2026) AutoSizer_AMS-SizingBench_LLM_Agent_Sizing arXiv2602.02849 | Harness whose generators seed claim 1; full-flow ALIGN+Magic mode is the month 1–2 reproduction target | §4 Populations, §6, §7 |
| (2025) GLOVA_Variation-Aware_Risk-Sensitive_RL_Sizing arXiv2505.11208 | Only prior corner + global/local MC success rates; 28 nm, no layout | §1, §7 |
| (2025) EEsizer_LLM_Agent_AMS_Sizing arXiv2509.25510 | Baseline generator; 10/50-sample perturbation test (v9 correction) | §4, §9 |
| (2025) AnalogSAGE_Self-Evolving_Analog_Design_Multi-Agents arXiv2512.22435 | Ten SKY130 op-amp problems | §4 Circuit families |
| (2023) Gao_Post-Layout_Simulation_Driven_Analog_Sizing arXiv2310.14049 | Published post-layout sizing loop; claim 3 baseline | §4 Repair loop |
| (2020) AutoCkt_Deep_RL_Analog_Circuit_Design arXiv2001.01808 | 2.4 s schematic vs ~91 s with layout parasitics | §11 |
| (2026) Tan_What_Can_Latent_World_Models_Know arXiv2607.27017 | Latent world-model framing, deliberately not load-bearing (v3 confirmed) | §8 |
| (2023) CktGNN_Circuit_Graph_Neural_Network_EDA arXiv2308.16406 | Candidate cross-topology skeleton | §4 The model |
| Universal Neural Simulator for Analog (INSIGHT, arXiv 2407.07346, v3) | Candidate cross-topology skeleton | §4 The model |
| (2025) DICE_Device-Level_IC_Encoder_Graph_Contrastive arXiv2502.08949 | Alternative pretrained graph encoder | §4 The model |
| (2026) Analog-DB_Agent-First_Analog_IC_Database arXiv2609.01286 | 68 circuits, 3 open PDKs, typical corner, matched devices, no layout; in the regulator corpus 17 of 23 imported sizings failed their testbenches before a gm/ID loop closed them | §7, §9 |
| (2024) AnalogGym_Open_Testing_Suite_Analog_Synthesis arXiv2409.08534 | Thirty topologies; LDOs/amps on ngspice+SKY130 | §4 Circuit families |
| (2024) AICircuit_Multi-Level_Dataset_Benchmark arXiv2407.18272 | Cadence benchmark (excluded) | §4 |
| (2026) AnalogAgent_Self-Improving_Analog_Design_LLM_Agents arXiv2603.23910 | 97.4/100 Pass@1/@5, all pre-layout | §1 |
| (2026) AnalogMaster_LLM_Analog_IC_Image_to_Layout arXiv2604.20916 | Image-to-layout; no PEX reported | §1, §7 |
| (2026) AaLLM_End-to-End_Analog_Topology_to_Sizing_LLM arXiv2608.13472 | 91.6% spec-met, no layout | §1 |
| (2026) Self-Calibrating_LLM_Analytical_Equation_Sizing arXiv2604.07387 | "No prior work relates accuracy to convergence" | §2, claim 3 |
| (2026) EXPLORE_Guided_Search_Analog_Topology_Generation_LM arXiv2607.13416 | Topology generation (excluded); success figures still to extract | §8, §9 |
| (2025) AutoCircuit-RL_RL-Driven_LLM_Topology_Generation arXiv2506.03122 | Topology generation context | §8 |
| (2025) AMS-IO-Bench_AMS-IO-Agent_IO_Ring_Design arXiv2512.21613 | Only agent output validated in silicon | §1 |
| (2023) Graph-JEPA_Graph-Level_Joint-Embedding_Predictive arXiv2309.16014 | Reference for the excluded JEPA arm | §8 |
| (2024) Wolters_Memory_Is_All_You_Need_CIM_Overview_LLM arXiv2406.08413 | CIM non-idealities catalogue | §6 tile |
| (2024) ADO-LLM_Analog_Design_BO_In-Context_LLM arXiv2406.18770 | Generator in AutoSizer harness | §4 Populations |
| (2024) LEDRO_LLM-Enhanced_Design_Space_Reduction_Sizing arXiv2411.12930 | Generator in AutoSizer harness | §4 Populations |
| (2026) SABLE_NDA-Safe_Closed-Loop_LLM_Analog_Optimization_Industrial arXiv2607.03701 | 16 nm FinFET, Spectre; LC-VCO and two-stage op-amp; three corners with worst-corner gating; no layout, no MC (closes v9 verify item) | §9 |
| osiris, panda, falcon, ZEROSIM, spiceassistant (pre-existing) | | §1, §4 |

## 2. Claim 1: layout, parasitics, corners, mismatch, yield

| File | What it is | Plan section |
|---|---|---|
| (2019) ALIGN_Open-Source_Analog_Layout_Automation_from_the_Ground_Up DAC | ALIGN flow (invited) | §4 tools |
| (2020) ALIGN_A_System_for_Automating_Analog_Layout arXiv2008.10682 | ALIGN system paper; supported circuit classes | §4, §9 |
| (2019) MAGICAL_Toward_Fully_Automated_Analog_IC_Layout ICCAD | Second open layout tool; OSIRIS baseline | §4 |
| (2020) ParaGraph_Layout_Parasitics_Prediction_with_GNNs DAC | Parasitics from schematic graph; closest prior art to the pre-layout survival predictor | §9 verify |
| (2021) Parasitic-Aware_Analog_Sizing_with_GNNs_and_BO DATE | Liu 2021; the "2–4× convergence" figure | §9 verify |
| (2026) ParasGB_Graph_Benchmark_Parasitic_Estimation_AMS arXiv2607.23225 | 25 July 2026; public; 20 analog designs (180 nm BCD, Calibre xRC) and 6 SRAM subsets (TSMC 28 nm, StarRC) with post-layout RC labels; closed processes | §4, §9 |
| (2023) Layout-Aware_AMS_Design_Automation_Bayesian_Neural_Networks arXiv2311.17073 | Budak group; BNN treats schematic vs post-layout as multi-fidelity (stand-in for ISPD 2023) | §4 Repair loop |
| (2026) Simulation-Aware_In-Context_Policy_LLM_Analog_Layout_Refinement arXiv2608.13767 | UT Austin (Pan); GPT-5 tunes a MAGICAL-derived generator; two OTAs at 65 nm and 40 nm; 31 extractions and 11 post-layout sims per design; no corners, no MC | §7 scoop |
| (2019) Multi-fidelity_Bayesian_Optimization_Analog_Circuit_Synthesis arXiv1912.00392 | Zhang DAC 2019; the MF-BO baseline | §4 Repair loop |
| (2022) RobustAnalog_Variation-Aware_Analog_Design_Multi-task_RL arXiv2207.06412 | Corner-as-task RL; GLOVA baseline | §1, §4 |
| (2025) PPAAS_PVT_and_Pareto_Aware_Analog_Sizing_RL arXiv2507.17003 | Newest corner-aware RL sizer; summarises PVTSizing | claim 1 baselines |
| (2025) White-Box_Reasoning_LLM_Strategy_gmId_Analog_Design_PVT arXiv2508.13172 | LLM sizing with all-corner validation; mismatch excluded | §1, §7 |
| (2023) Distributionally_Robust_Circuit_Design_under_Variation_Shifts arXiv2308.08111 | Yield-aware sizing when the variation model is wrong | claims 1–2 |
| (2024) NOFIS_Normalizing_Flow_Rare_Circuit_Failure_Analysis DAC | Rare-failure importance sampling; justifies 50/200-chip two-stage MC | §11 |
| (2024) Beyond_the_Yield_Barrier_Variational_Importance_Sampling arXiv2407.00711 | Surrogate + IS yield estimation | §11 |
| (2026) Zero-Hyperparameter_Yield_Multi-Corner_Analysis_Learned_Priors arXiv2603.13092 | Multi-corner yield with learned priors | claim 1 decomposition |
| (2026) HOLMES_In-Context_Failure-Center_Localization_Yield_Estimation arXiv2608.26758 | LLM-assisted yield estimation, single designs | §11 |
| (2026) Cascaded_Batch_Bayesian_Yield_Optimization_Deep_Transfer_Learning Electronics | Yield learned from sizing; the "spread as label" approach the plan replaces | claim 2 |
| (1989) Matching_Properties_of_MOS_Transistors_Pelgrom JSSC | 1/sqrt(WL) area law behind sky130 AGAUSS terms | §4 offsets |
| (2003) Understanding_MOSFET_Mismatch_for_Analog_Design JSSC | Vt mismatch departs from pure area law at analog aspect ratios; carry all four sky130 terms in the propagation test | §4 propagation |
| (2024) CACE_Circuit_Automatic_Characterization_Engine FSiC_slides | Open corners + MC characterisation framework (no paper exists) | §4 tools |

## 3. Claims 2–3: learned circuit models and search loops

| File | What it is | Plan section |
|---|---|---|
| (2020) GCN-RL_Circuit_Designer_Transferable_Transistor_Sizing arXiv2005.00406 | First netlist-graph policy transferring across topologies | §4 model |
| (2022) Pretraining_GNN_Few-shot_Analog_Circuit_Modeling arXiv2203.15913 | Cross-topology GNN surrogate with few-shot transfer | §4 model, coverage |
| (2025) RF-Informed_GNN_Data-Efficient_Circuit_Performance_Prediction arXiv2508.16403 | Five held-out topologies: FALCON (retrained by the authors) 28.8% weighted MRE vs 1.1% with RF-informed fine-tuning; coverage dominates | §4, §7 absorption |
| (2025) Supervised_Learning_Analog_RF_Design_Benchmarks arXiv2501.11839 | Baseline table for arm A, includes log vs linear inputs | §4 arms, units |
| (2023) Learning_to_Design_Analog_Circuits_Threshold_Specifications arXiv2307.13861 | Failure-boundary data matters | §4 selection strategies |
| (2024) LaMAGIC_LM-based_Topology_Generation_Analog_ICs arXiv2407.18269 | LM-as-circuit-model; justifies excluding invented topologies | §8 |
| (2024) AnalogCoder_Analog_Design_via_Training-Free_Code_Generation arXiv2405.14918 | Source of headline pre-layout pass rates | §1 |
| (2018) Batch_BO_Multi-objective_Acquisition_Ensemble_Analog ICML | MACE; standard BO sizing baseline | §4 baselines |
| (2021) Batch-Constrained_BO_Analog_Synthesis_MACE arXiv2106.15412 | Constrained MACE | §4 baselines |
| (2026) Multi-Fidelity_Surrogate_Models_Multi-Objective_Analog_Design Electronics | Recent open MF-surrogate sizing | §4 baselines |
| (2020) Trust-Region_Method_Deep_RL_Analog_Design_Space arXiv2009.13772 | Trust-region sizing | §4 baselines |
| (2018) Learning_to_Design_Circuits_RL_Sizing arXiv1812.02734 | RL sizing precursor | §4 baselines |
| (2021) DNN-Opt_RL_Inspired_Analog_Sizing_Deep_Neural_Networks arXiv2110.00211 | DNN surrogate as critic; sample-efficiency claims | claim 3 |
| (2024) RoSE-Opt_Robust_Analog_Parameter_Optimization_Knowledge_RL arXiv2407.19150 | Width + finger-number action space, PVT-robust | §4 repair loop actions |
| (2019) Analog_Circuit_Design_Hypernetworks_Differentiable_Simulator arXiv1911.03053 | Sizing by backprop through a differentiable simulator | claim 2 sensitivity |
| (2021) Sobolev_Trained_NN_Surrogate_Models_for_Optimization CCE_Imperial-OA | Sobolev surrogates have better derivatives; advantage "especially significant" at low data and near the training boundary, but persists at large N for black-box optimisation | arm B-S |
| (2026) Joint_Surrogate_Learning_Objectives_Constraints_Sensitivities arXiv2603.20984 | Surrogate Jacobians used as sensitivities inside optimiser | arm B-S, instrument 6 |
| (2025) Exploiting_Function-Family_Structure_Analog_Optimization arXiv2512.00712 | Reports held-out R² (GP-Matérn 0.16 on bandgap at 100 samples) and iterations-to-target as separate tables; does not quantify a relation between them | claim 3 |
| (2021) How_Powerful_are_Performance_Predictors_in_NAS arXiv2104.01177 | Uses Kendall tau as the predictor metric and shows it roughly tracks NAS performance; never evaluates held-out error | claim 3 framing |
| (2025) Impact_of_Surrogate_Accuracy_on_SAEA_Performance arXiv2503.00844 | Controlled pseudo-surrogate study: accuracy helps, but for two of three management strategies the effect saturates above 0.7–0.8 | claim 3 |
| ARCS, ASTRL, AnalogFed, AnalogToBi, Diffusion hybrid, Generative engine, AMSNet, Masala-CHAI, AMSbench, surveys (pre-existing) | | §1, §8 |

## 4. Methodology instruments

| File | What it is | Instrument |
|---|---|---|
| (2016) Understanding_Intermediate_Layers_Linear_Classifier_Probes arXiv1610.01644 | Linear probes | 1 |
| (2020) Information-Theoretic_Probing_for_Linguistic_Structure arXiv2004.03061 | Use the most expressive probe | 2 |
| (2019) Designing_and_Interpreting_Probes_with_Control_Tasks arXiv1909.03368 | Control tasks / selectivity | 3 |
| (2020) Information-Theoretic_Probing_with_Minimum_Description_Length arXiv2003.12298 | MDL probes; alternative to control-task subtraction | 3 |
| (2021) Probing_Classifiers_Promises_Shortcomings_Advances arXiv2102.12452 | Probe pitfalls survey | 1–4 |
| (2020) Probing_the_Probing_Paradigm arXiv2005.01810 | Decodable is not used; motivates intervention test | 5 |
| (2020) Shortcut_Learning_in_Deep_Neural_Networks arXiv2004.07780 | Constructed shortcut sets | §4, §5 |
| (2017) Sobolev_Training_for_Neural_Networks arXiv1706.04859 | Derivative supervision | arm B-S, 6 |
| (2019) Robust_Learning_with_Jacobian_Regularization arXiv1908.02729 | Cheap Jacobian-norm regulariser for untrained directions | 6 |
| (2021) Gradient-Enhanced_Physics-Informed_Neural_Networks_gPINNs arXiv2111.02801 | Gradient supervision reaches the same error with fewer points; PINN with doubled data nearly catches up | arm B-S |
| (2022) Gradient-Enhanced_Deep_Neural_Network_Approximations arXiv2211.04226 | Same accuracy with far fewer samples; does not state that the gain shrinks with data | arm B-S |
| (2020) Gradient-Enhanced_ANNs_for_Airfoil_Shape_Design SMO | Gradient-enhanced surrogate validated by optimum match, not held-out error | arm B-S, claim 3 |
| (2020) Objective_Mismatch_in_Model-based_RL arXiv2002.04523 | Model likelihood does not track control performance | claim 3 |
| (2020) The_Value_Equivalence_Principle_for_Model-Based_RL arXiv2011.03506 | Model need only match on quantities the planner uses | §2 |
| (2018) Iterative_Value-Aware_Model_Learning NeurIPS | Decision-weighted model loss; theory only, no experiments | claim 3 |
| (2022) Value_Gradient_Weighted_Model-Based_RL_VaGraM arXiv2204.01464 | Sensitivity-weighted model error | claim 3, arm B-S |
| (2017) What_Uncertainties_Do_We_Need_in_Bayesian_Deep_Learning arXiv1703.04977 | Heteroscedastic NLL head | arm B-het |
| (2022) Pitfalls_of_Heteroscedastic_Uncertainty_Estimation_NNs arXiv2203.09168 | NLL variance heads can fail to fit the mean | arm B-het, §5 |
| (2021) Pairwise_Difference_Regression_PADRE JCIM | Pairwise difference regression | arm B |
| (2024) Extrapolation_Is_Not_the_Same_as_Interpolation MachineLearning | Pairwise form extrapolates | arm B, §5 |
| (2022) Beyond_Neural_Scaling_Laws_Data_Pruning_Coverage arXiv2206.14486 | Which examples matters more than how many; best rule flips with data size | coverage vs quantity |
| (2005) Active_Learning_for_Identifying_Function_Threshold_Boundaries NeurIPS | Boundary-sampling acquisition (straddle) | selection strategy 3 |
| (2018) Lightweight_Probabilistic_Deep_Networks_Uncertainty_Propagation arXiv1805.11327 | Analytic uncertainty propagation through a network | 7 |
| (2015) Sloppiness_and_Emergent_Theories_Parameter_Identifiability arXiv1501.07668 | Why 20–40 device parameters are not identifiable from a dozen outputs | §4 offsets-as-input |
| Why NNs cannot extrapolate physical laws arXiv2510.04102 (pre-existing) | | §5 |

## 5. Gated bridge and CIM tile; Chai group papers

| File | What it is | Plan section |
|---|---|---|
| (1998) McAndrew_Statistical_Circuit_Modeling_BPV SISPAD | Backward propagation of variance | §6 bridge, §10 Q2 |
| (2021) Variability-Aware_Compact_Model_Circuit_Performance_DTCO arXiv2109.00849 | LER/MGG variability in BSIM-CMG propagated to RO and SRAM metrics by statistical SPICE runs, not sensitivities | §6 |
| (2022) Kuthe_OpenVAF_Verilog-A_Compiler MOS-AK_presentation | OpenVAF/OSDI (no peer-reviewed paper exists) | §6 bridge |
| (2024) Burmen_Free_Software_Compact_Modelling_Verilog-A_OpenVAF_OSDI InfMIDEM | Survey of open Verilog-A compilers and simulator support | §6 bridge |
| (2021) Kam_Deep_Learning_Assisted_Compact_Modeling_Nanoscale_Transistor arXiv2107.06167 | Explicit gm/gds loss terms | §9 derivative-loss lineage |
| (2025) Embedding-Enhanced_Probabilistic_Modeling_FeFET_Variability arXiv2508.02737 | NN compact model with device-to-device variability | §6 bridge |
| (2025) Defect-Aware_Compact_Model_Ferroelectric_nvCap_Circuit_Co-Design arXiv2511.21267 | Measured-calibrated Verilog-A model with D2D variation; template deliverable | §6 |
| (2024) Synaptogen_Generative_Device_Model_Neuromorphic_Circuit_Design arXiv2404.06344 | Verilog-A ReRAM model with measured C2C + D2D statistics; sky130 substitute | §6 tile, §9 |
| (2017) Compact_Verilog-A_ReRAM_Switching_Model arXiv1703.01167 | Deterministic ReRAM baseline | §6 tile |
| (2022) Variability-aware_Memristive_Crossbars_Tutorial arXiv2204.09543 | How variation, IR drop, sneak paths enter crossbar accuracy | §6 tile |
| (2020) DNN_NeuroSim_V2 arXiv2003.06471; (2025) NeuroSim_V1.5 arXiv2505.02314 | NeuroSim primary papers; device-expert vs circuit-expert noise modes | §6, §9 |
| (2022) CrossSim_Inference_Manual_v2.0 Sandia_OSTI; (2021) Xiao_Accuracy_of_Analog_NN_Inference_Accelerators_CrossSim arXiv2109.01262 | CrossSim documentation and accuracy study | §6, §9 |
| (2021) IBM_AIHWKit arXiv2104.02184; (2023) Using_IBM_AIHWKit arXiv2307.09357 | AIHWKit; algorithmic level, not circuit level | §6 tile |
| (2023) Material_to_System_Benchmarking_CMOS-integrated_RRAM SciRep | Measured 1T1R arrays into AIHWKit | §6 tile |
| (2026) Mannocci_Ielmini_High_Precision_Analog_In-Memory_Computing npjUnconvComput | Review of precision limits in analog CIM | §6 tile |
| (2025) ADC_Noise_Reference_Tuning_RRAM_CIM arXiv2502.05948 | Silicon-measured ADC/readout noise | §6 tile peripherals |
| (2021) Sensing_Circuit_Design_Techniques_RRAM_Advanced_CMOS Micromachines | Sense-amplifier offset under mismatch | §6 tile peripherals |
| (2024) ASiM_SRAM_Analog_CIM_Accuracy_Simulation_Framework arXiv2411.11022 | Open CIM accuracy simulator with ADC and cell mismatch | §6 tile |
| (2026) ChatNeuroSim_LLM_Agent_CIM_Accelerator_Deployment arXiv2603.08745 | LLM agent driving NeuroSim | §4 repair loop, §6 |
| (2019) ML-Assisted_DTCO_Modeling_Framework arXiv1904.10269 | Origin of NN surrogates in DTCO | §6 |
| (2024) IMC_Meets_SNN_Device-Circuit-System-Algorithm_Co-design arXiv2408.12767 | Cross-layer co-design framing | §10 Q1 |
| (2026) Wang_Chai_Synaptic_Transistors_In-situ_Spiking_RL_Eligibility_Trace NatCommun | Chai group; the device the bridge would most plausibly model | §10 |
| (2026) Chai_Thousand-state_Optoelectronic_Memory NatCommun | Multi-level device from the group | §10 Q2 |
| (2026) Chai_coauthor_Wafer-scale_HfO2_2D_MoS2_Transistors NatCommun | Wafer-scale device population statistics | §10 Q2 |
| (2020) Zhou_Chai_Near-sensor_and_In-sensor_Computing NatElectron_PolyU-IRA | Group's defining perspective | §10 Q1 |
| Compact-model papers (pre-existing: BSIM-NN, Novkin, Kang, KAN, NeuroSPICE, DDNet, iPREFER, GAA ANN, PINN, NN-VS, GaN HEMT, self-heating, CDRPE, derivative-free, EEspice, Li et al.) | | §6 bridge |

## Not found open-access (download manually or cite from abstract)

- Learn-by-Compare, Wang/Somayaji/Li, DAC 2024, 10.1145/3649329.3657342 (listed as CC-BY at ACM; curl blocked).
- Budak et al., ISPD 2023, 10.1145/3569052.3578929.
- Hammoud et al., MLCAD 2024, 10.1145/3670474.3685971; ICCAD 2024, 10.1145/3676536.3676823 (OpenFASoC/glayout).
- PVTSizing, Kong et al., DAC 2024, 10.1145/3649329.3661850.
- Kinget, JSSC 2005, device mismatch tradeoffs.
- Wang et al. DAC 2017 and Yin et al. DAC 2022 yield optimisation; WEIBO DAC 2018.
- BAG2 (CICC 2018), LAYGO, OpenFASoC base paper (VLSI-SoC 2020).
- Nix and Weigend 1994 (replaced by Kendall and Gal 2017).
- Wang, Wan, Ma, Chai, Nat. Nanotechnol. 2024, 10.1038/s41565-024-01665-7; Chai et al. Nat. Protoc. 2025.
- Bengel et al. JART VCM, TCAS-I 2020; Guan/Yu/Wong Stanford RRAM model, EDL 2012 (Verilog-A on nanoHUB).
- VerilogAE, JEDS 2020 (CC-BY, IEEE blocks curl).
- No paper validates SkyWater 130 nm mismatch/Monte Carlo models; only open_pdks files, the VLSIDA tutorial and forum threads exist.

## Findings that bear on the plan

- No paper through September 2026 measures a population of AI-sized analog designs after extraction, corners or Monte Carlo. Nearest are per-design: PANDA, arXiv 2608.13767 (Pan group), SABLE, White-Box Reasoning. AutoSizer's repo (last commit 26 May 2026) still reports no post-layout numbers. The §7 scoop risk stands; the Pan group is the most plausible source.
- The statement in arXiv 2604.07387 that "no prior work provides quantitative analysis of how prediction accuracy relates to convergence" is made in the context of LLM-based sizing. Outside circuits, arXiv 2503.00844 is a controlled study of surrogate accuracy against optimiser performance, and the model-based RL line (objective mismatch 2020, value equivalence 2020, VaGraM 2022) makes the same point empirically. No prior work measures per-property response fidelity or Jacobian agreement with the simulator. State the gap that narrowly.
- Tsay 2021 states that the Sobolev-training advantage is "especially significant" at low data volume and near the training boundary, and that it persists at large N for black-box optimisation. gPINN and Feng and Zeng show sample efficiency but do not state a shrinking gain. Report arm B-S versus B at each dataset size, not pooled.
- Drennan and McAndrew 2003: "Vt mismatch does not follow a simplistic 1/sqrt(area) law, especially for wide/short and narrow/long devices". The propagation test must carry all four sky130 terms (vth0, toxe, voff, nfactor).
- Explicit derivative loss in NN compact models, verified against the loss equations: Tung/Hu 2023 and BSIM-NN 2025 (gm, gds and their first derivatives, charge second derivatives), the 2024 self-heating model (by reference only), Novkin/Amrouch dual-network and KAN papers (gm, gds, second derivatives), Kam 2021 (gm, gds first order). No derivative terms in the GAA ANN model (MSE plus L2) or NN-VS (explicitly none). The three PINN papers use PDE or DAE residuals, not conductance targets. The KAN paper reports faulty derivatives despite the derivative terms in its loss.
- NeuroSim, CrossSim and AIHWKit do not ingest Verilog-A. A device model reaches the tile only by running it in ngspice Monte Carlo and feeding the resulting statistics to NeuroSim's circuit-expert mode or CrossSim's custom error function.
- sky130's ReRAM primitive (sky130_fd_pr_reram__reram_cell.va) is deterministic with 17 fixed parameters and no statistical hooks. Synaptogen (arXiv 2404.06344) is the drop-in substitute.
- ParasGB (arXiv 2607.23225) should be added to the §9 verify list beside Liu 2021, Budak 2023 and ParaGraph.
- Cross-topology surrogate error is already reported for FALCON on five held-out topologies: 28.8% weighted MRE when retrained by the authors of arXiv 2508.16403, against 1.1% with their method. Held-out-topology tests are now a cheap add-on for a systems group. Useful for §7 absorption.
- Gao et al. 2024 publish no code (checked PDF and author page). The claim 3 baseline must be re-implemented from the paper.
- No public count exists of OpenFASoC op-amp variants measured in silicon; the tapeout README names op-amp tiles but no measurements. Drop the verify item.
- FALCON's primary paper confirms 45 nm and a fixed 30 GHz simulation frequency. EXPLORE reports 65% success at tolerance 0.01 on a 6-component power-converter benchmark against 12% one-shot and 33% sample-and-filter.
- AutoSizer publishes no per-circuit ALIGN list; the README says "simple OTAs and amplifiers". Latest commit 26 May 2026; no post-layout or Monte Carlo results anywhere.
- No 2025–26 LLM sizing paper uses a trained surrogate to rank proposals before SPICE. The plan's ranker design appears unoccupied.
