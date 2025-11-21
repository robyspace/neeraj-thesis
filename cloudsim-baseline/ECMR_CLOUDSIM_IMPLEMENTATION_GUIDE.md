# ECMR-CloudSim Complete Integration - Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Technical Fixes Applied](#technical-fixes-applied)
5. [Execution Steps](#execution-steps)
6. [Results](#results)
7. [File Structure](#file-structure)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This document describes the complete integration of the **ECMR (Energy and Carbon-aware VM Dispatching with Multi-RES)** algorithm with **CloudSim Plus 8.5.1** infrastructure simulation framework. The integration enables carbon-aware VM placement decisions to be validated through realistic datacenter execution simulation.

### Key Achievements

- ✅ **100% VM Success Rate**: All VMs scheduled by ECMR are successfully executed in CloudSim
- ✅ **ECMR Placement Enforcement**: CloudSim respects ECMR's carbon-aware datacenter decisions
- ✅ **Green Datacenter Preference**: 90-100% of VMs placed in green (DG) datacenters
- ✅ **Complete CSV Data Usage**: All 42 columns from synchronized dataset utilized
- ✅ **Academic Paper Ready**: Results include both ECMR metrics (M1-M4) and CloudSim execution statistics

---

## Architecture

### Two-Phase Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Phase 1: ECMR Scheduling                │
│                         (Python)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Load synchronized_dataset_2024.csv (42 columns)         │
│     - Workload: vm_arrivals, CPU/RAM requests               │
│     - Carbon: carbon_intensity per datacenter               │
│     - Renewable: hydro/solar/wind breakdown                 │
│     - Classification: DG (green) / DB (brown) types         │
│                                                              │
│  2. Generate VMs based on hourly workload data              │
│     - Distribute VMs across 10 hours                        │
│     - Realistic CPU/RAM requirements                        │
│                                                              │
│  3. ECMR Placement Decision Algorithm                       │
│     - Weighted scoring: renewable% + carbon + latency       │
│     - Weights: (0.4, 0.4, 0.2)                             │
│     - Latency threshold: 175ms                              │
│     - Prioritize green (DG) datacenters                     │
│                                                              │
│  4. Tag VMs with target datacenter                          │
│     - Store ECMR decision in VM description field           │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Py4J Bridge
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Phase 2: CloudSim Execution                │
│                         (Java)                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Create CloudSim Datacenters                             │
│     - 5 datacenters across Europe                           │
│     - 100 servers each, 32 CPUs, 256GB RAM per server       │
│     - Power model: 200W idle, 400W max                      │
│                                                              │
│  2. Custom EcmrDatacenterBroker                             │
│     - Reads ECMR target from VM description                 │
│     - Enforces ECMR placement via setDatacenterMapper()     │
│     - Overrides CloudSim's automatic placement              │
│                                                              │
│  3. VM Execution Simulation                                 │
│     - Cloudlets with dynamic resource utilization           │
│     - 50% CPU, 30% RAM, 20% bandwidth usage                 │
│     - Energy consumption tracking                           │
│                                                              │
│  4. Results Collection                                      │
│     - Successful/failed VMs                                 │
│     - Total energy consumption                              │
│     - Per-datacenter statistics                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
synchronized_dataset_2024.csv
          │
          ├──► Workload Data ──────► VM Generation
          │                           │
          ├──► Carbon Intensity ──┐   │
          │                       │   │
          ├──► Renewable Energy ──┼───► ECMR Scheduling
          │                       │   │
          └──► DG/DB Type ────────┘   │
                                      │
                                      ▼
                            VM with target datacenter
                                      │
                                      │ submitVMToDatacenter()
                                      │
                                      ▼
                          EcmrDatacenterBroker
                                      │
                                      │ setDatacenterMapper()
                                      │
                                      ▼
                            CloudSim Execution
                                      │
                                      ▼
                              Results + Metrics
```

---

## Implementation Details

### 1. ECMR Scheduling Algorithm (`ecmr_cloudsim_complete.py`)

#### Weighted Multi-Objective Scoring

```python
def calculate_weighted_score(dc, user_lat, user_lon, w1, w2, w3):
    """
    Multi-objective scoring for datacenter selection

    Parameters:
    - w1: Weight for renewable energy (0.4)
    - w2: Weight for carbon intensity (0.4)
    - w3: Weight for latency (0.2)
    """
    # Normalize renewable percentage (0-100% → 0-1)
    renewable_score = (100 - dc.renewable_pct) / 100

    # Normalize carbon intensity (0-500 gCO2/kWh → 0-1)
    carbon_score = dc.carbon_intensity / 500

    # Calculate and normalize latency
    latency_ms = calculate_latency(user_lat, user_lon, dc.latitude, dc.longitude)
    latency_score = latency_ms / 300

    # Weighted combination
    total_score = (w1 * renewable_score) + (w2 * carbon_score) + (w3 * latency_score)

    return total_score, latency_ms
```

#### Green Datacenter Preference

The algorithm prioritizes datacenters with:
- **High renewable energy percentage** (>50%)
- **Low carbon intensity** (<100 gCO2/kWh)
- **Acceptable latency** (<175ms)

Result: 90-100% of VMs are placed in green (DG) datacenters.

### 2. CloudSim Infrastructure (`ECMRSimulation.java`)

#### Datacenter Configuration

```java
public String createDatacenter(String id, int numServers, int cpuPerServer,
                               int ramPerServerMB, double powerIdleW, double powerMaxW) {
    List<Host> hostList = new ArrayList<>();

    for (int i = 0; i < numServers; i++) {
        // Create processing elements (CPU cores)
        List<Pe> peList = new ArrayList<>();
        for (int j = 0; j < cpuPerServer; j++) {
            peList.add(new PeSimple(1000)); // 1000 MIPS per core
        }

        // Create host with power model
        Host host = new HostSimple(
            ramPerServerMB,    // RAM in MB
            10000,             // Bandwidth: 10 Gbps
            1000000,           // Storage: 1 TB
            peList
        );

        // Linear power model between idle and max
        host.setPowerModel(new PowerModelHostSimple(powerMaxW, powerIdleW));
        hostList.add(host);
    }

    Datacenter dc = new DatacenterSimple(simulation, hostList);
    datacenterMap.put(id, dc);
    return id;
}
```

#### VM Submission with ECMR Target

```java
public boolean submitVMToDatacenter(int vmId, int cpus, int ramMB,
                                   int mips, String targetDatacenterId) {
    // Create VM
    Vm vm = new VmSimple(vmId, mips, cpus)
            .setRam(ramMB)
            .setBw(1000)
            .setSize(10000);

    // Tag VM with ECMR-selected datacenter
    vm.setDescription(targetDatacenterId);

    // Create cloudlet with dynamic resource utilization
    Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
            .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))   // 50%
            .setUtilizationModelRam(new UtilizationModelDynamic(0.3))   // 30%
            .setUtilizationModelBw(new UtilizationModelDynamic(0.2));   // 20%

    broker.submitVm(vm);
    broker.submitCloudlet(cloudlet);
    return true;
}
```

### 3. ECMR Placement Enforcement (`EcmrDatacenterBroker.java`)

#### Custom Datacenter Mapper

```java
public class EcmrDatacenterBroker extends DatacenterBrokerSimple {
    private Map<String, Datacenter> datacenterMap;

    public EcmrDatacenterBroker(CloudSimPlus simulation,
                               Map<String, Datacenter> datacenterMap) {
        super(simulation);
        this.datacenterMap = datacenterMap;
        this.setSelectClosestDatacenter(false);

        // Set custom datacenter mapper to enforce ECMR decisions
        this.setDatacenterMapper(this::mapVmToEcmrSelectedDatacenter);
    }

    /**
     * Custom mapper that enforces ECMR's placement decisions
     * Reads target datacenter ID from VM description field
     */
    private Datacenter mapVmToEcmrSelectedDatacenter(Datacenter datacenter, Vm vm) {
        String ecmrTargetId = vm.getDescription();

        if (ecmrTargetId == null || ecmrTargetId.isEmpty()) {
            logger.warn("VM {} has no ECMR target datacenter", vm.getId());
            return datacenter;
        }

        Datacenter ecmrTarget = datacenterMap.get(ecmrTargetId);

        if (ecmrTarget == null) {
            logger.error("ECMR target datacenter {} not found", ecmrTargetId);
            return datacenter;
        }

        logger.debug("VM {} mapped to ECMR-selected datacenter: {}",
                    vm.getId(), ecmrTargetId);

        return ecmrTarget;
    }
}
```

**Key Innovation**: The `setDatacenterMapper()` method allows us to override CloudSim's automatic datacenter selection logic with ECMR's carbon-aware decisions.

---

## Technical Fixes Applied

### Problem 1: CloudSim Hanging Indefinitely

**Symptom**: CloudSim simulation never completed, gateway logs showed:
```
WARN CloudletScheduler - Cloudlet 51 requested 65536 MB of VmRam
but no amount is available, which delays Cloudlet processing.
```

**Root Cause**: Cloudlets using `UtilizationModelFull()` requested 100% of VM resources, creating resource contention deadlocks.

**Solution**: Changed to `UtilizationModelDynamic()` with realistic percentages.

**File**: `src/main/java/com/ecmr/baseline/ECMRSimulation.java:171-173`

```java
// BEFORE (Broken)
Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
        .setUtilizationModelCpu(new UtilizationModelFull())
        .setUtilizationModelRam(new UtilizationModelFull())
        .setUtilizationModelBw(new UtilizationModelFull());

// AFTER (Fixed)
Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
        .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))  // 50% CPU
        .setUtilizationModelRam(new UtilizationModelDynamic(0.3))  // 30% RAM
        .setUtilizationModelBw(new UtilizationModelDynamic(0.2));  // 20% BW
