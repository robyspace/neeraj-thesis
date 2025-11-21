# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an ECMR (Energy and Carbon-aware VM Dispatching with Multi-RES) baseline implementation that integrates CloudSimPlus (Java) with Python-based scheduling algorithms via Py4J. The project simulates datacenter VM placement decisions based on renewable energy availability, carbon intensity, and network latency across European datacenters.

**Architecture Pattern:** Hybrid Java-Python system where CloudSimPlus handles simulation infrastructure and Python implements the ECMR scheduling algorithm.

## Build and Development Commands

### Java (Maven)

```bash
# Build the project and create JAR with dependencies
mvn clean package

# Compile only
mvn compile

# Run tests
mvn test

# Run a single test class
mvn test -Dtest=SimpleTest

# Clean build artifacts
mvn clean

# Run the main CloudSim simulation (standalone)
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.ECMRSimulation

# Start the Py4J Gateway Server (required for Python integration)
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.Py4JGateway
```

### Python

```bash
# Activate virtual environment (if using venv)
source venv/bin/activate  # macOS/Linux

# Run Python-only ECMR simulation (no CloudSim)
python3 src/main/python/ecmr_baseline.py --data output/synchronized_dataset_2024.csv --max-vms 100

# Run integrated ECMR-CloudSim simulation (requires Java gateway to be running)
# Step 1: Start Java Gateway in one terminal
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.Py4JGateway

# Step 2: Run Python integration script in another terminal
python3 src/main/python/ecmr_cloudsim_integrated.py --data output/synchronized_dataset_2024.csv --max-vms 100
```

## High-Level Architecture

### Component Interaction

```
┌─────────────────────┐                    ┌──────────────────────┐
│   Python Layer      │    Py4J Gateway    │    Java Layer        │
│                     │◄──────────────────►│                      │
│ ecmr_baseline.py    │   (Port 25333)     │ ECMRSimulation.java  │
│ - ECMR Algorithm    │                    │ - CloudSimPlus       │
│ - Scheduling Logic  │                    │ - Datacenter Infra   │
│ - Metrics (M1-M4)   │                    │ - VM/Host Management │
│                     │                    │ - Power Models       │
└─────────────────────┘                    └──────────────────────┘
         │                                           │
         │                                           │
         ▼                                           ▼
┌─────────────────────┐                    ┌──────────────────────┐
│  Data Sources       │                    │  CloudSim Core       │
│                     │                    │                      │
│ electricitymaps/    │                    │ - Hosts & VMs        │
│ entsoe/             │                    │ - Cloudlets          │
│ workload/           │                    │ - Brokers            │
└─────────────────────┘                    └──────────────────────┘
```

### Java Architecture (src/main/java/com/ecmr/baseline/)

1. **ECMRSimulation.java** - Main simulation class
   - Creates and manages datacenters, hosts, VMs
   - Uses CloudSimPlus APIs for infrastructure simulation
   - Collects metrics: energy consumption, VM placement, execution times
   - Power model: Linear interpolation between idle and max power based on CPU utilization

2. **Py4JGateway.java** - Bridge between Python and Java
   - Exposes ECMRSimulation methods to Python via Py4J (port 25333)
   - Main entry point for Python integration
   - Methods: `initializeSimulation()`, `createDatacenter()`, `submitVM()`, `runSimulation()`, `getResults()`

3. **SimpleTest.java** (org.example) - Basic CloudSimPlus test
   - Verifies CloudSimPlus setup works correctly
   - Simple example: 1 datacenter, 1 host, 1 VM, 1 cloudlet

### Python Architecture (src/main/python/)

1. **ecmr_baseline.py** - Pure Python ECMR implementation
   - Implements Algorithm 1 from Miao et al. 2024
   - **Step 1:** Classify datacenters as DG (green) or DB (brown) based on renewable percentage
   - **Step 2:** Sort DG datacenters by distance from user location
   - **Step 3:** Use MESF (Most Effective Server First) for server selection
   - **Step 4:** Weighted sum optimization: w1(energy) + w2(carbon) + w3(latency)
   - **Step 5:** Calculate metrics M1-M4:
     - M1: RES Utilization (%)
     - M2: Carbon Reduction (%)
     - M3: Average Response Time (ms)
     - M4: Failure Rate (%)
   - Uses synchronized dataset with hourly renewable energy and carbon intensity data
   - Does NOT use CloudSimPlus (pure Python simulation)

2. **ecmr_cloudsim_integrated.py** - Python-Java integration
   - Connects to Py4JGateway to control CloudSimPlus from Python
   - Submits VMs to CloudSim based on workload data
   - Retrieves placement decisions and metrics from Java simulation
   - Requires Java gateway to be running first

### Key Design Patterns

- **Gateway Pattern:** Py4J bridges Python and Java, allowing Python code to invoke Java CloudSimPlus APIs
- **Two-Mode Operation:**
  1. Pure Python mode (ecmr_baseline.py) - Faster, simpler, no CloudSim
  2. Integrated mode (ecmr_cloudsim_integrated.py) - Full CloudSim simulation with ECMR scheduling
- **Datacenter Classification:** Green (DG) vs Brown (DB) based on renewable energy percentage threshold
- **Resource Model:** CPUs and RAM are tracked at datacenter level; hosts are aggregated
- **Power Model:** Linear model: P = P_idle + (P_max - P_idle) × CPU_utilization

## Data Files

### Input Data Structure

