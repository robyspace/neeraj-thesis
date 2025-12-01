# Enhanced Comparison Report: ECMR vs C-MORL

**Generated:** 2025-11-29 23:15:58

---

## Configuration

### ECMR Baseline
- Simulation: 24 hours × 10 VMs/hour
- Total VMs: 240
- Runtime: 0.4s

### C-MORL
- Simulation: 24 hours × 10 VMs/hour
- Total VMs: 240
- Training: 3 policies × 20000 timesteps
- Extensions: 2 sparse solutions
- Runtime: 327.9s (5.5 min)
- Pareto Front Size: 2 solutions

---

## C-MORL Pareto Front Solutions

All solutions discovered by C-MORL:

| # | Policy ID | Stage | Energy (kWh) | Carbon (gCO2) | Latency (ms) | Green DC % |
|---|-----------|-------|--------------|---------------|--------------|------------|
| 1 | 3 | 1 | 26.69 | 383.40 | 8.62 | 100.0% |
| 2 | extended_1_Carbon | 2 | 26.69 | 319.70 | 14.60 | 100.0% |

---

## Best Solutions Comparison

Comparing ECMR against the best C-MORL solution for each objective:

### Best Energy Solution

**C-MORL Solution:** #1 (Policy 3)

| Metric | ECMR | C-MORL | Improvement |
|--------|------|--------|-------------|
| Energy per VM (kWh) | 0.0920 | 0.1112 | -20.8% |
| Total Carbon (gCO2) | 1958.10 | 1958.20 | -0.0% |
| Avg Latency (ms) | 0.00 | 8.62 | +0.0% |
| Green DC Util (%) | 100.0% | 100.0% | +0.0pp |
| Success Rate (%) | 100.0% | 100.0% | - |

### Best Carbon Solution

**C-MORL Solution:** #2 (Policy extended_1_Carbon)

| Metric | ECMR | C-MORL | Improvement |
|--------|------|--------|-------------|
| Energy per VM (kWh) | 0.0920 | 0.1112 | -20.8% |
| Total Carbon (gCO2) | 1958.10 | 1958.20 | -0.0% |
| Avg Latency (ms) | 0.00 | 14.60 | +0.0% |
| Green DC Util (%) | 100.0% | 100.0% | +0.0pp |
| Success Rate (%) | 100.0% | 100.0% | - |

### Best Latency Solution

**C-MORL Solution:** #1 (Policy 3)

| Metric | ECMR | C-MORL | Improvement |
|--------|------|--------|-------------|
| Energy per VM (kWh) | 0.0920 | 0.1112 | -20.8% |
| Total Carbon (gCO2) | 1958.10 | 1958.20 | -0.0% |
| Avg Latency (ms) | 0.00 | 8.62 | +0.0% |
| Green DC Util (%) | 100.0% | 100.0% | +0.0pp |
| Success Rate (%) | 100.0% | 100.0% | - |

---

## Detailed Metrics: ECMR vs Best C-MORL (Energy-optimal)

### M1: Resource Utilization Efficiency

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Total Energy (kWh) | 26.6898 | 26.6906 | ECMR |
| Energy per VM (kWh) | 0.0920 | 0.1112 | ECMR |
| Avg CPU Util (%) | 0.0000 | 0.0000 | ECMR |
| Avg RAM Util (%) | 0.0000 | 0.0000 | ECMR |

### M2: Throughput

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Success Rate (%) | 100.0000 | 100.0000 | ECMR |
| VMs per Second | 29.0000 | 4.0000 | ECMR |

### M3: Response Time

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Avg Latency (ms) | 0.0000 | 8.6175 | ECMR |

### M4: Carbon Intensity Reduction

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Total Carbon (gCO2) | 0.0000 | 0.0000 | ECMR |
| Avg Carbon Intensity (gCO2/kWh) | 0.0000 | 0.0000 | ECMR |
| Avg Renewable (%) | 0.0000 | 0.0000 | ECMR |

### M5: Green DC Utilization

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Green DC Util (%) | 0.0000 | 0.0000 | ECMR |
| Brown DC Util (%) | 0.0000 | 0.0000 | ECMR |

---

## Key Findings

1. **Pareto Front**: C-MORL discovered 2 non-dominated solutions
2. **Hypervolume**: 579.59
3. **Trade-offs**: C-MORL provides multiple solutions with different objective trade-offs
4. **ECMR**: Single-objective greedy solution, fast execution

### Performance Improvements (Best C-MORL vs ECMR)

-  **Energy**: 0.0% increase
-  **Carbon**: 0.0% increase