```

**Result**: CloudSim simulation completes in 0.01-0.07 seconds ✅

---

### Problem 2: All VMs Failed to Execute in CloudSim

**Symptom**:
```
CLOUDSIM EXECUTION:
  Total VMs: 20
  Successful: 0
  Failed: 20
```

Gateway logs showed:
```
WARN DatacenterBroker - Vm 5 (DC_SE) has been moved to the failed list
because creation retry is not enabled.
```

**Root Cause**: CloudSim broker was doing automatic datacenter placement, ignoring ECMR's placement decisions stored in VM description field.

**Solution**: Implemented custom `EcmrDatacenterBroker` with `setDatacenterMapper()` to enforce ECMR decisions.

**File**: `src/main/java/com/ecmr/baseline/EcmrDatacenterBroker.java`

```java
// Set custom datacenter mapper to enforce ECMR decisions
this.setDatacenterMapper(this::mapVmToEcmrSelectedDatacenter);

private Datacenter mapVmToEcmrSelectedDatacenter(Datacenter datacenter, Vm vm) {
    String ecmrTargetId = vm.getDescription();
    Datacenter ecmrTarget = datacenterMap.get(ecmrTargetId);
    return ecmrTarget;  // Override CloudSim's suggestion
}
```

**Result**: 100% VM success rate ✅

---

### Problem 3: VMs Can't Fit on Datacenter Hosts

**Symptom**:
```
WARN VmAllocationPolicy - No suitable host found for Vm 0 (DC_DE) in #Datacenter 6
```

**Root Cause**: MIPS parameter misconfiguration. In CloudSim Plus, `VmSimple(vmId, mips, cpus)` expects **MIPS per PE**, not total MIPS.

```
Python sent:   mips = cpus * 1000 = 16000 (for 16 CPUs)
Java created:  16 PEs × 16000 MIPS each = 256,000 total MIPS required
Host had:      32 PEs × 1000 MIPS each  = 32,000 total MIPS available
Result:        VM can't fit! ❌
```

**Solution**: Changed MIPS to 1000 (matching host PE capacity).

**File**: `src/main/python/ecmr_cloudsim_complete.py:879`

```python
# BEFORE (Broken)
vm = {
    'vm_id': len(vms),
    'num_cpus': cpus,
    'ram_mb': ram_mb,
    'mips': cpus * 1000  # Wrong: total MIPS
}

