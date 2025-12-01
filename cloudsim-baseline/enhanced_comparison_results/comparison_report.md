# Enhanced Comparison Report: ECMR vs C-MORL

**Generated:** 2025-11-29 20:51:38

---

## Configuration

### ECMR Baseline
- Simulation: 2 hours × 5 VMs/hour
- Total VMs: 10
- Runtime: 0.4s

### C-MORL
- Simulation: 2 hours × 5 VMs/hour
- Total VMs: 10
- Training: 3 policies × 10000 timesteps
- Extensions: 2 sparse solutions
- Runtime: 127.1s (2.1 min)
- Pareto Front Size: 4 solutions

---

## C-MORL Pareto Front Solutions

All solutions discovered by C-MORL:

| # | Policy ID | Stage | Energy (kWh) | Carbon (gCO2) | Latency (ms) | Green DC % |
|---|-----------|-------|--------------|---------------|--------------|------------|
| 1 | 1 | 1 | 0.55 | 0.00 | 9.30 | 100.0% |
| 2 | 3 | 1 | 0.55 | 0.00 | 9.30 | 0.0% |
| 3 | extended_1_Latency | 2 | 6.68 | 245.50 | 5.64 | 100.0% |
| 4 | extended_2_Latency | 2 | 6.67 | 60.23 | 6.72 | 0.0% |

---

## Best Solutions Comparison

Comparing ECMR against the best C-MORL solution for each objective:

### Best Energy Solution

**C-MORL Solution:** #1 (Policy 1)

| Metric | ECMR | C-MORL | Improvement |
|--------|------|--------|-------------|
| Energy per VM (kWh) | 0.0830 | 0.0554 | +33.3% |
| Total Carbon (gCO2) | 62.60 | 41.70 | +33.4% |
| Avg Latency (ms) | 10.00 | 9.30 | +7.0% |
| Green DC Util (%) | 100.0% | 100.0% | +0.0pp |
| Success Rate (%) | 100.0% | 100.0% | - |

### Best Carbon Solution

**C-MORL Solution:** #1 (Policy 1)

| Metric | ECMR | C-MORL | Improvement |
|--------|------|--------|-------------|
| Energy per VM (kWh) | 0.0830 | 0.0554 | +33.3% |
| Total Carbon (gCO2) | 62.60 | 41.70 | +33.4% |
| Avg Latency (ms) | 10.00 | 9.30 | +7.0% |
| Green DC Util (%) | 100.0% | 100.0% | +0.0pp |
| Success Rate (%) | 100.0% | 100.0% | - |

### Best Latency Solution

**C-MORL Solution:** #3 (Policy extended_1_Latency)

| Metric | ECMR | C-MORL | Improvement |
|--------|------|--------|-------------|
| Energy per VM (kWh) | 0.0830 | 0.0554 | +33.3% |
| Total Carbon (gCO2) | 62.60 | 41.70 | +33.4% |
| Avg Latency (ms) | 10.00 | 5.64 | +43.6% |
| Green DC Util (%) | 100.0% | 100.0% | +0.0pp |
| Success Rate (%) | 100.0% | 100.0% | - |

---

## Detailed Metrics: ECMR vs Best C-MORL (Energy-optimal)

### M1: Resource Utilization Efficiency

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Total Energy (kWh) | 0.8304 | 0.5536 | C-MORL ✓ |
| Energy per VM (kWh) | 0.0830 | 0.0554 | C-MORL ✓ |
| Avg CPU Util (%) | 37.8000 | 29.6000 | ECMR |
| Avg RAM Util (%) | 41.1000 | 32.1000 | ECMR |

### M2: Throughput

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Success Rate (%) | 100.0000 | 100.0000 | ECMR |
| VMs per Second | 1.0000 | 0.1667 | ECMR |

### M3: Response Time

| Metric | ECMR | C-MORL | Winner |
|--------|------|--------|--------|
| Avg Latency (ms) | 10.0000 | 9.2986 | C-MORL ✓ |

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

1. **Pareto Front**: C-MORL discovered 4 non-dominated solutions
2. **Hypervolume**: 1989.21
3. **Trade-offs**: C-MORL provides multiple solutions with different objective trade-offs
4. **ECMR**: Single-objective greedy solution, fast execution

### Performance Improvements (Best C-MORL vs ECMR)

-  **Energy**: 33.3% reduction
-  **Carbon**: 33.4% reduction
