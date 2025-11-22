# ECMR vs C-MORL: Standardized Comparison Framework

## Overview
This framework provides a fair comparison between ECMR (baseline) and C-MORL (proposed) algorithms using **identical experimental conditions** and **unified metrics**.

## ✅ Verified Identical Configuration

### Infrastructure
| Component | ECMR | C-MORL | Status |
|-----------|------|--------|--------|
| **Datacenters** | 5 European | 5 European | ✅ IDENTICAL |
| - Madrid (Spain) | DC_SPAIN (PUE 1.25) | DC_MADRID (PUE 1.25) | ✅ |
| - Amsterdam (Netherlands) | DC_NETHERLANDS (PUE 1.2) | DC_AMSTERDAM (PUE 1.2) | ✅ |
| - Paris (France) | DC_FRANCE (PUE 1.15) | DC_PARIS (PUE 1.15) | ✅ |
| - Milan (Italy) | DC_ITALY (PUE 1.2) | DC_MILAN (PUE 1.2) | ✅ |
| - Stockholm (Sweden) | DC_SWEDEN (PUE 1.1) | DC_STOCKHOLM (PUE 1.1) | ✅ |
| **Server Types** | 3 heterogeneous | 3 heterogeneous | ✅ IDENTICAL |
| - Huawei RH2285 V2 | 40 servers | 40 servers | ✅ |
| - Huawei RH2288H V3 | 40 servers | 40 servers | ✅ |
| - Lenovo SR655 V3 | 40 servers | 40 servers | ✅ |
| **VM Types** | small(40%), medium(30%), large(20%), xlarge(10%) | small(40%), medium(30%), large(20%), xlarge(10%) | ✅ IDENTICAL |
| **Power Models** | 11-point SpecPower curves | 11-point SpecPower curves | ✅ IDENTICAL |
| **Energy Calculation** | PUE-adjusted | PUE-adjusted | ✅ IDENTICAL |
| **Carbon Data** | synchronized_dataset_2024.csv | synchronized_dataset_2024.csv | ✅ IDENTICAL |
| **CloudSim Backend** | Py4JGatewayEnhanced | Py4JGatewayEnhanced | ✅ IDENTICAL |

## Unified Metrics (4 Research Metrics)

### M1: Resource Utilization Efficiency
- **Primary**: Energy per VM (kWh/VM) - Lower is better
- **Secondary**: CPU/RAM utilization (%) - Higher is better
- **Normalized Score**: 0-1 (higher is better)

### M2: Throughput
- **Primary**: Success Rate (%) - Higher is better
- **Secondary**: VMs placed per second
- **Normalized Score**: 0-1 (higher is better)

### M3: Response Time
- **Primary**: Average network latency (ms) - Lower is better
- **Secondary**: VM creation time (s)
- **Normalized Score**: 0-1 (higher is better)

### M4: Carbon Intensity Reduction
- **Primary**: Total carbon emissions (gCO2) - Lower is better
- **Secondary**: Reduction vs baseline (%)
- **Additional**: Average carbon intensity (gCO2/kWh), Renewable % (%)
- **Normalized Score**: 0-1 (higher is better)

## Files Created

### Core Components
1. **unified_metrics.py** - Standardized metrics calculation and comparison
2. **cmorl_environment.py** - C-MORL Gym environment (✅ matches ECMR config)
3. **cmorl_agent.py** - Multi-objective PPO agent
4. **train_cmorl.py** - Two-stage C-MORL training
5. **pareto_utils.py** - Pareto front management

### Comparison Scripts
6. **run_final_comparison.sh** - Automated comparison execution
7. **process_comparison_results.py** - Post-processing and metrics extraction
8. **run_comparison.py** - Alternative Python-based comparison script

## Usage