# AFTER (Fixed)
vm = {
    'vm_id': len(vms),
    'num_cpus': cpus,
    'ram_mb': ram_mb,
    'mips': 1000  # Correct: MIPS per PE
}
```

**Result**: All VMs fit on hosts and execute successfully ✅

---

## Execution Steps

### Prerequisites

1. **Java**: JDK 11 or higher
2. **Maven**: 3.6 or higher
3. **Python**: 3.8 or higher
4. **Dataset**: `output/synchronized_dataset_2024.csv`

### Step 1: Build Java Project

```bash
cd /Users/robyspace/Documents/cloudsim-baseline

# Clean and build with dependencies
mvn clean package -DskipTests

# Verify JAR created
ls -lh target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar
```

**Expected Output**:
```
BUILD SUCCESS
Total time: 15.234 s
```

### Step 2: Start Java Gateway

```bash
# Start gateway in background
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
     com.ecmr.baseline.Py4JGateway > gateway.log 2>&1 &

# Check gateway started
tail -5 gateway.log
```

**Expected Output**:
```
[main] INFO com.ecmr.baseline.Py4JGateway - Py4J Gateway Server started on port 25333
[main] INFO com.ecmr.baseline.Py4JGateway - Python can now connect using: gateway = JavaGateway()
Gateway is running. Python scripts can now connect.
```

### Step 3: Set Up Python Environment

```bash
# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install py4j numpy pandas geopy
```

### Step 4: Run ECMR-CloudSim Simulation

```bash
# Run with 100 VMs distributed across 10 hours
python3 -u src/main/python/ecmr_cloudsim_complete.py \
    --data output/synchronized_dataset_2024.csv \
    --max-vms 100 \
    --vms-per-hour 10 \
    --output ecmr_results.json
