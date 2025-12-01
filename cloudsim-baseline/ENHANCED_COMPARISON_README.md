# Enhanced Comparison Framework: ECMR vs C-MORL

Complete comparison framework with comprehensive metrics extraction (M1-M5) and visualization.

## 🎯 What's New

### ✅ Fixed Issues from Original Comparison
- **M5 (Green DC Utilization) now extracted and compared** ⭐
- **Real metrics extracted** instead of hardcoded/estimated values
- **All Pareto solutions analyzed** instead of just "best"
- **Fair comparison configuration** with identical parameters
- **Enhanced parsers** that extract datacenter placement details
- **Publication-quality visualizations** (radar charts, 3D Pareto fronts, etc.)

### 📊 Complete Metrics Extraction
- **M1: Resource Utilization Efficiency** - Actual CPU/RAM utilization from CloudSim
- **M2: Throughput** - Real success rates and timing
- **M3: Response Time** - Accurate latency from datacenter placement
- **M4: Carbon Intensity Reduction** - Complete carbon metrics with baseline comparison
- **M5: Green DC Utilization** - **NEW!** Green (DG) vs Brown (DB) datacenter breakdown

---

## 🚀 Quick Start

### Prerequisites
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install matplotlib if not already installed
pip install matplotlib
```

### 1. Run Complete Comparison

```bash
# Full comparison with default settings (24 hours, 10 VMs/hour)
python3 run_enhanced_comparison.py

# Custom configuration
python3 run_enhanced_comparison.py \
  --hours 24 \
  --vms-per-hour 10 \
  --cmorl-timesteps 10000 \
  --cmorl-policies 3 \
  --cmorl-extend 2 \
  --output-dir my_comparison_results
```

**Note:** Make sure the Java gateway is running before executing:
```bash
# Start gateway (in separate terminal or background)
java -Xmx4g -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 &
```

### 2. Generate Visualizations

```bash
# Generate all charts and graphs
python3 comparison_visualizer.py --results-dir enhanced_comparison_results
```

### 3. View Results

```bash
# Read the comparison report
cat enhanced_comparison_results/comparison_report.md

# View figures
open enhanced_comparison_results/figures/
```

---

## 📁 Output Structure

```
enhanced_comparison_results/
├── comparison_report.md          # Comprehensive Markdown report
├── ecmr/
│   ├── output.txt                # Full ECMR execution log
│   ├── metrics.json              # Extracted M1-M5 metrics
│   └── raw_data.json             # Detailed raw data
├── cmorl/
│   ├── training_log.txt          # Full C-MORL training log
│   ├── solution_1_metrics.json   # Metrics for each Pareto solution
│   ├── solution_2_metrics.json
│   ├── ...
│   ├── final_results.json        # Pareto front summary
│   ├── raw_data.json             # Detailed raw data
│   └── stage1/                   # Trained policies
│       └── stage2/
└── figures/                       # Visualizations
    ├── objectives_comparison.png  # Bar charts for Energy/Carbon/Latency
    ├── pareto_front_3d.png        # 3D scatter plot of Pareto front
    ├── metrics_radar.png          # Radar chart comparing M1-M5
    ├── green_dc_utilization.png   # Green vs Brown DC breakdown
    └── improvement_summary.png    # Percentage improvements
```

---

## 🔧 Advanced Usage

### Skip Already-Run Algorithms

```bash
# Skip ECMR if already run (use existing results)
python3 run_enhanced_comparison.py --skip-ecmr

# Skip C-MORL if already run
python3 run_enhanced_comparison.py --skip-cmorl

# Skip both (just regenerate report from existing results)
python3 run_enhanced_comparison.py --skip-ecmr --skip-cmorl
```

### Test Individual Parsers

```bash
# Test ECMR parser
python3 enhanced_ecmr_parser.py enhanced_comparison_results/ecmr/output.txt

# Test C-MORL parser
python3 enhanced_cmorl_parser.py \
  enhanced_comparison_results/cmorl \
  enhanced_comparison_results/cmorl/training_log.txt
```

### Use Parsers in Your Own Scripts

```python
from enhanced_ecmr_parser import parse_ecmr_results
from enhanced_cmorl_parser import parse_cmorl_results

# Parse ECMR output
with open('ecmr_output.txt', 'r') as f:
    ecmr_output = f.read()
ecmr_metrics, ecmr_raw_data = parse_ecmr_results(ecmr_output)

# Parse C-MORL results
cmorl_metrics_list, cmorl_raw_data = parse_cmorl_results(
    'cmorl_results_dir',
    'cmorl_training_log.txt'
)

# Access metrics
print(ecmr_metrics.metrics['M5_green_dc_utilization'])
for sol_metrics in cmorl_metrics_list:
    print(sol_metrics.metrics['M4_carbon_reduction'])
