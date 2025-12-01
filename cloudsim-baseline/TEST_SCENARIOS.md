# Test Scenarios and Expected Results

## Overview

This document describes test scenarios for ECMR and C-MORL algorithms, expected results, validation criteria, and interpretation guidelines.

---

## Table of Contents

1. [Test Configuration Matrix](#test-configuration-matrix)
2. [ECMR Test Scenarios](#ecmr-test-scenarios)
3. [C-MORL Test Scenarios](#c-morl-test-scenarios)
4. [Comparison Test Scenarios](#comparison-test-scenarios)
5. [Validation Criteria](#validation-criteria)
6. [Expected Results](#expected-results)
7. [Result Interpretation](#result-interpretation)

---

## Test Configuration Matrix

### Test Modes

| Mode | Duration | VMs/Hour | Total VMs | Purpose | Runtime |
|------|----------|----------|-----------|---------|---------|
| **Smoke Test** | 1 hour | 5 | 5 | Quick sanity check | ~1 min |
| **Quick Test** | 2 hours | 5 | 10 | Rapid validation | ~2-3 min |
| **Standard Test** | 24 hours | 10 | 240 | Daily cycle evaluation | ~15-20 min |
| **Extended Test** | 168 hours | 10 | 1680 | Weekly cycle evaluation | ~1-2 hours |
| **Stress Test** | 24 hours | 50 | 1200 | High load testing | ~30-45 min |

### Infrastructure Configuration

**Datacenters (Identical for ECMR and C-MORL):**

| ID | Location | Country | PUE | Servers | Total Capacity |
|----|----------|---------|-----|---------|----------------|
| DC_SPAIN | Madrid | spain | 1.25 | 120 | 6720 cores, 11520 GB RAM |
| DC_NETHERLANDS | Amsterdam | netherlands | 1.20 | 120 | 6720 cores, 11520 GB RAM |
| DC_FRANCE | Paris | france | 1.15 | 120 | 6720 cores, 11520 GB RAM |
| DC_ITALY | Milan | italy | 1.20 | 120 | 6720 cores, 11520 GB RAM |
| DC_SWEDEN | Stockholm | sweden | 1.10 | 120 | 6720 cores, 11520 GB RAM |

**Server Mix per Datacenter:**
- 40 × Huawei RH2285 V2 (16 cores, 24 GB RAM, 58-189W)
- 40 × Huawei RH2288H V3 (40 cores, 64 GB RAM, 95-315W)
- 40 × Lenovo SR655 V3 (96 cores, 192 GB RAM, 150-520W)

**VM Distribution:**
- 40% Small (1 core, 2 GB RAM)
- 30% Medium (2 cores, 4 GB RAM)
- 20% Large (4 cores, 8 GB RAM)
- 10% XLarge (8 cores, 16 GB RAM)

---

## ECMR Test Scenarios

### Scenario E1: Smoke Test (Sanity Check)

**Objective:** Verify basic ECMR functionality

**Configuration:**
```bash
python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 1 \
  --vms-per-hour 5
```

**Expected Output:**
```
[1/6] Loading carbon intensity data... ✓
[2/6] Connecting to Java gateway... ✓
[3/6] Initializing CloudSim simulation... ✓
[4/6] Creating heterogeneous datacenters... ✓
[5/6] Running simulation (1 hours, 5 VMs/hour)... ✓
[6/6] Running CloudSim simulation... ✓

SIMULATION RESULTS
  Total IT Energy: 0.5-2.0 kWh
  Successful VMs: 5/5 (100%)
  Total Carbon: 50-300 gCO2
```

**Validation Criteria:**
- ✅ All 6 initialization steps complete
- ✅ 5 VMs placed successfully
- ✅ Success rate ≥ 95%
- ✅ Energy consumption > 0
- ✅ All 5 datacenters created

**Runtime:** ~60 seconds

---

### Scenario E2: Standard Daily Cycle

**Objective:** Evaluate ECMR performance over 24-hour carbon intensity variations

**Configuration:**
```bash
python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 24 \
  --vms-per-hour 10
```

**Expected Output:**
```
SIMULATION RESULTS

OVERALL STATISTICS
  Total IT Energy: 80-120 kWh
  Total Facility Energy: 95-142 kWh
  Average PUE: 1.15-1.20
  Successful VMs: 235-240
  Success Rate: 98-100%

CARBON & RENEWABLE METRICS
  Total Carbon Emissions: 12000-20000 gCO2
  Weighted Avg Carbon Intensity: 120-180 gCO2/kWh
  Weighted Avg Renewable %: 55-75%

GREEN DATACENTER UTILIZATION
  Green DC (DG) VMs: 160-200 (67-83%)
  Brown DC (DB) VMs: 40-80 (17-33%)
  Green DC Utilization Score: 0.67-0.83
```

**Validation Criteria:**
- ✅ Success rate ≥ 98%
- ✅ Energy per VM: 0.35-0.60 kWh/VM
- ✅ Carbon intensity < Random baseline (avg ~180 gCO2/kWh)
- ✅ Green DC utilization ≥ 65%
- ✅ All datacenters utilized

**Key Metrics:**

| Metric | Target | Acceptable Range |
|--------|--------|------------------|
| M1: Energy per VM | 0.40-0.50 kWh | 0.35-0.60 kWh |
| M2: Success Rate | 99-100% | 98-100% |
| M3: Avg Latency | 6-10 ms | 5-15 ms |
| M4: Total Carbon | 14000-17000 gCO2 | 12000-20000 gCO2 |
| M5: Green DC % | 70-80% | 65-85% |

**Runtime:** ~15-20 minutes

---

### Scenario E3: Renewable Energy Priority Test

**Objective:** Test ECMR behavior during high renewable availability

**Configuration:**
```bash
# Use dataset filtered for high renewable hours (>70%)
python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 24 \
  --vms-per-hour 10
```

**Expected Behavior:**
- Higher placement ratio in Sweden (highest renewable %)
- Lower carbon intensity (110-150 gCO2/kWh)
- Green DC utilization > 80%

**Validation:**
- ✅ DC_STOCKHOLM (Sweden) gets most VMs
- ✅ Carbon emissions 15-30% lower than baseline
- ✅ Renewable % > 65%

---

### Scenario E4: Carbon Intensity Spike Test

**Objective:** Evaluate ECMR adaptation to sudden carbon intensity changes

**Expected Behavior:**
- Algorithm shifts placements away from high-carbon DCs
- Carbon emissions increase moderately (better than random)
- Success rate remains stable

**Validation:**
- ✅ Placement shifts to lower-carbon DCs within 1 hour
- ✅ Carbon increase < 50% of worst-case
- ✅ Success rate ≥ 95%

---

### Scenario E5: Stress Test (High Load)

**Objective:** Test ECMR under high VM request load

**Configuration:**
```bash
python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 24 \
  --vms-per-hour 50
```

**Expected Output:**
```
Total VMs: 1200
Successful VMs: 1100-1180
Success Rate: 92-98%
Total Energy: 450-550 kWh
```

**Expected Behavior:**
- Some VM failures due to resource exhaustion
- Even distribution across datacenters
- Higher CPU/RAM utilization (70-90%)

**Validation:**
- ✅ Success rate ≥ 90%
- ✅ No single DC overwhelmed (>30% of load)
- ✅ Energy consumption scales linearly

**Runtime:** ~30-45 minutes

---

## C-MORL Test Scenarios

### Scenario C1: Quick Training Test

**Objective:** Verify C-MORL training pipeline works end-to-end

**Configuration:**
```bash
python3 train_cmorl.py \
  --simulation-hours 2 \
  --vms-per-hour 5 \
  --n-policies 3 \
  --timesteps 1000 \
  --n-extend 2 \
  --output-dir cmorl_quick_test \
  --seed 42
```

**Expected Output:**
```
================================================================================
STAGE 1: PARETO INITIALIZATION
================================================================================
Training 3 policies with 1000 timesteps each

--- Training Policy 1/3 ---
Preference: [0.45, 0.32, 0.23]
Episode 10: Return E=-0.523, C=-0.612, L=-0.134
Training complete: 1000 timesteps, 50 episodes

--- Training Policy 2/3 ---
...

✓ Stage 1 complete
Pareto Front Size: 3

================================================================================
STAGE 2: PARETO EXTENSION
================================================================================
Selecting 2 sparse solutions for extension

--- Extending Solution 1/2 ---
  Optimizing Energy...
  Optimizing Carbon...
  Optimizing Latency...

✓ Stage 2 complete
Pareto Front Size: 9 (3 Stage 1 + 6 Stage 2)

Final Results:
  Pareto Front Size: 9
  Hypervolume: 0.65-0.75
  Expected Utility: 0.55-0.65
```

**Validation Criteria:**
- ✅ Stage 1 completes with 3 policies
- ✅ Stage 2 extends to 9 total policies (3 + 2×3)
- ✅ Pareto front size ≥ 7 (some may be dominated)
- ✅ Hypervolume > 0.6
- ✅ No crashes or NaN values

**Runtime:** ~10-15 minutes

---

### Scenario C2: Standard Training (Research Quality)

**Objective:** Train C-MORL with sufficient timesteps for meaningful results

**Configuration:**
```bash
python3 train_cmorl.py \
  --simulation-hours 24 \
  --vms-per-hour 10 \
  --n-policies 6 \
  --timesteps 50000 \
  --n-extend 5 \
  --output-dir cmorl_standard \
  --seed 42
```

**Expected Output:**
```
STAGE 1: 6 policies × 50K timesteps
  Training time: ~2-3 hours
  Pareto Front Size: 6

STAGE 2: 5 extensions × 3 objectives
  Training time: ~30-60 minutes
  Pareto Front Size: 18-21 (6 + 15)

Final Pareto Front:
  Size: 18-21 solutions
  Hypervolume: 0.75-0.85
  Expected Utility: 0.65-0.75

Best Solutions:
  Energy: 85-95 kWh (vs ECMR 95-105 kWh)
  Carbon: 13000-15000 gCO2 (vs ECMR 14500-16500 gCO2)
  Latency: 6.5-8.0 ms (vs ECMR 7.5-9.5 ms)
```

**Validation Criteria:**
- ✅ Pareto front size ≥ 15
- ✅ Hypervolume > 0.70
- ✅ Best energy solution < ECMR by 5-15%
- ✅ Best carbon solution < ECMR by 5-15%
- ✅ Best latency solution < ECMR by 5-15%

**Key Performance Indicators:**

| Solution Type | Energy (kWh) | Carbon (gCO2) | Latency (ms) |
|---------------|--------------|---------------|--------------|
| **Energy-optimal** | 85-92 | 15000-17000 | 8.0-10.0 |
| **Carbon-optimal** | 90-100 | 13000-14500 | 7.5-9.5 |
| **Latency-optimal** | 92-105 | 14500-16000 | 6.5-8.0 |
| **Balanced** | 88-96 | 14000-15500 | 7.2-8.8 |

**Runtime:** ~3-5 hours

---

### Scenario C3: Full Training (Publication Quality)

**Objective:** Train C-MORL with paper-specified hyperparameters

**Configuration:**
```bash
python3 train_cmorl.py \
  --simulation-hours 24 \
  --vms-per-hour 10 \
  --n-policies 6 \
  --timesteps 1500000 \
  --n-extend 5 \
  --output-dir cmorl_full \
  --seed 42
```

**Expected Output:**
```
Pareto Front Size: 20-24 solutions
Hypervolume: 0.82-0.90
Expected Utility: 0.72-0.82

Performance vs ECMR:
  Energy: 10-20% improvement
  Carbon: 8-18% improvement
  Latency: 8-15% improvement
```

**Runtime:** ~8-12 hours

---

### Scenario C4: Preference Sensitivity Test

**Objective:** Test C-MORL behavior with extreme preferences

**Test Cases:**

1. **Energy-focused:** `preference = [0.8, 0.1, 0.1]`
   - Expected: Lowest energy, possibly higher carbon/latency

2. **Carbon-focused:** `preference = [0.1, 0.8, 0.1]`
   - Expected: Lowest carbon, possibly higher energy/latency

3. **Latency-focused:** `preference = [0.1, 0.1, 0.8]`
   - Expected: Lowest latency, possibly higher energy/carbon

**Validation:**
- ✅ Each preference produces distinct policy
- ✅ Preferences reflect in objective priorities
- ✅ Trade-offs visible in Pareto front

---

### Scenario C5: Convergence Test

**Objective:** Verify C-MORL training convergence

**Metrics to Track:**
```
Episode 100: Loss=0.345, Return=-0.567
Episode 200: Loss=0.278, Return=-0.489
Episode 300: Loss=0.234, Return=-0.423
...
Episode 1000: Loss=0.156, Return=-0.312  # Converged
```

**Convergence Criteria:**
- ✅ Policy loss decreases and stabilizes
- ✅ Value loss decreases and stabilizes
- ✅ Episode return improves and plateaus
- ✅ No catastrophic forgetting (sudden drops)

---

## Comparison Test Scenarios

### Scenario CP1: Quick Comparison

**Objective:** Rapid ECMR vs C-MORL comparison

**Configuration:**
```bash
python3 run_comparison.py \
  --hours 2 \
  --vms-per-hour 5 \
  --cmorl-timesteps 1000 \
  --output-dir comparison_quick
```

**Expected Output:**
```markdown
# ECMR vs C-MORL Comparison Report

## Performance Comparison

| Metric | ECMR | C-MORL (Best) | Improvement |
|--------|------|---------------|-------------|
| Energy (kWh) | 4.25 | 3.78 | +11.06% |
| Carbon (gCO2) | 672.3 | 601.5 | +10.53% |
| Latency (ms) | 8.2 | 7.4 | +9.76% |

## C-MORL Pareto Front
  Size: 9 solutions
  Hypervolume: 0.68
  Expected Utility: 0.59
```

**Validation:**
- ✅ Both algorithms complete successfully
- ✅ C-MORL shows 5-15% improvement in at least one objective
- ✅ Pareto front size ≥ 7
- ✅ Comparison report generated

**Runtime:** ~15-20 minutes

---

### Scenario CP2: Standard Comparison (Daily Cycle)

**Objective:** Comprehensive comparison over 24-hour cycle

**Configuration:**
```bash
python3 run_comparison.py \
  --hours 24 \
  --vms-per-hour 10 \
  --cmorl-timesteps 50000 \
  --output-dir comparison_standard
```

**Expected Output:**

**ECMR Baseline:**
```
Total Energy: 98.5 kWh
Total Carbon: 15234.6 gCO2
Success Rate: 98.8%
Green DC %: 74.2%
```

**C-MORL Results:**
```
Best Solutions:
  Energy: 86.3 kWh (-12.4%)
  Carbon: 13567.2 gCO2 (-10.9%)
  Latency: 6.8 ms (-14.1%)

Pareto Front:
  Size: 19 solutions
  Hypervolume: 0.81
  Expected Utility: 0.71
```

**Comparison Metrics:**

| Metric | ECMR | C-MORL (Best) | C-MORL (Avg) | Winner |
|--------|------|---------------|--------------|--------|
| **M1: Energy/VM** | 0.410 kWh | 0.359 kWh | 0.385 kWh | C-MORL ✅ |
| **M2: Success Rate** | 98.8% | 99.2% | 98.6% | C-MORL ✅ |
| **M3: Avg Latency** | 7.9 ms | 6.8 ms | 7.3 ms | C-MORL ✅ |
| **M4: Total Carbon** | 15234.6 gCO2 | 13567.2 gCO2 | 14123.8 gCO2 | C-MORL ✅ |
| **M5: Green DC %** | 74.2% | 78.9% | 76.1% | C-MORL ✅ |

**Validation:**
- ✅ C-MORL improves on ECMR in 4/5 metrics
- ✅ Improvements are statistically significant (>5%)
- ✅ Pareto front provides trade-off options
- ✅ No degradation in success rate

**Runtime:** ~4-6 hours

---

### Scenario CP3: Weekly Cycle Comparison

**Objective:** Long-term performance evaluation

**Configuration:**
```bash
python3 run_comparison.py \
  --hours 168 \
  --vms-per-hour 10 \
  --cmorl-timesteps 50000 \
  --output-dir comparison_weekly
```

**Expected Scaling:**
- Energy: ~600-750 kWh (ECMR), ~550-680 kWh (C-MORL)
- Carbon: ~100K-140K gCO2 (ECMR), ~90K-125K gCO2 (C-MORL)
- Success Rate: 97-99% (both)

**Runtime:** ~24-30 hours

---

## Validation Criteria

### Success Criteria

#### ECMR
1. **Functional Requirements:**
   - ✅ All VMs placed or rejected (no hangs)
   - ✅ Success rate ≥ 95%
   - ✅ Energy consumption > 0 for all DCs
   - ✅ Carbon calculations match energy × intensity × PUE

2. **Performance Requirements:**
   - ✅ Energy per VM: 0.35-0.60 kWh
   - ✅ Carbon intensity < Random baseline
   - ✅ Green DC utilization ≥ 65%
   - ✅ Execution time < 30 minutes (240 VMs)

3. **Quality Requirements:**
   - ✅ Consistent results with same seed
   - ✅ Placement decisions explainable (scoring visible)
   - ✅ All 5 datacenters utilized

#### C-MORL
1. **Functional Requirements:**
   - ✅ Stage 1 and Stage 2 complete without errors
   - ✅ Pareto front size ≥ 70% of theoretical max
   - ✅ All policies save successfully
   - ✅ Results JSON valid and complete

2. **Performance Requirements:**
   - ✅ Hypervolume > 0.70
   - ✅ Expected utility > 0.60
   - ✅ At least one solution improves on ECMR
   - ✅ Training converges (loss decreases)

3. **Quality Requirements:**
   - ✅ No NaN or infinite values
   - ✅ Preferences reflected in learned policies
   - ✅ Pareto front spans objective space
   - ✅ Reproducible with same seed

#### Comparison
1. **Fair Comparison:**
   - ✅ Identical infrastructure configuration
   - ✅ Same dataset and time periods
   - ✅ Equal number of VMs placed
   - ✅ Metrics calculated consistently

2. **Statistical Validity:**
   - ✅ Run 3+ times with different seeds
   - ✅ Report mean and standard deviation
   - ✅ Perform significance testing (t-test)
   - ✅ Improvement > measurement noise (5%)

3. **Completeness:**
   - ✅ All 5 metrics (M1-M5) reported
   - ✅ Both best and average C-MORL results
   - ✅ Pareto front visualized
   - ✅ Trade-offs discussed

---

## Expected Results

### ECMR Baseline Performance

**24-hour, 240 VMs:**

| Metric | Expected Value | Range |
|--------|---------------|-------|
| Total Energy | 100 kWh | 90-110 kWh |
| Energy per VM | 0.42 kWh | 0.38-0.46 kWh |
| Total Carbon | 15000 gCO2 | 13500-16500 gCO2 |
| Success Rate | 99% | 98-100% |
| Avg Latency | 8.0 ms | 7.5-9.0 ms |
| Green DC % | 73% | 68-78% |

**Placement Distribution (typical):**
- DC_SWEDEN: 25-30% (best PUE + high renewable)
- DC_FRANCE: 20-25% (good PUE)
- DC_ITALY: 18-22%
- DC_NETHERLANDS: 15-20%
- DC_SPAIN: 12-18% (worst PUE)

### C-MORL Performance

**24-hour, 240 VMs, 50K timesteps:**

| Metric | Best Solution | Average | vs ECMR |
|--------|---------------|---------|---------|
| Energy | 88 kWh | 94 kWh | -12% / -6% |
| Carbon | 13800 gCO2 | 14500 gCO2 | -8% / -3% |
| Latency | 7.1 ms | 7.6 ms | -11% / -5% |

**Pareto Front Characteristics:**
- Size: 18-22 solutions
- Hypervolume: 0.78-0.84
- Expected Utility: 0.68-0.74
- Coverage: Spans all objective trade-offs

### Improvement Analysis

**Expected C-MORL Advantages:**
1. **Energy Efficiency:** 8-15% reduction
   - Learns optimal server utilization patterns
   - Better workload consolidation

2. **Carbon Reduction:** 6-12% reduction
   - Exploits temporal carbon variations
   - Proactive green energy utilization

3. **Latency Optimization:** 8-14% reduction
   - Learns user location patterns
   - Balances carbon and proximity

4. **Flexibility:** Pareto front provides 15-25 solutions
   - Adaptable to changing priorities
   - Multiple trade-off options

**ECMR Advantages:**
1. **Speed:** 10-50× faster (no training)
2. **Simplicity:** Easier to understand and debug
3. **Deterministic:** Same input → same output
4. **Robustness:** No hyperparameter tuning needed

---

## Result Interpretation

### Reading ECMR Output

**Energy Metrics:**
```
Total IT Energy: 87.5432 kWh        # Raw server power
Total Facility Energy: 103.2518 kWh # IT energy × PUE
Average PUE: 1.18                   # Facility / IT
```
- **Interpretation:** PUE of 1.18 means 18% overhead for cooling/infrastructure
- **Good:** PUE < 1.2 (achieved via strategic DC selection)

**Carbon Metrics:**
```
Total Carbon Emissions: 15234.5678 gCO2
Weighted Avg Carbon Intensity: 147.6 gCO2/kWh
Weighted Avg Renewable %: 65.3%
```
- **Calculation:** Carbon = Facility Energy × Carbon Intensity
- **Interpretation:** 147.6 gCO2/kWh is 18% below EU average (~180 gCO2/kWh)

**Green DC Utilization:**
```
Green Datacenter (DG) VMs: 178 (74.79%)
Brown Datacenter (DB) VMs: 59 (25.21%)
```
- **Interpretation:** Algorithm successfully prioritizes green DCs
- **Good:** >70% in green DCs
- **Excellent:** >80% in green DCs

### Reading C-MORL Output

**Pareto Front:**
```json
"solutions": [
  {"objectives": [85.23, 14567.89, 7.45], "stage": 1},
  {"objectives": [87.12, 13892.34, 7.89], "stage": 1},
  {"objectives": [91.45, 13234.56, 6.78], "stage": 2}
]
```

**Interpretation:**
- **Solution 1:** Balanced (Stage 1)
- **Solution 2:** Carbon-optimal (Stage 1, lowest carbon)
- **Solution 3:** Latency-optimal (Stage 2, lowest latency)

**Quality Metrics:**
```
Hypervolume: 0.8234
Expected Utility: 0.7456
```
- **Hypervolume > 0.80:** Excellent Pareto front quality
- **Expected Utility > 0.70:** Strong performance across preferences

### Comparing Results

**Example Comparison:**
```
| Metric | ECMR | C-MORL (Best) | Improvement |
|--------|------|---------------|-------------|
| Energy | 103.25 kWh | 88.45 kWh | +14.33% |
```

**Interpretation:**
- **+14.33%:** C-MORL uses 14.33% less energy
- **Significant:** Improvement > 10% is statistically significant
- **Practical:** Translates to measurable cost/carbon savings

**Trade-off Analysis:**
```
Solution A: Energy=85 kWh, Carbon=15000 gCO2, Latency=9 ms
Solution B: Energy=92 kWh, Carbon=13500 gCO2, Latency=8 ms
```
- **Solution A:** Energy-optimal (8% more energy for 10% less carbon)
- **Solution B:** Carbon-optimal
- **Choice:** Depends on business priorities

---

## Troubleshooting Failed Tests

### ECMR Failures

**Low Success Rate (<95%):**
- **Cause:** Insufficient datacenter capacity
- **Solution:** Reduce VMs/hour or increase server count
- **Check:** VM distribution matches capacity

**High Carbon Intensity:**
- **Cause:** Dataset has high-carbon period
- **Solution:** Verify dataset quality
- **Check:** Compare to baseline (random placement)

**Execution Timeout:**
- **Cause:** Gateway unresponsive
- **Solution:** Restart gateway with more heap memory

### C-MORL Failures

**Training Divergence (NaN loss):**
- **Cause:** Learning rate too high
- **Solution:** Reduce learning rate to 1e-4 or 1e-5
- **Check:** Monitor loss curves

**Small Pareto Front (<10 solutions):**
- **Cause:** Insufficient timesteps or dominated solutions
- **Solution:** Increase timesteps or adjust preferences
- **Check:** Stage 1 diversity

**Long Training Time:**
- **Cause:** High episode duration or large networks
- **Solution:** Reduce episode length or use smaller networks
- **Acceptable:** 1.5M timesteps should complete in <12 hours

### Comparison Failures

**Inconsistent Results:**
- **Cause:** Different random seeds or configurations
- **Solution:** Verify identical parameters
- **Check:** Infrastructure configuration matches

**No Improvement:**
- **Cause:** Insufficient C-MORL training
- **Solution:** Increase timesteps to 50K+
- **Check:** Convergence curves

---

## Summary

### Quick Test Checklist

**ECMR (2 hours, 10 VMs):**
- [ ] Gateway starts successfully
- [ ] All 5 DCs created
- [ ] 10 VMs placed
- [ ] Success rate ≥ 98%
- [ ] Energy: 3-6 kWh
- [ ] Carbon: 500-1000 gCO2
- [ ] Runtime: <3 minutes

**C-MORL (2 hours, 10 VMs, 1K timesteps):**
- [ ] Stage 1 trains 3 policies
- [ ] Stage 2 extends to 9 policies
- [ ] Pareto front size ≥ 7
- [ ] Hypervolume > 0.60
- [ ] No NaN values
- [ ] Runtime: <15 minutes

**Comparison:**
- [ ] Both complete successfully
- [ ] Metrics calculated consistently
- [ ] Comparison report generated
- [ ] C-MORL improves ≥1 objective
- [ ] Runtime: <20 minutes

### Standard Test Checklist

**ECMR (24 hours, 240 VMs):**
- [ ] Success rate ≥ 98%
- [ ] Energy: 90-110 kWh
- [ ] Carbon: 13500-16500 gCO2
- [ ] Green DC%: 65-80%
- [ ] Runtime: <20 minutes

**C-MORL (24 hours, 240 VMs, 50K timesteps):**
- [ ] Pareto front size ≥ 15
- [ ] Hypervolume > 0.70
- [ ] Energy improvement: 5-15%
- [ ] Carbon improvement: 5-15%
- [ ] Runtime: 3-5 hours

**Comparison:**
- [ ] C-MORL wins 3/5 metrics
- [ ] Improvements > 5%
- [ ] Statistical significance confirmed
- [ ] Trade-offs documented
- [ ] Runtime: 4-6 hours

---

For running instructions, see `RUNNING_TESTING_GUIDE.md`.
For implementation details, see `CODE_REFERENCE.md`.