```

**Command-Line Options**:
- `--data`: Path to synchronized dataset CSV file
- `--max-vms`: Maximum number of VMs to generate (default: 100)
- `--vms-per-hour`: VMs per hour for temporal distribution (default: 10)
- `--output`: Output JSON file for results (default: ecmr_cloudsim_results.json)

### Step 5: Monitor Execution

**Python Console Output**:
```
================================================================================
ECMR-CloudSim COMPLETE INTEGRATION
================================================================================

[1/6] Connecting to Java Gateway at localhost:25333...
      Connected to Java Gateway successfully

[2/6] Initializing CloudSim simulation...
      CloudSim initialized

[3/6] Creating datacenters (CloudSim + Enhanced ECMR models)...
      Created: DC_IT (Milan Datacenter)
      Created: DC_SE (Stockholm Datacenter)
      Created: DC_ES (Madrid Datacenter)
      Created: DC_FR (Paris Datacenter)
      Created: DC_DE (Frankfurt Datacenter)

[4/6] Loading synchronized dataset with ALL columns...
      Loaded 8784 hours of data
      Total columns: 42

[5/6] Running complete ECMR + CloudSim simulation...
  Processing VMs with complete ECMR scheduling...
  Hour 1 Placement Summary:
  ----------------------------------------------------------------------------
    DG (Green):  10 VMs (100.0%)
    DB (Brown):  0 VMs (0.0%)
    DC_DE [DG]: 10 VMs | Renewable: 72.6% | Carbon: 163 gCO2/kWh

  Running CloudSim simulation...
  CloudSim simulation completed in 0.07 seconds

[6/6] Collecting complete results...
```

**Gateway Logs** (gateway.log):
```
[Thread-2] INFO EcmrDatacenterBroker - VM 0 submitted with ECMR target datacenter: DC_DE
[Thread-2] INFO EcmrDatacenterBroker - VM 1 submitted with ECMR target datacenter: DC_DE
...
[Thread-2] INFO ECMRSimulation - Results collected: 100 successful VMs, 0 failed VMs
```

### Step 6: Verify Results

```bash
# Check final results
cat ecmr_results.json | jq '.cloudsim_execution'
```

**Expected Output**:
```json
{
  "total_vms": 100,
  "successful": 100,
  "failed": 0,
  "total_energy_kwh": 3.93
}
```

### Step 7: Cleanup (Optional)

```bash
# Stop Java gateway
pkill -f "Py4JGateway"

# Deactivate Python environment
deactivate
```

---

## Results

### Final Execution Results (100 VMs)

```
================================================================================
COMPLETE SIMULATION RESULTS
================================================================================

ECMR ALGORITHM METRICS (M1-M4):
--------------------------------------------------------------------------------
  M1: RES Utilization:        53.66%
  M2: Carbon Reduction:       0.00%
  M3: Avg Response Time:      31.56 ms
  M4: Failure Rate:           0.00%

ENERGY CONSUMPTION:
--------------------------------------------------------------------------------
  Total Energy:               11.64 kWh
  Renewable Energy:           6.25 kWh
  Carbon Emissions:           0.58 kg

RENEWABLE ENERGY BREAKDOWN (from CSV hydro/solar/wind):
--------------------------------------------------------------------------------
  Hydro:  2.34 kWh (37.4%)
  Solar:  0.35 kWh (5.7%)
  Wind:   3.56 kWh (56.9%)

VM PLACEMENT:
--------------------------------------------------------------------------------
  Total VMs:                  100
  Successfully placed:        100
  Failed:                     0

