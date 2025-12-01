# Documentation Index

## Overview

This index provides a comprehensive guide to all documentation for the ECMR vs C-MORL carbon-aware workload scheduling research project.

**Created:** 2025-11-24
**Status:** Complete ✅

---

## Quick Start

### I want to...

**...run a quick test (5 minutes)**
→ See: [RUNNING_TESTING_GUIDE.md → Quick Test](#quick-reference)
```bash
# Start gateway
pkill -9 -f "Py4JGatewayEnhanced" && \
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 & sleep 5

# Run ECMR
python3 ecmr_heterogeneous_integration.py --hours 2 --vms-per-hour 5
```

**...understand the code**
→ See: [CODE_REFERENCE.md → Architecture Overview](#code-reference)

**...run the full comparison**
→ See: [RUNNING_TESTING_GUIDE.md → Running Complete Comparison](#running-complete-comparison)
```bash
python3 run_comparison.py --hours 24 --vms-per-hour 10 --cmorl-timesteps 50000
```

**...interpret results**
→ See: [TEST_SCENARIOS.md → Result Interpretation](#result-interpretation)

---

## Core Documentation Files

### 1. RUNNING_TESTING_GUIDE.md
**Purpose:** Step-by-step instructions for running all tests

**Contents:**
- Prerequisites and environment setup
- Building CloudSim backend
- Running ECMR baseline
- Training C-MORL agent
- Executing complete comparisons
- Troubleshooting common issues
- Quick reference commands

**Target Audience:** Researchers, developers, students running experiments

**Key Sections:**
- [Prerequisites](RUNNING_TESTING_GUIDE.md#prerequisites)
- [Environment Setup](RUNNING_TESTING_GUIDE.md#environment-setup)
- [Running ECMR](RUNNING_TESTING_GUIDE.md#running-ecmr-baseline)
- [Running C-MORL](RUNNING_TESTING_GUIDE.md#running-c-morl)
- [Running Comparison](RUNNING_TESTING_GUIDE.md#running-complete-comparison)
- [Troubleshooting](RUNNING_TESTING_GUIDE.md#troubleshooting)

**When to Use:**
- First time setup
- Running any experiments
- Debugging runtime issues
- Learning the workflow

---

### 2. CODE_REFERENCE.md
**Purpose:** Comprehensive code documentation and implementation details

**Contents:**
- System architecture overview
- ECMR implementation (633 lines)
- C-MORL implementation (2200+ lines)
- CloudSim integration
- Key algorithms and data structures
- Configuration parameters

**Target Audience:** Developers, code reviewers, technical audience

**Key Sections:**
- [Architecture Overview](CODE_REFERENCE.md#architecture-overview)
- [ECMR Implementation](CODE_REFERENCE.md#ecmr-implementation)
  - DatacenterState class
  - ECMRHeterogeneousScheduler algorithm
  - Scoring function (Lines 144-209)
- [C-MORL Implementation](CODE_REFERENCE.md#c-morl-implementation)
  - CMORLEnvironment (132-dim state space)
  - CMORLAgent (multi-objective PPO)
  - Two-stage training pipeline
- [CloudSim Integration](CODE_REFERENCE.md#cloudsim-integration)
  - Py4J bridge
  - Java gateway methods
- [Utility Modules](CODE_REFERENCE.md#utility-modules)

**When to Use:**
- Understanding implementation details
- Modifying algorithms
- Debugging complex issues
- Code reviews
- Writing research papers (citing specific algorithms)

---

### 3. TEST_SCENARIOS.md
**Purpose:** Test configurations, expected results, and validation criteria

**Contents:**
- Test configuration matrix (5 modes)
- ECMR test scenarios (5 scenarios)
- C-MORL test scenarios (5 scenarios)
- Comparison test scenarios (3 scenarios)
- Validation criteria
- Expected results with ranges
- Result interpretation guide
- Troubleshooting failed tests

**Target Audience:** QA testers, researchers validating results

**Key Sections:**
- [Test Configuration Matrix](TEST_SCENARIOS.md#test-configuration-matrix)
- [ECMR Scenarios](TEST_SCENARIOS.md#ecmr-test-scenarios)
  - E1: Smoke test (1 hour, 5 VMs)
  - E2: Standard daily cycle (24 hours, 240 VMs)
  - E3: Renewable priority test
  - E4: Carbon spike test
  - E5: Stress test (1200 VMs)
- [C-MORL Scenarios](TEST_SCENARIOS.md#c-morl-test-scenarios)
  - C1: Quick training (10 mins)
  - C2: Standard training (3-5 hours)
  - C3: Full training (8-12 hours)
  - C4: Preference sensitivity
  - C5: Convergence test
- [Comparison Scenarios](TEST_SCENARIOS.md#comparison-test-scenarios)
  - CP1: Quick (15 mins)
  - CP2: Standard (4-6 hours)
  - CP3: Weekly (24-30 hours)
- [Expected Results](TEST_SCENARIOS.md#expected-results)
- [Validation Criteria](TEST_SCENARIOS.md#validation-criteria)

**When to Use:**
- Planning experiments
- Validating results
- Comparing performance
- Identifying test failures
- Writing methodology sections

---

### 4. DOCUMENTATION_INDEX.md (This File)
**Purpose:** Navigation guide for all documentation

**Contents:**
- Quick start references
- File descriptions
- Navigation map
- Document dependencies

**Target Audience:** All users (entry point)

**When to Use:**
- First time exploring the project
- Finding specific information
- Understanding documentation structure

---

## Supporting Documentation

### 5. COMPARISON_FRAMEWORK_READY.md
**Purpose:** Status of comparison framework implementation

**Contents:**
- Framework completion status
- Unified metrics output format
- Configuration verification
- Usage examples
- Test run results

**Status:** ✅ Complete and tested

**When to Use:**
- Verifying comparison framework works
- Understanding unified metrics
- Checking configuration parity

---

### 6. COMPARISON_SETUP.md
**Purpose:** Detailed comparison framework documentation

**Contents:**
- Framework architecture
- Configuration details
- File descriptions
- Usage instructions

**When to Use:**
- Deep dive into comparison methodology
- Understanding metric calculations
- Framework development

---

### 7. Existing Research Documentation

These documents contain research background and implementation history:

- `COMPLETE_INTEGRATION_GUIDE.md` - Original integration guide
- `ECMR_CLOUDSIM_IMPLEMENTATION_GUIDE.md` - ECMR implementation details
- `HETEROGENEOUS_INFRASTRUCTURE.md` - Infrastructure specifications
- `INFRASTRUCTURE_VERIFICATION.md` - Verification process
- `PROFESSOR_SUMMARY.md` - Research summary for advisor
- `VERIFICATION_INDEX.md` - Verification documentation index
- `RESULTS_VERIFICATION_AND_AUTHENTICITY.md` - Result validation
- `DATACENTER_TYPE_REVISION.md` - DC type implementation notes
- `DC_TYPE_ANALYSIS.md` - DC type analysis
- `DC_TYPE_IMPLEMENTATION_COMPLETE.md` - DC type implementation status
- `CMORL_RETRAIN_STATUS.md` - C-MORL retraining status
- `FULL_COMPARISON_STATUS.md` - Full comparison status
- `INCREMENTAL_TEST_RESULTS.md` - Incremental test results

---

## Documentation Dependency Map

```
DOCUMENTATION_INDEX.md (START HERE)
    ├── RUNNING_TESTING_GUIDE.md (How to run)
    │   ├── Prerequisites & Setup
    │   ├── ECMR Execution → ecmr_heterogeneous_integration.py
    │   ├── C-MORL Training → train_cmorl.py
    │   └── Comparison → run_comparison.py
    │
    ├── CODE_REFERENCE.md (What the code does)
    │   ├── ECMR Algorithm → ecmr_heterogeneous_integration.py
    │   ├── C-MORL Algorithm → cmorl_*.py files
    │   ├── CloudSim Bridge → Py4JGatewayEnhanced.java
    │   └── Utilities → unified_metrics.py, pareto_utils.py
    │
    └── TEST_SCENARIOS.md (Expected results)
        ├── Test Configurations
        ├── Expected Outputs
        ├── Validation Criteria
        └── Interpretation Guide
```

---

## Documentation for Different User Roles

### For Students / First-Time Users

**Start Here:**
1. Read this index (DOCUMENTATION_INDEX.md)
2. Follow [RUNNING_TESTING_GUIDE.md → Prerequisites](RUNNING_TESTING_GUIDE.md#prerequisites)
3. Run smoke test [TEST_SCENARIOS.md → Scenario E1](TEST_SCENARIOS.md#scenario-e1-smoke-test-sanity-check)
4. Understand results [TEST_SCENARIOS.md → Result Interpretation](TEST_SCENARIOS.md#result-interpretation)

**Focus On:**
- Running tests successfully
- Understanding basic concepts
- Interpreting output

**Skip For Now:**
- Code implementation details
- Algorithm internals
- Advanced scenarios

---

### For Researchers / Paper Authors

**Start Here:**
1. Review [CODE_REFERENCE.md → Architecture](CODE_REFERENCE.md#architecture-overview)
2. Understand algorithms:
   - [ECMR Algorithm](CODE_REFERENCE.md#ecmrheterogeneousscheduler-lines-90-210)
   - [C-MORL Algorithm](CODE_REFERENCE.md#c-morl-implementation)
3. Run standard comparison [TEST_SCENARIOS.md → CP2](TEST_SCENARIOS.md#scenario-cp2-standard-comparison-daily-cycle)
4. Analyze results [TEST_SCENARIOS.md → Expected Results](TEST_SCENARIOS.md#expected-results)

**Focus On:**
- Algorithm correctness
- Statistical validity
- Result interpretation
- Comparison methodology

**Key Sections:**
- ECMR scoring function (CODE_REFERENCE.md:144-209)
- C-MORL training pipeline (CODE_REFERENCE.md:231-428)
- Validation criteria (TEST_SCENARIOS.md)
- Expected performance metrics

---

### For Developers / Contributors

**Start Here:**
1. Study [CODE_REFERENCE.md](CODE_REFERENCE.md) thoroughly
2. Review architecture and data flow
3. Understand key classes and methods
4. Run all test scenarios [TEST_SCENARIOS.md](TEST_SCENARIOS.md)
5. Modify code and verify results

**Focus On:**
- Code structure and organization
- Algorithm implementation details
- Integration points (Py4J bridge)
- Testing and validation

**Key Files to Study:**
- `ecmr_heterogeneous_integration.py` (633 lines)
- `cmorl_environment.py` (670 lines)
- `cmorl_agent.py` (395 lines)
- `train_cmorl.py` (515 lines)
- `unified_metrics.py` (244 lines)

---

### For Reviewers / Advisors

**Start Here:**
1. Read [PROFESSOR_SUMMARY.md](PROFESSOR_SUMMARY.md) for research overview
2. Review [VERIFICATION_INDEX.md](VERIFICATION_INDEX.md) for authenticity
3. Check [COMPARISON_FRAMEWORK_READY.md](COMPARISON_FRAMEWORK_READY.md) for status
4. Examine [TEST_SCENARIOS.md → Validation Criteria](TEST_SCENARIOS.md#validation-criteria)

**Focus On:**
- Research validity
- Methodology soundness
- Result authenticity
- Fair comparison

**Key Documents:**
- PROFESSOR_SUMMARY.md (research overview)
- RESULTS_VERIFICATION_AND_AUTHENTICITY.md (validation)
- TEST_SCENARIOS.md (methodology)
- COMPARISON_FRAMEWORK_READY.md (fairness)

---

## Common Tasks and Where to Find Them

### Setup and Installation

| Task | Document | Section |
|------|----------|---------|
| Install prerequisites | RUNNING_TESTING_GUIDE.md | [Prerequisites](#prerequisites) |
| Build CloudSim | RUNNING_TESTING_GUIDE.md | [Environment Setup](#environment-setup) |
| Verify dataset | RUNNING_TESTING_GUIDE.md | [Step 2: Verify Dataset](#step-2-verify-dataset) |
| Start gateway | RUNNING_TESTING_GUIDE.md | [Step 1: Start Java Gateway](#step-1-start-java-gateway) |

### Running Experiments

| Task | Document | Section |
|------|----------|---------|
| Quick ECMR test | RUNNING_TESTING_GUIDE.md | [Quick Test (2 hours, 10 VMs)](#quick-test-2-hours-10-vms) |
| Full ECMR test | RUNNING_TESTING_GUIDE.md | [Full Test (24 hours, 240 VMs)](#full-test-24-hours-240-vms) |
| Train C-MORL | RUNNING_TESTING_GUIDE.md | [Running C-MORL](#running-c-morl) |
| Run comparison | RUNNING_TESTING_GUIDE.md | [Running Complete Comparison](#running-complete-comparison) |

### Understanding Code

| Task | Document | Section |
|------|----------|---------|
| System architecture | CODE_REFERENCE.md | [Architecture Overview](#architecture-overview) |
| ECMR algorithm | CODE_REFERENCE.md | [ECMR Implementation](#ecmr-implementation) |
| C-MORL algorithm | CODE_REFERENCE.md | [C-MORL Implementation](#c-morl-implementation) |
| State space | CODE_REFERENCE.md | [CMORLEnvironment](#file-cmorl_environmentpy-670-lines) |
| Reward function | CODE_REFERENCE.md | [_calculate_rewards()](#4-_calculate_rewards-lines-452-550) |
| Pareto front | CODE_REFERENCE.md | [pareto_utils.py](#file-pareto_utilspy-380-lines) |

### Validating Results

| Task | Document | Section |
|------|----------|---------|
| Expected ECMR results | TEST_SCENARIOS.md | [ECMR Baseline Performance](#ecmr-baseline-performance) |
| Expected C-MORL results | TEST_SCENARIOS.md | [C-MORL Performance](#c-morl-performance) |
| Validation criteria | TEST_SCENARIOS.md | [Validation Criteria](#validation-criteria) |
| Interpreting output | TEST_SCENARIOS.md | [Result Interpretation](#result-interpretation) |
| Troubleshooting | RUNNING_TESTING_GUIDE.md | [Troubleshooting](#troubleshooting) |

### Research and Writing

| Task | Document | Section |
|------|----------|---------|
| Algorithm description | CODE_REFERENCE.md | ECMR/C-MORL sections |
| Methodology | TEST_SCENARIOS.md | Test scenarios |
| Results table | TEST_SCENARIOS.md | [Expected Results](#expected-results) |
| Comparison metrics | COMPARISON_FRAMEWORK_READY.md | [Unified Metrics](#-unified-metrics-output-format) |
| Authenticity proof | RESULTS_VERIFICATION_AND_AUTHENTICITY.md | All sections |

---

## File Size and Complexity Reference

| Document | Size | Lines | Complexity | Read Time |
|----------|------|-------|------------|-----------|
| DOCUMENTATION_INDEX.md | ~15 KB | 500 | Low | 10 min |
| RUNNING_TESTING_GUIDE.md | ~45 KB | 950 | Medium | 30 min |
| CODE_REFERENCE.md | ~60 KB | 1100 | High | 45 min |
| TEST_SCENARIOS.md | ~55 KB | 1050 | High | 40 min |
| COMPARISON_FRAMEWORK_READY.md | ~20 KB | 412 | Low | 15 min |

**Total New Documentation:** ~195 KB, ~4000 lines

---

## Key Takeaways

### Research Contributions

1. **ECMR Baseline:**
   - Carbon-aware greedy scheduling
   - Multi-objective scoring (carbon, renewable, latency)
   - Heterogeneous infrastructure (3 server types, 5 DCs)
   - Real carbon intensity data integration

2. **C-MORL Algorithm:**
   - Multi-objective reinforcement learning
   - Two-stage Pareto optimization
   - 132-dimensional state space
   - Preference-based scalarization

3. **Fair Comparison:**
   - Identical infrastructure
   - Unified metrics (M1-M5)
   - Statistical validation
   - Trade-off analysis

### Expected Outcomes

**C-MORL vs ECMR Improvements:**
- Energy: 8-15% reduction
- Carbon: 6-12% reduction
- Latency: 8-14% reduction
- Pareto front: 15-25 solutions

**ECMR Advantages:**
- 10-50× faster execution
- Deterministic behavior
- Easier to understand
- No hyperparameter tuning

---

## Updates and Maintenance

### Version History

- **v1.0** (2025-11-24): Initial comprehensive documentation
  - RUNNING_TESTING_GUIDE.md created
  - CODE_REFERENCE.md created
  - TEST_SCENARIOS.md created
  - DOCUMENTATION_INDEX.md created

### Future Updates

When code changes, update:
1. CODE_REFERENCE.md (if algorithm/architecture changes)
2. RUNNING_TESTING_GUIDE.md (if commands/workflow changes)
3. TEST_SCENARIOS.md (if expected results change)

### Contact

For questions or issues:
1. Check [RUNNING_TESTING_GUIDE.md → Troubleshooting](RUNNING_TESTING_GUIDE.md#troubleshooting)
2. Review [TEST_SCENARIOS.md → Troubleshooting Failed Tests](TEST_SCENARIOS.md#troubleshooting-failed-tests)
3. Examine error logs in `gateway.log` or script output

---

## Summary

This documentation suite provides:

✅ **Complete coverage** of ECMR and C-MORL implementations
✅ **Step-by-step instructions** for all experiments
✅ **Comprehensive reference** for all code components
✅ **Detailed test scenarios** with expected results
✅ **Validation criteria** for research quality
✅ **Troubleshooting guides** for common issues

**Total Documentation: 4+ comprehensive guides, 195+ KB, 4000+ lines**

**For most users, start with:**
1. This index (DOCUMENTATION_INDEX.md)
2. Running guide (RUNNING_TESTING_GUIDE.md)
3. Test scenarios (TEST_SCENARIOS.md)

**For deep technical understanding:**
4. Code reference (CODE_REFERENCE.md)

---

**Last Updated:** 2025-11-24
**Status:** Complete and ready for use ✅
