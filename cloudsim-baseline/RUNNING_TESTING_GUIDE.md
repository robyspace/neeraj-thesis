# Step-by-Step Guide: Running and Testing ECMR, C-MORL, and Baseline Comparison

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Running ECMR Baseline](#running-ecmr-baseline)
4. [Running C-MORL](#running-c-morl)
5. [Running Complete Comparison](#running-complete-comparison)
6. [Understanding Results](#understanding-results)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Java 8+**: For CloudSim simulation backend
- **Python 3.8+**: For ECMR and C-MORL implementations
- **Maven**: For building Java components

### Required Python Packages
```bash
pip install pandas numpy py4j torch gymnasium
```

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB free space for results
- **OS**: macOS, Linux, or Windows (with WSL)

---

## Environment Setup

### Step 1: Build CloudSim Backend

```bash
# Navigate to project root
cd /Users/robyspace/Documents/GitHub/neeraj-thesis/cloudsim-baseline

# Clean and build
mvn clean package
```

**Expected Output:**
```
[INFO] BUILD SUCCESS
[INFO] Total time: XX.XXX s
```

**What this does:**
- Compiles Java CloudSim classes
- Creates heterogeneous datacenter infrastructure
- Packages with dependencies into JAR file
- Location: `target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar`

### Step 2: Verify Dataset

```bash
# Check carbon intensity dataset exists
ls -lh output/synchronized_dataset_2024.csv
```

**Expected:**
- File size: ~500KB
- Contains: 8760 hourly records (1 year)
- Columns: Timestamp, carbon intensity, renewable %, datacenter types for 5 countries

---

## Running ECMR Baseline

### Step 1: Start Java Gateway

```bash
# Kill any existing gateway processes
pkill -9 -f "Py4JGatewayEnhanced"

# Start new gateway in background
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway_ecmr.log 2>&1 &

# Wait for gateway to initialize
sleep 5

# Verify gateway is running
tail -f gateway_ecmr.log
# Press Ctrl+C after seeing "Gateway Server Started"
```

**What this does:**
- Starts Py4J bridge between Python and Java
- Initializes CloudSim core components
- Creates heterogeneous datacenter infrastructure
- Loads non-linear power models from SpecPower data

### Step 2: Run ECMR Algorithm

#### Quick Test (2 hours, 10 VMs)
```bash
python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 2 \
  --vms-per-hour 5 \
  > ecmr_quick_test.txt 2>&1

# View results
cat ecmr_quick_test.txt
```

#### Full Test (24 hours, 240 VMs)
```bash
python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 24 \
  --vms-per-hour 10 \
  > ecmr_full_test.txt 2>&1

# Monitor progress
tail -f ecmr_full_test.txt
```

**Parameters:**
- `--data`: Path to carbon intensity CSV file
- `--hours`: Number of simulation hours (1-8760)
- `--vms-per-hour`: VMs to place each hour (1-50)

**Execution Time:**
- Quick test: ~2-3 minutes
- Full test: ~15-20 minutes

### Step 3: Verify ECMR Results

```bash
# Check output file
grep -A 10 "SIMULATION RESULTS" ecmr_full_test.txt

# Extract key metrics
grep "Total IT Energy" ecmr_full_test.txt
grep "Total Carbon Emissions" ecmr_full_test.txt
grep "Success Rate" ecmr_full_test.txt
```

**Expected Metrics:**
- Total Energy: 50-150 kWh (depends on workload)
- Total Carbon: 5000-30000 gCO2
- Success Rate: >95%
- Green DC Utilization: 60-80%

### Step 4: Stop Gateway

```bash
pkill -9 -f "Py4JGatewayEnhanced"
```

---

## Running C-MORL

### Step 1: Start Java Gateway

```bash
# Kill any existing processes
pkill -9 -f "Py4JGatewayEnhanced"

# Start gateway
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway_cmorl.log 2>&1 &

sleep 5
```

### Step 2: Train C-MORL Agent

#### Quick Training (Test Mode)
```bash
python3 train_cmorl.py \
  --simulation-hours 2 \
  --vms-per-hour 5 \
  --n-policies 3 \
  --timesteps 1000 \
  --n-extend 2 \
  --output-dir cmorl_test \
  --seed 42
```

**What this does:**
- **Stage 1**: Trains 3 policies with different preference vectors (1000 timesteps each)
- **Stage 2**: Extends 2 best policies with constrained optimization
- **Output**: Pareto front of 9 policies (3 initial + 2×3 extensions)

**Execution Time:** ~10-15 minutes

#### Medium Training (Research Mode)
```bash
python3 train_cmorl.py \
  --simulation-hours 24 \
  --vms-per-hour 10 \
  --n-policies 6 \
  --timesteps 50000 \
  --n-extend 5 \
  --output-dir cmorl_medium \
  --seed 42
```

**What this does:**
- **Stage 1**: Trains 6 policies (50K timesteps each = ~300K total)
- **Stage 2**: Extends 5 policies (60 steps × 3 objectives = 900 additional steps)
- **Output**: Pareto front of 21 policies

**Execution Time:** ~2-4 hours

#### Full Training (Publication Mode)
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

**Execution Time:** ~8-12 hours

**Parameters:**
- `--simulation-hours`: Episode duration (hours per episode)
- `--vms-per-hour`: VM requests per hour
- `--n-policies`: Number of Stage 1 policies (M=6 from paper)
- `--timesteps`: Timesteps per policy (1.5M from paper)
- `--n-extend`: Number of Stage 2 extensions (N=5 from paper)
- `--output-dir`: Directory for saving models and results
- `--seed`: Random seed for reproducibility

### Step 3: Monitor Training Progress

```bash
# Watch training log
tail -f cmorl_test/training.log

# Check Stage 1 completion
ls -lh cmorl_test/stage1/

# Check Stage 2 completion
ls -lh cmorl_test/stage2/

# View final results
cat cmorl_test/final_results.json | python3 -m json.tool
```

### Step 4: Verify C-MORL Results

```bash
# Check Pareto front size
grep "pareto_front_size" cmorl_test/final_results.json

# View all solutions
python3 << EOF
import json
with open('cmorl_test/final_results.json', 'r') as f:
    results = json.load(f)
    print(f"Pareto Front Size: {results['pareto_front_size']}")
    print(f"Hypervolume: {results['hypervolume']:.2f}")
    print(f"Expected Utility: {results['expected_utility']:.2f}")
    for i, sol in enumerate(results['solutions']):
        obj = sol['objectives']
        print(f"Solution {i+1}: Energy={obj[0]:.2f} kWh, Carbon={obj[1]:.2f} gCO2, Latency={obj[2]:.2f} ms")
EOF
```

**Expected Metrics:**
- Pareto Front Size: 9-21 solutions (depends on training)
- Hypervolume: 0.7-0.9 (higher is better)
- Expected Utility: 0.6-0.8

### Step 5: Stop Gateway

```bash
pkill -9 -f "Py4JGatewayEnhanced"
```

---

## Running Complete Comparison

### Method 1: Using Automated Script

```bash
# Quick comparison (2 hours, 10 VMs)
python3 run_comparison.py \
  --hours 2 \
  --vms-per-hour 5 \
  --cmorl-timesteps 1000 \
  --output-dir comparison_results_quick

# Full comparison (24 hours, 240 VMs)
python3 run_comparison.py \
  --hours 24 \
  --vms-per-hour 10 \
  --cmorl-timesteps 50000 \
  --output-dir comparison_results_full
```

**What this does:**
1. Starts gateway
2. Runs ECMR baseline
3. Restarts gateway
4. Trains C-MORL agent
5. Generates comparison report
6. Stops gateway

**Execution Time:**
- Quick: ~15-20 minutes
- Full: ~3-5 hours

### Method 2: Using Shell Script

```bash
# Make script executable
chmod +x run_final_comparison.sh

# Run comparison
./run_final_comparison.sh
```

**Script contents:**
- Handles gateway lifecycle automatically
- Runs 24-hour simulation with 240 VMs
- Generates comprehensive comparison
- Saves all outputs to timestamped directories

### Method 3: Manual Step-by-Step

#### Step 1: Run ECMR
```bash
pkill -9 -f "Py4JGatewayEnhanced"
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway_ecmr.log 2>&1 &
sleep 5

python3 ecmr_heterogeneous_integration.py \
  --data output/synchronized_dataset_2024.csv \
  --hours 24 \
  --vms-per-hour 10 \
  > comparison_manual/ecmr_output.txt 2>&1

pkill -9 -f "Py4JGatewayEnhanced"
```

#### Step 2: Run C-MORL
```bash
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway_cmorl.log 2>&1 &
sleep 5

python3 train_cmorl.py \
  --simulation-hours 24 \
  --vms-per-hour 10 \
  --n-policies 6 \
  --timesteps 50000 \
  --n-extend 5 \
  --output-dir comparison_manual/cmorl \
  --seed 42

pkill -9 -f "Py4JGatewayEnhanced"
```

#### Step 3: Generate Comparison
```bash
python3 process_comparison_results.py \
  comparison_manual/ecmr_output.txt \
  comparison_manual/cmorl/
```

---

## Understanding Results

### ECMR Output Format

```
================================================================================
SIMULATION RESULTS
================================================================================

 OVERALL STATISTICS
--------------------------------------------------------------------------------
  Total IT Energy: 87.5432 kWh
  Total Facility Energy (PUE-adjusted): 103.2518 kWh
  Average PUE: 1.18
  Total VMs Requested: 240
  Successful VMs: 237
  Failed VMs: 3
  Success Rate: 98.8%

 CARBON & RENEWABLE METRICS
--------------------------------------------------------------------------------
  Total Carbon Emissions: 15234.5678 gCO2
  Weighted Avg Carbon Intensity: 147.6 gCO2/kWh
  Weighted Avg Renewable %: 65.3%

🌱 M5: GREEN DATACENTER UTILIZATION
--------------------------------------------------------------------------------
  Green Datacenter (DG) VMs: 178 (74.79%)
  Brown Datacenter (DB) VMs: 59 (25.21%)
  ➜ Green DC Utilization Score: 0.748/1.000
```

**Key Metrics:**
- **M1 (Resource Efficiency)**: Energy per VM = 103.25 / 240 = 0.43 kWh/VM
- **M2 (Throughput)**: Success Rate = 98.8%
- **M3 (Response Time)**: Check "Avg Network Latency" in per-DC stats
- **M4 (Carbon Reduction)**: Total emissions = 15234.57 gCO2
- **M5 (Green DC Usage)**: 74.79% of VMs in green datacenters

### C-MORL Output Format

```json
{
  "pareto_front_size": 21,
  "hypervolume": 0.8234,
  "expected_utility": 0.7456,
  "solutions": [
    {
      "objectives": [85.23, 14567.89, 7.45],
      "metadata": {
        "policy_id": 1,
        "preference": [0.33, 0.33, 0.34],
        "stage": 1
      }
    }
  ]
}
```

**Interpretation:**
- **objectives[0]**: Energy consumption (kWh) - Lower is better
- **objectives[1]**: Carbon emissions (gCO2) - Lower is better
- **objectives[2]**: Average latency (ms) - Lower is better
- **pareto_front_size**: Number of non-dominated solutions
- **hypervolume**: Quality of Pareto front (higher is better)
- **expected_utility**: Average utility across preferences

### Comparison Report Format

```markdown
# ECMR vs C-MORL Comparison Report

## Performance Comparison

| Metric | ECMR | C-MORL (Best) | C-MORL (Avg) | Improvement |
|--------|------|---------------|--------------|-------------|
| Energy (kWh) | 103.25 | 85.23 | 92.45 | +17.46% |
| Carbon (gCO2) | 15234.57 | 14567.89 | 15012.34 | +4.38% |
| Latency (ms) | 8.50 | 7.45 | 7.89 | +12.35% |
```

**How to Read:**
- **Positive improvement %**: C-MORL is better
- **Best**: Best solution from Pareto front for that objective
- **Avg**: Average across all Pareto solutions

---

## Troubleshooting

### Issue 1: Gateway Connection Failed

**Symptom:**
```
py4j.protocol.Py4JNetworkError: An error occurred while trying to connect to the Java server
```

**Solution:**
```bash
# Check if gateway is running
ps aux | grep Py4JGatewayEnhanced

# Kill and restart
pkill -9 -f "Py4JGatewayEnhanced"
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 &
sleep 10  # Wait longer

# Check gateway log
tail gateway.log
```

### Issue 2: Out of Memory Error

**Symptom:**
```
Java heap space
OutOfMemoryError
```

**Solution:**
```bash
# Increase Java heap size
java -Xmx4G -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 &
```

### Issue 3: Build Failure

**Symptom:**
```
[ERROR] Failed to execute goal
```

**Solution:**
```bash
# Clean Maven cache
mvn clean
rm -rf ~/.m2/repository/

# Rebuild
mvn clean package -U
```

### Issue 4: Python Package Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'gymnasium'
```

**Solution:**
```bash
# Install missing packages
pip install --upgrade pandas numpy py4j torch gymnasium

# Verify installation
python3 -c "import gymnasium; import torch; print('OK')"
```

### Issue 5: Slow Training

**Symptom:**
C-MORL training takes >8 hours for test configuration

**Solution:**
```bash
# Reduce parameters for testing
python3 train_cmorl.py \
  --simulation-hours 2 \
  --vms-per-hour 5 \
  --n-policies 2 \
  --timesteps 500 \
  --n-extend 1
```

### Issue 6: Dataset Not Found

**Symptom:**
```
FileNotFoundError: output/synchronized_dataset_2024.csv
```

**Solution:**
```bash
# Check dataset location
ls -lh output/

# If missing, check data/ directory
ls -lh data/

# Use alternative path
python3 ecmr_heterogeneous_integration.py \
  --data data/synchronized_dataset_2024.csv
```

---

## Quick Reference Commands

### Start Gateway
```bash
pkill -9 -f "Py4JGatewayEnhanced" && \
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced > gateway.log 2>&1 & \
sleep 5
```

### Run ECMR Quick Test
```bash
python3 ecmr_heterogeneous_integration.py --data output/synchronized_dataset_2024.csv --hours 2 --vms-per-hour 5
```

### Run C-MORL Quick Test
```bash
python3 train_cmorl.py --simulation-hours 2 --vms-per-hour 5 --n-policies 3 --timesteps 1000 --n-extend 2 --output-dir cmorl_test
```

### Run Complete Comparison
```bash
python3 run_comparison.py --hours 2 --vms-per-hour 5 --cmorl-timesteps 1000 --output-dir comparison_quick
```

### Stop All Java Processes
```bash
pkill -9 -f "Py4JGatewayEnhanced"
```

---

## Next Steps

After running tests successfully:

1. **Analyze Results**: Review comparison reports and identify key improvements
2. **Generate Visualizations**: Create Pareto front plots and metric comparisons
3. **Document Findings**: Summarize key insights for research paper
4. **Run Extended Tests**: Execute 48-hour or 168-hour simulations for comprehensive analysis

For detailed code reference, see `CODE_REFERENCE.md`.
For test scenarios and expected results, see `TEST_SCENARIOS.md`.