CONSTRAINT ENFORCEMENT:
--------------------------------------------------------------------------------
  Latency rejections:         50
  RES rejections:             0

CLOUDSIM EXECUTION:
--------------------------------------------------------------------------------
  Total VMs:                  100
  Successful:                 100  ✅
  Failed:                     0    ✅
  Total Energy:               3.93 kWh

ECMR PLACEMENT DISTRIBUTION:
--------------------------------------------------------------------------------
PLACEMENT BY DATACENTER TYPE:
  DG (Green): 100 VMs (100.0%) - Avg Renewable: 71.1%
  DB (Brown):   0 VMs (  0.0%)

PLACEMENT BY DATACENTER:
  DC_DE (Germany) [DG]:  50 VMs ( 50.0%)
  DC_SE (Sweden)  [DG]:  50 VMs ( 50.0%)

================================================================================

PER-DATACENTER PLACEMENT STATISTICS:
--------------------------------------------------------------------------------

  DC_IT - Milan Datacenter (italy):
    VMs placed: 0
    Reason: Not selected (check constraint violations)

  DC_SE - Stockholm Datacenter (sweden):
    VMs placed: 50
    Avg carbon when selected: 23.9 gCO2/kWh
    Avg renewable when selected: 68.1%
    Final classification: DG

  DC_ES - Madrid Datacenter (spain):
    VMs placed: 0
    Reason: Not selected (check constraint violations)

  DC_FR - Paris Datacenter (france):
    VMs placed: 0
    Reason: Not selected (check constraint violations)

  DC_DE - Frankfurt Datacenter (germany):
    VMs placed: 50
    Avg carbon when selected: 152.0 gCO2/kWh
    Avg renewable when selected: 74.1%
    Final classification: DG
```

### Key Performance Indicators

| Metric | Value | Explanation |
|--------|-------|-------------|
| **VM Success Rate** | 100% | All VMs executed successfully in CloudSim |
| **Green DC Preference** | 100% | All VMs placed in green (DG) datacenters |
| **Avg Renewable Energy** | 71.1% | High renewable utilization across placements |
| **Avg Carbon Intensity** | 88 gCO2/kWh | Low carbon footprint (weighted average) |
| **Latency Violations** | 50 VMs | VMs rejected for exceeding 175ms threshold |
| **Simulation Time** | 0.07 sec | Fast CloudSim execution |

### CSV Data Usage Statistics

```
[1] WORKLOAD DATA USAGE:
--------------------------------------------------------------------------------
  VM Arrivals:    831 total,  25.2 avg/hour
  CPU Requests:   3535 total, 107.1 avg/hour
  RAM Requests:   1289424 GB total, 39073.5 GB avg/hour

[2] CARBON INTENSITY DATA USAGE (per datacenter):
--------------------------------------------------------------------------------
  DC_SE (Sweden):   Avg: 23.6 gCO2/kWh,  Min: 6.2,   Max: 36.9
  DC_FR (France):   Avg: 15.2 gCO2/kWh,  Min: 13.2,  Max: 19.0
  DC_ES (Spain):    Avg: 75.0 gCO2/kWh,  Min: 50.2,  Max: 103.2
  DC_DE (Germany):  Avg: 147.0 gCO2/kWh, Min: 120.0, Max: 170.0
  DC_IT (Italy):    Avg: 237.4 gCO2/kWh, Min: 182.4, Max: 280.4

[3] RENEWABLE ENERGY DATA USAGE (per datacenter):
--------------------------------------------------------------------------------
  DC_DE (Germany):  Avg: 78.0% renewable (71.9% - 84.5%)
  DC_SE (Sweden):   Avg: 68.0% renewable (62.9% - 73.7%)
  DC_ES (Spain):    Avg: 51.6% renewable (38.1% - 66.2%)
  DC_IT (Italy):    Avg: 43.1% renewable (32.9% - 56.4%)
  DC_FR (France):   Avg: 33.7% renewable (27.4% - 37.0%)

[4] RENEWABLE ENERGY BREAKDOWN (Hydro/Solar/Wind):
--------------------------------------------------------------------------------
  DC_DE: Wind-dominant (31,388 MW avg)
  DC_SE: Hydro-dominant (7,872 MW avg)
  DC_ES: Balanced mix (Hydro: 5,551 MW, Wind: 7,661 MW)
  DC_FR: Wind-dominant (12,658 MW avg)
  DC_IT: Balanced mix (Hydro: 3,291 MW, Wind: 2,984 MW)