```
data/
├── electricitymaps/         # Carbon intensity data
│   ├── emaps_france.csv
│   ├── emaps_germany.csv
│   ├── emaps_italy.csv
│   ├── emaps_spain.csv
│   └── emaps_sweden.csv
├── entsoe/                  # Renewable energy generation data
│   ├── entsoe-france.csv
│   ├── entsoe-germany.csv
│   ├── entsoe-italy.csv
│   ├── entsoe-spain.csv
│   └── entsoe-sweden.csv
└── workload/                # VM arrival workload patterns

output/
└── synchronized_dataset_2024.csv  # Preprocessed, synchronized data for simulation
```

### Expected CSV Structure

**synchronized_dataset_2024.csv** should contain hourly data with columns:
- `timestamp`: Datetime
- `vm_arrivals`: Number of VM requests per hour
- `{country}_total_renewable_mw`: Renewable generation in MW
- `{country}_carbon_intensity`: gCO2/kWh
- `{country}_renewable_pct`: Percentage of renewable energy
- `{country}_datacenter_type`: 'DG' (green) or 'DB' (brown)

Where `{country}` is one of: italy, sweden, spain, france, germany (lowercase)

## Important Implementation Details

### Java (CloudSimPlus)

- **Java Version:** 21
- **CloudSimPlus Version:** 8.5.7
- **Main Class:** `com.ecmr.baseline.ECMRSimulation`
- **Gateway Class:** `com.ecmr.baseline.Py4JGateway`
- **Dependencies:** Maven handles all dependencies (CloudSimPlus, Py4J, Commons CSV, Gson, SLF4J)

**Key CloudSimPlus concepts:**
- **Host:** Physical server with CPUs (PEs), RAM, bandwidth, storage
- **VM:** Virtual machine allocated to a host
- **Cloudlet:** Workload/task running on a VM
- **Broker:** Manages VM and cloudlet submission and scheduling
- **Datacenter:** Collection of hosts
- **Power Model:** `PowerModelHostSimple` calculates power consumption

### Python (ECMR Algorithm)

- **Scheduler Class:** `ECMRScheduler` in ecmr_baseline.py
- **Datacenter Model:** `Datacenter` dataclass with resources, location, power specs
- **VM Model:** `VM` dataclass with resource requirements
- **Distance Calculation:** Haversine formula for lat/lon to km
- **Default User Location:** Paris (48.8566, 2.3522)
- **Default Weights:** w1=0.33 (energy), w2=0.33 (carbon), w3=0.34 (latency)

**Datacenter Configuration (5 European DCs):**
- DC_IT (Milan): 45.4642°N, 9.1900°E
- DC_SE (Stockholm): 59.3293°N, 18.0686°E
- DC_ES (Madrid): 40.4168°N, -3.7038°W
- DC_FR (Paris): 48.8566°N, 2.3522°E
- DC_DE (Frankfurt): 50.1109°N, 8.6821°E

Each datacenter: 100 servers, 32 CPUs/server, 256GB RAM/server, PUE varies (1.1-1.2)

### Py4J Integration

- **Port:** 25333 (default)
- **Start Gateway:** Must start Java gateway BEFORE running Python integration script
- **Connection:** Python uses `JavaGateway` from `py4j.java_gateway`
- **Data Conversion:** Python dicts → Java HashMaps (handled automatically by Py4J)

## Common Workflows

### Running a Full Simulation

```bash
# 1. Build Java
mvn clean package

# 2. Start Java Gateway (Terminal 1)
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.Py4JGateway

# 3. Run Python integration (Terminal 2)
python3 src/main/python/ecmr_cloudsim_integrated.py \
  --data output/synchronized_dataset_2024.csv \
  --max-vms 100 \
  --output results.json
```

### Running Pure Python ECMR (No CloudSim)

```bash
python3 src/main/python/ecmr_baseline.py \
  --data output/synchronized_dataset_2024.csv \
  --duration 24 \
  --max-vms 100 \
  --output ecmr_results.json
```

### Testing Java Standalone

```bash
mvn package
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.ECMRSimulation
```

## Debugging and Diagnostics

- **diagnose.sh**: Script to check Maven dependencies and CloudSimPlus setup
- **Logging:** Uses SLF4J with Logback (Java), standard print statements (Python)
- **Common Issue:** Py4J connection failure → Ensure Java gateway is running on port 25333
- **JAR Location:** `target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar`

## Key Metrics

The simulation tracks these metrics (per ECMR paper):
- **M1:** RES (Renewable Energy Source) Utilization %
- **M2:** Carbon Reduction % (vs baseline)
- **M3:** Average Response Time (ms)
- **M4:** VM Failure Rate %
- Total Energy (kWh), Renewable Energy (kWh), Carbon Emissions (kg)
- Successful/Failed VM counts

## File Organization

```
src/main/
├── java/
│   ├── com/ecmr/baseline/
│   │   ├── ECMRSimulation.java       # Main simulation logic
│   │   └── Py4JGateway.java          # Python-Java bridge
│   └── org/example/
│       └── SimpleTest.java           # CloudSim verification test
└── python/
    ├── ecmr_baseline.py              # Pure Python ECMR
    └── ecmr_cloudsim_integrated.py   # Python-Java integration
```

## Testing Notes

- No automated test suite currently exists in `src/test/java/`
- **SimpleTest.java** serves as a manual verification test
- Test CloudSimPlus setup: `mvn test` or run SimpleTest directly
- Test Python integration: Run with small `--max-vms` value (e.g., 10) first
