# ECMR vs C-MORL Comparison Report

Generated: 2025-11-22 02:23:59

## Configuration

- **ECMR**: 2 hours × 5 VMs/hour = 10 total VMs
- **C-MORL**: 2 hours × 5 VMs/hour × 1000 timesteps

## Performance Comparison

| Metric | ECMR | C-MORL (Best) | C-MORL (Avg) | Improvement |
|--------|------|---------------|--------------|-------------|
| Energy (kWh) | 0.55 | 0.55 | 0.55 | +0.0% |
| Carbon (gCO2) | 0.04 | 0.00 | 4.16 | +100.0% |
| Runtime (s) | 0.4 | 26.6 | - | - |

## C-MORL Pareto Front

- **Size**: 2 solutions
- **Hypervolume**: 0.36
- **Expected Utility**: -2.49

### All Solutions

| Solution | Energy (kWh) | Carbon (gCO2) | Latency (ms) | Stage | Preference |
|----------|--------------|---------------|--------------|-------|------------|
| 1 | 0.55 | 0.00 | 9.30 | 1 | [0.10, 0.63, 0.27] |
| 2 | 0.55 | 8.33 | 5.00 | 2 | [0.15, 0.15, 0.70] |

## Key Findings

- ✅ C-MORL achieves 0.0% energy reduction
- ✅ C-MORL achieves 100.0% carbon reduction
- C-MORL provides 2 trade-off solutions vs ECMR's single solution