```

---

## 📊 Metrics Explained

### M1: Resource Utilization Efficiency
- **Total Energy (kWh)**: Total facility energy consumption (IT + PUE overhead)
- **Energy per VM (kWh)**: Energy efficiency metric
- **CPU/RAM Utilization (%)**: Weighted average across all datacenters
- **Efficiency Score**: Normalized score (0-1, higher is better)

### M2: Throughput
- **Success Rate (%)**: Percentage of VMs successfully placed
- **VMs per Second**: Placement throughput
- **Throughput Score**: Normalized score (0-1, higher is better)

### M3: Response Time
- **Avg Network Latency (ms)**: User-to-datacenter network delay
- **VM Creation Time (s)**: Time to place and create VM
- **Response Score**: Normalized score (0-1, higher is better)

### M4: Carbon Intensity Reduction
- **Total Carbon Emissions (gCO2)**: Total carbon footprint
- **Reduction vs Baseline (%)**: Improvement over ECMR baseline
- **Avg Carbon Intensity (gCO2/kWh)**: Weighted average across DCs
- **Avg Renewable (%)**: Weighted renewable energy percentage
- **Carbon Score**: Normalized score (0-1, higher is better)

### M5: Green Datacenter Utilization ⭐ NEW
- **Green DC VMs**: Number of VMs placed in Green datacenters (DG)
- **Brown DC VMs**: Number of VMs placed in Brown datacenters (DB)
- **Green Utilization (%)**: Percentage of VMs in green DCs
- **Green DC Score**: Normalized score (0-1, higher is better)

---

## 🎨 Visualizations Generated

### 1. Objectives Comparison (`objectives_comparison.png`)
Bar charts showing Energy, Carbon, and Latency for ECMR and all C-MORL Pareto solutions.
- Best C-MORL solution highlighted in green
- Clear comparison across all objectives

### 2. 3D Pareto Front (`pareto_front_3d.png`)
3D scatter plot showing the Pareto front in Energy-Carbon-Latency space.
- ECMR shown as single red point
- C-MORL Pareto solutions shown as blue triangles
- Visualizes trade-offs between objectives

### 3. Metrics Radar Chart (`metrics_radar.png`)
Radar chart comparing M1-M5 normalized scores.
- ECMR (red) vs C-MORL best solution (blue)
- Shows strengths and weaknesses across all metrics

### 4. Green DC Utilization (`green_dc_utilization.png`)
Stacked bar chart showing Green vs Brown datacenter usage.
- M5 metric visualization
- Critical for sustainability comparison

### 5. Improvement Summary (`improvement_summary.png`)
Horizontal bar chart showing percentage improvements.
- Positive = C-MORL better
- Negative = ECMR better
- Clear visual summary of key improvements

---

## 🔬 Fair Comparison Ensured

The enhanced framework ensures fair comparison:

1. **Identical Simulation Configuration**
   - Same simulation duration (hours)
   - Same VM arrival rate (VMs/hour)
   - Same total VMs processed
   - Same carbon intensity data

2. **Appropriate Training Budget**
   - Default: 10,000 timesteps per policy (vs old 1,000)
   - Sufficient for meaningful learning
   - Can be adjusted via `--cmorl-timesteps`

3. **Apples-to-Apples Metrics**
   - Both use same CloudSim backend
   - Both evaluated on same datacenter infrastructure
   - M5 extracted using identical methodology

---

## 📝 Example Workflow

```bash
# 1. Start gateway
pkill -9 -f "Py4JGatewayEnhanced"
java -Xmx4g -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > /Volumes/M4MiniDrv/cmorl_logs/gateway.log 2>&1 &

sleep 5

# 2. Activate environment
source venv/bin/activate

# 3. Run comparison (this takes time - C-MORL training is lengthy)
python3 run_enhanced_comparison.py \
  --hours 24 \
  --vms-per-hour 10 \
  --cmorl-timesteps 10000 \
  --output-dir my_results

# 4. Generate visualizations
python3 comparison_visualizer.py --results-dir my_results

# 5. View results
cat my_results/comparison_report.md
open my_results/figures/

# 6. Cleanup
pkill -9 -f "Py4JGatewayEnhanced"
```

---

## 🆚 Comparison vs Old Framework

| Feature | Old Framework | Enhanced Framework |
|---------|--------------|-------------------|
| **M5 Extraction** | ❌ Not extracted | ✅ Fully extracted |
| **Actual Metrics** | ❌ Hardcoded/estimated | ✅ Real from CloudSim |
| **Pareto Analysis** | ❌ Only "best" solution | ✅ All solutions |
| **Fair Config** | ⚠️ Unfair (1000 timesteps) | ✅ Fair (10000 timesteps) |
| **Visualizations** | ❌ Text only | ✅ 5 publication charts |
| **Parser Robustness** | ⚠️ Regex fragile | ✅ Comprehensive |
| **Documentation** | ⚠️ Minimal | ✅ Complete README |

---

## ❓ Troubleshooting

### Gateway Connection Issues
```bash
# Check if gateway is running
ps aux | grep Py4JGatewayEnhanced

# Restart gateway
pkill -9 -f "Py4JGatewayEnhanced"
java -Xmx4g -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 &
```

### Module Not Found Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install missing dependencies
pip install matplotlib numpy pandas
```

### Parsing Errors
```bash
# Test parsers individually
python3 enhanced_ecmr_parser.py <ecmr_output.txt>
python3 enhanced_cmorl_parser.py <cmorl_dir> <training_log.txt>
```

### M5 Not Extracted
- Ensure your ECMR/C-MORL output includes the "M5: GREEN DATACENTER UTILIZATION" section
- Check that datacenter types (DG/DB) are properly configured
- The parser will fallback to inference if M5 section not found

---

## 📚 Additional Resources

- **Original Comparison Scripts**: `run_comparison.py`, `process_comparison_results.py` (legacy)
- **Unified Metrics Module**: `unified_metrics.py`
- **C-MORL Training**: `train_cmorl.py`
- **ECMR Integration**: `ecmr_heterogeneous_integration.py`

---

## 🎓 For Your Thesis/Paper

This enhanced framework provides:

1. **Complete M1-M5 metrics** for both algorithms
2. **Publication-quality figures** (300 DPI PNGs)
3. **Comprehensive Markdown report** for documentation
4. **JSON metrics files** for further analysis (Excel, R, Python)
5. **Reproducible comparison** with fair configuration

**Citation-worthy results** with rigorous methodology! 🎯

---

## 📧 Need Help?

Check the comparison report markdown file for detailed results and findings.

---

**Last Updated**: 2025-11-29
**Framework Version**: 2.0 (Enhanced)