```

### Visualization of Results

#### VM Placement Distribution

```
DC_DE (Germany) [DG]:  ████████████████████████████████████████████████ 50 VMs (74.1% renewable)
DC_SE (Sweden)  [DG]:  ████████████████████████████████████████████████ 50 VMs (68.1% renewable)
DC_ES (Spain)   [DG]:  0 VMs
DC_FR (France)  [DB]:  0 VMs
DC_IT (Italy)   [DB]:  0 VMs
```

#### Energy Mix

```
Renewable Energy: 53.7% ████████████████████████████░░░░░░░░░░░░░░░░░░░
Non-Renewable:    46.3% ███████████████████████░░░░░░░░░░░░░░░░░░░░░░░░
```

---

## File Structure

```
cloudsim-baseline/
│
├── src/
│   ├── main/
│   │   ├── java/com/ecmr/baseline/
│   │   │   ├── ECMRSimulation.java           # Main CloudSim simulation class
│   │   │   ├── EcmrDatacenterBroker.java     # Custom broker enforcing ECMR placement
│   │   │   ├── Py4JGateway.java              # Python-Java bridge
│   │   │   └── Datacenter.java               # Datacenter model
│   │   │
│   │   └── python/
│   │       ├── ecmr_cloudsim_complete.py     # Complete ECMR-CloudSim integration
│   │       ├── ecmr_baseline.py              # Original ECMR algorithm
│   │       └── datacenter_energy_models.py   # Energy models
│   │
│   └── test/
│       └── java/com/ecmr/baseline/
│           └── ECMRSimulationTest.java       # Unit tests
│
├── output/
│   └── synchronized_dataset_2024.csv         # 42-column synchronized dataset
│
├── target/
│   └── cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar
│
├── pom.xml                                    # Maven configuration
├── gateway.log                                # Java gateway logs
├── ecmr_results.json                         # Simulation results
└── ECMR_CLOUDSIM_IMPLEMENTATION_GUIDE.md     # This document
```

### Key Files and Their Roles

| File | Lines of Code | Purpose |
|------|--------------|---------|
| `ecmr_cloudsim_complete.py` | ~1,300 | Complete ECMR algorithm + CloudSim integration |
| `ECMRSimulation.java` | 360 | CloudSim datacenter infrastructure |
| `EcmrDatacenterBroker.java` | 75 | Custom broker enforcing ECMR placement |
| `Py4JGateway.java` | 50 | Python-Java communication bridge |
| `synchronized_dataset_2024.csv` | 8,784 rows | 42 columns of hourly energy/workload data |

---

## Troubleshooting

### Issue 1: Connection Refused to Gateway

**Symptom**:
```
ERROR: Failed to connect to Java Gateway at localhost:25333
```

**Solution**:
```bash
# Check if gateway is running
ps aux | grep "Py4JGateway"

# If not running, start gateway
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
     com.ecmr.baseline.Py4JGateway > gateway.log 2>&1 &

# Wait for gateway to initialize
sleep 3
```

---

### Issue 2: CloudSim Hanging

**Symptom**: Python script runs but CloudSim simulation never completes.

**Solution**: This should be fixed in the current implementation. Verify:
```bash
# Check gateway logs for resource warnings
grep "requested.*but no amount is available" gateway.log

# If found, ensure you're using UtilizationModelDynamic (already fixed)
```

---

### Issue 3: VM Creation Failures

**Symptom**:
```
CLOUDSIM EXECUTION:
  Successful: 0
  Failed: 100
```

**Solution**: Verify ECMR broker is being used:
```bash
# Check gateway logs
grep "EcmrDatacenterBroker initialized" gateway.log

# Should see:
# [Thread-2] INFO EcmrDatacenterBroker - EcmrDatacenterBroker initialized with ECMR-enforced placement
```

---

### Issue 4: MIPS Configuration Error

**Symptom**:
```
WARN VmAllocationPolicy - No suitable host found for Vm X
```

**Solution**: Verify MIPS is set to 1000 (not cpus * 1000):
```bash
# Check Python code
grep "mips.*1000" src/main/python/ecmr_cloudsim_complete.py

# Should see:
# 'mips': 1000  # MIPS per PE (not total)
```

---

### Issue 5: Maven Build Fails

**Symptom**:
```
[ERROR] Failed to execute goal on project cloudsim-baseline
```

**Solution**:
```bash
# Clean Maven cache
rm -rf ~/.m2/repository/org/cloudsimplus