### Quick Test (2 hours, 10 VMs)
```bash
# 1. Start gateway
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 &

# 2. Run ECMR
source venv/bin/activate
python ecmr_heterogeneous_integration.py --hours 2 --vms-per-hour 5

# 3. Restart gateway and run C-MORL
python train_cmorl.py --simulation-hours 2 --vms-per-hour 5 \
  --n-policies 3 --timesteps 1000 --n-extend 2 --output-dir cmorl_results

# 4. Compare results
python process_comparison_results.py ecmr_output.txt cmorl_results/
```

### Full Comparison (24 hours, 240 VMs)
```bash
./run_final_comparison.sh
```

## Output Format

Both algorithms now produce results in the same unified format:

```
================================================================================
ALGORITHM NAME
================================================================================

📊 M1: RESOURCE UTILIZATION EFFICIENCY
--------------------------------------------------------------------------------
  Total Energy:          X.XXXX kWh
  Total VMs:             XXX
  Energy per VM:         X.XXXX kWh/VM
  Avg CPU Utilization:   XX.XX%
  Avg RAM Utilization:   XX.XX%
  ➜ Efficiency Score:    X.XXX/1.000

⚡ M2: THROUGHPUT
--------------------------------------------------------------------------------
  Successful VMs:        XXX
  Failed VMs:            XXX
  Success Rate:          XX.XX%
  VMs per Second:        X.XXXX
  ➜ Throughput Score:    X.XXX/1.000

⏱️  M3: RESPONSE TIME
--------------------------------------------------------------------------------
  Avg Network Latency:   X.XXXX ms
  Avg VM Creation Time:  X.XXXX s
  Total Simulation Time: XXX.XX s
  ➜ Response Score:      X.XXX/1.000

🌍 M4: CARBON INTENSITY REDUCTION
--------------------------------------------------------------------------------
  Total Carbon Emissions: X.XXXX gCO2
  Baseline Carbon:        X.XXXX gCO2
  Reduction vs Baseline:  +XX.XX%
  Avg Carbon Intensity:   XX.XX gCO2/kWh
  Avg Renewable Energy:   XX.XX%
  ➜ Carbon Score:         X.XXX/1.000

================================================================================
📊 METRICS COMPARISON: ECMR vs C-MORL
================================================================================
[Side-by-side comparison with improvement percentages]
```

## Key Differences (Algorithm Only)

| Aspect | ECMR | C-MORL |
|--------|------|--------|
| **Algorithm Type** | Weighted sum MILP optimization | Multi-objective PPO (Reinforcement Learning) |
| **Decision Making** | Deterministic (single best solution) | Stochastic policy learning |
| **Output** | 1 solution | Pareto front of solutions |
| **Training** | No training (optimization-based) | Two-stage training (Pareto initialization + extension) |
| **Adaptation** | Static weights | Learns from experience |
| **Trade-offs** | Fixed preference vector | Explores multiple preference vectors |

## Next Steps

1. ✅ **Configuration verified** - Both use identical infrastructure
2. ✅ **Unified metrics defined** - 4 standardized metrics (M1-M4)
3. ✅ **Comparison framework ready** - Scripts and tools created
4. 🔄 **Run comparison** - Execute with matching workloads
5. 📊 **Analyze results** - Compare performance across all metrics
6. 📝 **Generate paper results** - Tables and figures for publication

## Expected Results

C-MORL should demonstrate:
- **Multiple solutions** vs ECMR's single solution
- **Better carbon reduction** through multi-objective optimization
- **Flexible trade-offs** between energy, carbon, and latency
- **Pareto optimality** - no single metric can improve without degrading another

ECMR advantages:
- **Faster execution** - No training required
- **Deterministic results** - Reproducible without random seed
- **Simpler implementation** - Straightforward optimization

## Files Location
```
cloudsim-baseline/
├── unified_metrics.py                 # Metrics calculation
├── cmorl_environment.py               # C-MORL environment
├── cmorl_agent.py                     # PPO agent
├── train_cmorl.py                     # Training script
├── pareto_utils.py                    # Pareto front utils
├── run_final_comparison.sh            # Comparison script
├── process_comparison_results.py      # Results processing
└── COMPARISON_SETUP.md                # This file
```