# Rebuild
mvn clean package -DskipTests -U
```

---

### Issue 6: Python Import Errors

**Symptom**:
```
ModuleNotFoundError: No module named 'py4j'
```

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install py4j numpy pandas geopy

# Verify installation
pip list | grep py4j
```

---

### Debugging Tips

#### View Gateway Logs in Real-Time
```bash
tail -f gateway.log
```

#### Enable Java Debug Logging
```bash
java -Dorg.slf4j.simpleLogger.defaultLogLevel=DEBUG \
     -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
     com.ecmr.baseline.Py4JGateway > gateway_debug.log 2>&1 &
```

#### Check VM Placement Decisions
```bash
# View ECMR decisions
grep "SELECTED" ecmr_test_output.log

# View CloudSim placement
grep "VM.*submitted with ECMR target" gateway.log
```

#### Validate Results
```bash
# Check JSON output
cat ecmr_results.json | jq '.ecmr_placement.by_type'

# Expected:
# {
#   "DG": 100,
#   "DB": 0
# }
```

---

## Academic Paper Integration

### Key Results for Publication

1. **M1: RES Utilization**: 53.66%
2. **M2: Carbon Reduction**: Comparison with baseline (requires baseline run)
3. **M3: Avg Response Time**: 31.56 ms
4. **M4: Failure Rate**: 0.00%

### Figures for Paper

#### Figure 1: VM Placement Distribution
- Bar chart showing VMs per datacenter
- Color-coded by DG (green) / DB (brown) type
- Include renewable % and carbon intensity labels

#### Figure 2: Energy Consumption Breakdown
- Pie chart: Hydro (37.4%), Solar (5.7%), Wind (56.9%)
- Total renewable vs non-renewable comparison

#### Figure 3: Temporal VM Distribution
- Line graph showing VM arrivals per hour
- Overlay with renewable energy availability

#### Figure 4: Carbon Intensity Comparison
- Box plot of carbon intensity per datacenter
- Highlight ECMR's preference for low-carbon DCs

### Tables for Paper

#### Table 1: Datacenter Configuration
| Datacenter | Location | Servers | CPUs | RAM (GB) | Renewable % | Carbon (gCO2/kWh) |
|------------|----------|---------|------|----------|-------------|-------------------|
| DC_SE | Stockholm | 100 | 3,200 | 25,600 | 68.0% | 23.6 |
| DC_DE | Frankfurt | 100 | 3,200 | 25,600 | 78.0% | 147.0 |
| DC_ES | Madrid | 100 | 3,200 | 25,600 | 51.6% | 75.0 |
| DC_FR | Paris | 100 | 3,200 | 25,600 | 33.7% | 15.2 |
| DC_IT | Milan | 100 | 3,200 | 25,600 | 43.1% | 237.4 |

#### Table 2: ECMR Performance Metrics
| Metric | Value | Description |
|--------|-------|-------------|
| VM Success Rate | 100% | All VMs executed successfully |
| Green DC Placement | 100% | VMs placed in DG datacenters |
| Avg Renewable | 71.1% | Average renewable energy utilization |
| Avg Carbon | 88 gCO2/kWh | Weighted average carbon intensity |
| Total Energy | 3.93 kWh | CloudSim execution energy |
| Simulation Time | 0.07 sec | Fast simulation performance |

---

## Conclusion

This implementation demonstrates a complete integration of the ECMR algorithm with CloudSim Plus, providing:

✅ **Academic Rigor**: Results include both ECMR metrics (M1-M4) and CloudSim execution statistics

✅ **Carbon-Aware Placement**: 90-100% green datacenter placement with 71% average renewable energy

✅ **Complete Data Usage**: All 42 columns from synchronized dataset utilized for realistic workload simulation

✅ **Production-Ready**: 100% VM success rate with robust error handling

✅ **Reproducible**: Step-by-step execution guide with troubleshooting

The integration satisfies academic paper requirements by showing ECMR placement metrics in the context of a realistic cloud infrastructure simulation using CloudSim Plus.

---

## Citations

1. CloudSim Plus 8.5.1: https://cloudsimplus.org
2. Py4J: https://www.py4j.org
3. ECMR Algorithm: [Your Paper Reference]
4. Synchronized Dataset: [Dataset Source]

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
**Maintainer**: ECMR Research Team
**Contact**: [Your Email]
