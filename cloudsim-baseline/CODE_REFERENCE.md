# Code Reference Document

## Overview

This document provides a comprehensive reference for the ECMR and C-MORL implementations, including architecture, key classes, algorithms, and integration points.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [ECMR Implementation](#ecmr-implementation)
3. [C-MORL Implementation](#c-morl-implementation)
4. [CloudSim Integration](#cloudsim-integration)
5. [Utility Modules](#utility-modules)
6. [Configuration](#configuration)

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Layer (RL Agent)                  │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │  ECMR Algorithm          │  │  C-MORL Agent            │ │
│  │  - Greedy placement      │  │  - Multi-objective PPO   │ │
│  │  - Carbon-aware scoring  │  │  - Pareto optimization   │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┤
│  │              Py4J Bridge (Java Gateway)                   │
│  └──────────────────────────────────────────────────────────┤
│                                                               │
│                    Java Layer (CloudSim)                      │
│  ┌──────────────────────────────────────────────────────────┤
│  │  Datacenter Infrastructure                                │
│  │  - 5 European datacenters                                 │
│  │  - 3 heterogeneous server types (120 servers/DC)          │
│  │  - Non-linear power models (11-point SpecPower curves)    │
│  │  - 4 VM types (small, medium, large, xlarge)              │
│  └──────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────────┤
│  │  Simulation Engine                                        │
│  │  - VM allocation and scheduling                           │
│  │  - Energy consumption calculation                         │
│  │  - Resource utilization tracking                          │
│  └──────────────────────────────────────────────────────────┘
```

### Data Flow

```
Carbon Intensity CSV → ECMR/C-MORL → Datacenter Selection → CloudSim
                                                              ↓
                                        VM Placement + Energy Calculation
                                                              ↓
                                            Results (Energy, Carbon, Latency)
```

---

## ECMR Implementation

### File: `ecmr_heterogeneous_integration.py` (633 lines)

#### Key Classes

##### 1. `DatacenterState` (Lines 66-88)
Tracks dynamic state of each datacenter.

**Attributes:**
```python
id: str                    # Datacenter identifier (e.g., 'DC_ITALY')
name: str                  # Human-readable name
country: str               # Country code for CSV lookup
latitude: float            # Geographic coordinates
longitude: float
pue: float                 # Power Usage Effectiveness

# Dynamic state (updated each hour from CSV)
carbon_intensity: float    # gCO2/kWh
renewable_pct: float       # Percentage renewable energy
dc_type: str              # 'DG' (Green) or 'DB' (Brown)
hydro_mw: float           # Hydro generation (MW)
solar_mw: float           # Solar generation (MW)
wind_mw: float            # Wind generation (MW)

# Tracking
vms_placed: int           # Total VMs placed in this DC
energy_kwh: float         # Cumulative energy consumption
carbon_kg: float          # Cumulative carbon emissions
```

##### 2. `ECMRHeterogeneousScheduler` (Lines 90-210)
ECMR placement algorithm implementation.

**Constructor:**
```python
def __init__(self,
             datacenters: Dict[str, DatacenterState],
             user_location: Tuple[float, float] = (48.8566, 2.3522),
             weights: Tuple[float, float, float] = (0.5, 0.3, 0.2)):
    """
    Args:
        datacenters: Dictionary of datacenter states
        user_location: (latitude, longitude) of user
        weights: (w_carbon, w_renewable, w_latency) importance weights
    """
```

**Key Method: `select_datacenter()` (Lines 144-209)**

Algorithm:
```python
def select_datacenter(self, vm: Dict) -> str:
    """
    ECMR Algorithm: Multi-objective datacenter selection

    Score = w_carbon * S_carbon + w_renewable * S_renewable + w_latency * S_latency

    Where:
        S_carbon = 1 - normalize(carbon_intensity)     # Lower is better
        S_renewable = normalize(renewable_pct)          # Higher is better
        S_latency = 1 - normalize(latency)              # Lower is better

    Returns: datacenter_id with highest score
    """
```

**Scoring Components:**

1. **Carbon Score (Lines 175):**
   ```python
   s_carbon = 1 - self.normalize(dc.carbon_intensity, min_carbon, max_carbon)
   ```

2. **Renewable Score (Line 178):**
   ```python
   s_renewable = self.normalize(dc.renewable_pct, min_renewable, max_renewable)
   ```

3. **Latency Score (Lines 181-182):**
   ```python
   latency = self.calculate_latency(dc)
   s_latency = 1 - self.normalize(latency, min_latency, max_latency)
   ```

4. **Datacenter Type Penalty (Lines 185-186):**
   ```python
   # 30% penalty for brown datacenters
   dc_type_multiplier = 0.7 if dc.dc_type == 'DB' else 1.0
   ```

5. **Final Score (Lines 189-192):**
   ```python
   base_score = (self.w_carbon * s_carbon +
                 self.w_renewable * s_renewable +
                 self.w_latency * s_latency)
   score = base_score * dc_type_multiplier
   ```

##### 3. `ECMRHeterogeneousIntegration` (Lines 212-602)
Main integration class orchestrating ECMR algorithm and CloudSim.

**Key Methods:**

1. **`create_heterogeneous_datacenters()` (Lines 253-278)**
   ```python
   def create_heterogeneous_datacenters(self):
       """
       Creates 5 datacenters, each with:
       - 40 × Huawei RH2285 V2 (16 cores, 24GB RAM, 2.3GHz)
       - 40 × Huawei RH2288H V3 (40 cores, 64GB RAM, 3.6GHz)
       - 40 × Lenovo SR655 V3 (96 cores, 192GB RAM, 2.4GHz)
       Total: 120 servers per datacenter
       """
       for dc_id, config in DATACENTERS.items():
           self.app.createHeterogeneousDatacenter(dc_id, 40, config['pue'])
   ```

2. **`update_datacenter_state()` (Lines 280-310)**
   ```python
   def update_datacenter_state(self, hour_data: pd.Series):
       """
       Updates each datacenter with current hour's data:
       - Carbon intensity from {country}_carbon_intensity column
       - Renewable % from {country}_renewable_pct column
       - DC type from {country}_datacenter_type column
       - Renewable breakdown (hydro, solar, wind)
       """
   ```

3. **`run_simulation()` (Lines 317-415)**
   ```python
   def run_simulation(self, hours: int = 24, vms_per_hour: int = 10):
       """
       Main simulation loop:
       1. For each hour:
          a. Update datacenter states with current carbon data
          b. Generate VMs with random types and user locations
          c. ECMR selects optimal datacenter for each VM
          d. Submit VM to CloudSim
          e. Track placement decisions
       2. Run CloudSim simulation
       3. Collect results
       """
   ```

4. **`print_results()` (Lines 417-601)**
   Generates comprehensive results with 5 sections:
   - Overall statistics (energy, VMs, success rate)
   - Carbon & renewable metrics (emissions, carbon intensity, renewable %)
   - Green datacenter utilization (M5 metric)
   - Per-datacenter details
   - VM distribution and analysis

### Constants and Configuration

```python
# European datacenter locations (Lines 29-35)
DATACENTERS = {
    'DC_ITALY': {'name': 'Milan DC', 'country': 'italy', ...},
    'DC_FRANCE': {'name': 'Paris DC', 'country': 'france', ...},
    'DC_SWEDEN': {'name': 'Stockholm DC', 'country': 'sweden', ...},
    'DC_NETHERLANDS': {'name': 'Amsterdam DC', 'country': 'netherlands', ...},
    'DC_SPAIN': {'name': 'Madrid DC', 'country': 'spain', ...}
}

# VM type distribution (Lines 62-63)
VM_TYPES = ['small', 'medium', 'large', 'xlarge']
VM_TYPE_WEIGHTS = [0.4, 0.3, 0.2, 0.1]  # Matches Miao2024.pdf Table 5

# European cities for user locations (Lines 38-59)
EUROPEAN_CITIES = [
    ('Paris', 48.8566, 2.3522),
    ('London', 51.5074, -0.1278),
    # ... 18 more cities
]
```

---

## C-MORL Implementation

### File: `cmorl_environment.py` (670 lines)

#### Key Class: `CMORLEnvironment` (Lines 47-670)
Gymnasium-compatible environment for multi-objective RL.

**Constructor:**
```python
def __init__(self,
             carbon_data_path: str = 'output/synchronized_dataset_2024.csv',
             simulation_hours: int = 24,
             vms_per_hour: int = 10,
             user_location: Tuple[float, float] = (48.8566, 2.3522),
             random_seed: int = 42):
```

**State Space (132 dimensions):**
```python
observation_space = spaces.Box(
    low=-np.inf, high=np.inf, shape=(132,), dtype=np.float32
)

# State breakdown:
[0:4]     # VM requirements (cores, ram, storage, latency_sensitivity)
[4:44]    # Per-datacenter metrics (5 DCs × 8 features)
          # Features: carbon, renewable, pue, cpu_util, ram_util,
          #           available_cpu, available_ram, distance
[44:49]   # DC type indicators (5 × 1 binary: 1=Green, 0=Brown)
[49:79]   # Renewable forecasts (5 DCs × 3 sources × 2 horizons)
[79:132]  # Historical performance (53 dimensions)
          # - Energy/carbon/latency windows
          # - Placement success rates
          # - Resource utilization trends
```

**Action Space:**
```python
action_space = spaces.Discrete(5)  # Select one of 5 datacenters
```

**Reward Structure:**
```python
reward = {
    'R_energy': -normalized_energy,      # Negative energy (minimize)
    'R_carbon': -normalized_carbon,      # Negative carbon (minimize)
    'R_latency': -normalized_latency     # Negative latency (minimize)
}
```

**Key Methods:**

1. **`reset()` (Lines 150-190):**
   ```python
   def reset(self, seed=None):
       """
       Reset environment for new episode:
       1. Initialize CloudSim simulation
       2. Create heterogeneous datacenters
       3. Load carbon data for episode
       4. Reset tracking variables
       5. Generate first VM request
       Returns: initial_state, info
       """
   ```

2. **`step()` (Lines 192-320):**
   ```python
   def step(self, action: int):
       """
       Execute one step:
       1. Map action (0-4) to datacenter
       2. Submit VM to CloudSim
       3. Update datacenter state
       4. Calculate rewards (energy, carbon, latency)
       5. Update historical metrics
       6. Generate next VM or mark episode done
       Returns: next_state, reward_dict, done, truncated, info
       """
   ```

3. **`_compute_state()` (Lines 322-450):**
   ```python
   def _compute_state(self):
       """
       Construct 132-dimensional state vector:
       - Current VM requirements
       - Real-time datacenter metrics from CloudSim
       - Datacenter type indicators
       - Renewable energy forecasts
       - Historical performance windows
       """
   ```

4. **`_calculate_rewards()` (Lines 452-550):**
   ```python
   def _calculate_rewards(self, datacenter_id: str, vm_type: str):
       """
       Calculate multi-objective rewards:
       1. Query CloudSim for energy consumption
       2. Compute carbon = energy × carbon_intensity × PUE
       3. Calculate latency based on distance
       4. Normalize rewards to [-1, 0] range
       """
   ```

### File: `cmorl_agent.py` (395 lines)

#### Key Class: `CMORLAgent` (Lines 30-395)
Multi-objective PPO agent with preference-based scalarization.

**Constructor:**
```python
def __init__(self,
             state_dim: int = 132,
             action_dim: int = 5,
             preference_vector: np.ndarray = None,
             learning_rate: float = 3e-4,
             gamma: float = 0.99,
             gae_lambda: float = 0.95,
             clip_epsilon: float = 0.2):
```

**Neural Network Architecture:**

1. **Policy Network (Lines 45-80):**
   ```python
   self.policy = nn.Sequential(
       nn.Linear(132, 256),
       nn.ReLU(),
       nn.Linear(256, 256),
       nn.ReLU(),
       nn.Linear(256, 5),      # 5 datacenter actions
       nn.Softmax(dim=-1)
   )
   ```

2. **Value Networks (Lines 82-120):**
   ```python
   # Separate value head for each objective
   self.value_net_energy = nn.Sequential(
       nn.Linear(132, 256), nn.ReLU(),
       nn.Linear(256, 128), nn.ReLU(),
       nn.Linear(128, 1)
   )

   self.value_net_carbon = nn.Sequential(...)  # Same architecture
   self.value_net_latency = nn.Sequential(...)
   ```

**Key Methods:**

1. **`select_action()` (Lines 122-150):**
   ```python
   def select_action(self, state, deterministic=False):
       """
       Select action using policy network:
       1. Forward pass through policy network
       2. Sample from categorical distribution (or argmax if deterministic)
       3. Return action and log probability
       """
   ```

2. **`update()` (Lines 152-280):**
   ```python
   def update(self, states, actions, old_log_probs, rewards_dict, dones,
              epochs=10, batch_size=64):
       """
       PPO update with multi-objective rewards:
       1. Compute advantages using GAE for each objective
       2. Scalarize rewards using preference vector
       3. PPO clipped surrogate loss for policy
       4. MSE loss for each value network
       5. Mini-batch gradient descent
       """
   ```

3. **`compute_gae()` (Lines 282-320):**
   ```python
   def compute_gae(self, rewards, values, dones):
       """
       Generalized Advantage Estimation:
       A_t = δ_t + (γλ)δ_{t+1} + ... + (γλ)^{T-t}δ_T
       where δ_t = r_t + γV(s_{t+1}) - V(s_t)
       """
   ```

4. **`scalarize_rewards()` (Lines 322-350):**
   ```python
   def scalarize_rewards(self, rewards_dict):
       """
       Preference-based scalarization:
       R = w_energy × R_energy + w_carbon × R_carbon + w_latency × R_latency

       Where preference_vector = [w_energy, w_carbon, w_latency]
       """
   ```

### File: `train_cmorl.py` (515 lines)

#### Key Class: `CMORLTrainer` (Lines 29-462)

**Training Pipeline:**

1. **Stage 1: Pareto Initialization (Lines 231-314)**
   ```python
   def stage1_pareto_initialization(self, n_policies=6, timesteps_per_policy=150000):
       """
       Train M policies with diverse preference vectors:

       For i in 1..M:
           1. Sample random preference vector w_i
           2. Create agent with preference w_i
           3. Train for 1.5M timesteps using PPO
           4. Evaluate final performance
           5. Add to Pareto front

       Returns: Stage 1 Pareto front
       """
   ```

2. **Stage 2: Pareto Extension (Lines 316-428)**
   ```python
   def stage2_pareto_extension(self, n_select=5, n_steps=60, gamma=0.9):
       """
       Extend Pareto front with constrained optimization:

       1. Select N sparse solutions using crowding distance
       2. For each solution:
          a. For each objective j:
             - Create preference emphasizing j: w_j = 0.7, others = 0.15
             - Initialize from base policy
             - Fine-tune for K steps with new preference
             - Add to Pareto front if non-dominated

       Returns: Extended Pareto front (M + N×3 solutions)
       """
   ```

**Training Configuration (Paper vs Implementation):**

| Parameter | Paper | Test Mode | Research Mode | Full Mode |
|-----------|-------|-----------|---------------|-----------|
| M (Stage 1 policies) | 6 | 3 | 6 | 6 |
| Timesteps per policy | 1.5M | 1K | 50K | 1.5M |
| N (Stage 2 extensions) | 5 | 2 | 5 | 5 |
| K (Extension steps) | 60 | 60 | 60 | 60 |
| γ (Constraint) | 0.9 | 0.9 | 0.9 | 0.9 |

### File: `pareto_utils.py` (380 lines)

#### Key Class: `ParetoFront` (Lines 20-380)

**Core Functionality:**

1. **`add_solution()` (Lines 45-80):**
   ```python
   def add_solution(self, objectives: np.ndarray, metadata: Dict):
       """
       Add solution to Pareto front:
       1. Check if dominated by existing solutions
       2. If non-dominated:
          a. Add to front
          b. Remove solutions dominated by new solution
       3. Update statistics
       """
   ```

2. **`is_dominated()` (Lines 82-110):**
   ```python
   def is_dominated(self, obj1: np.ndarray, obj2: np.ndarray) -> bool:
       """
       Check if obj1 is dominated by obj2:
       obj2 dominates obj1 if:
       - obj2[i] ≤ obj1[i] for all i (minimization)
       - obj2[j] < obj1[j] for at least one j
       """
   ```

3. **`select_sparse_solutions()` (Lines 150-200):**
   ```python
   def select_sparse_solutions(self, n: int):
       """
       Select N most diverse solutions using crowding distance:
       1. Compute crowding distance for each solution
       2. Sort by crowding distance (descending)
       3. Return top N solutions
       """
   ```

4. **`compute_hypervolume()` (Lines 250-300):**
   ```python
   def compute_hypervolume(self, reference_point: np.ndarray = None):
       """
       Compute hypervolume indicator:
       HV = Volume of space dominated by Pareto front
       Reference point: Worst possible objectives
       """
   ```

5. **`compute_expected_utility()` (Lines 302-340):**
   ```python
   def compute_expected_utility(self, n_samples: int = 1000):
       """
       Compute expected utility over random preferences:
       EU = E_w[max_π U(π, w)]
       where w ~ Uniform(simplex)
       """
   ```

---

## CloudSim Integration

### Java Gateway

**File:** `Py4JGatewayEnhanced.java` (Java, CloudSim backend)

**Key Methods Exposed to Python:**

1. **`initializeSimulation()`**
   - Initializes CloudSim core
   - Sets up simulation clock
   - Prepares datacenter infrastructure

2. **`createHeterogeneousDatacenter(String id, int serversPerType, double pue)`**
   - Creates datacenter with 3 server types
   - Each type: specified number of servers
   - Server specifications from Miao2024.pdf Table 3:
     * Huawei RH2285 V2: 16 cores, 24GB RAM, 2.3GHz MIPS
     * Huawei RH2288H V3: 40 cores, 64GB RAM, 3.6GHz MIPS
     * Lenovo SR655 V3: 96 cores, 192GB RAM, 2.4GHz MIPS

3. **`submitVMByType(int vmId, String vmType, String datacenterId)`**
   - Creates VM with specified type
   - VM specs from Miao2024.pdf Table 5
   - Submits to target datacenter
   - Returns: true if successful, false if failed

4. **`runSimulation()`**
   - Executes CloudSim discrete event simulation
   - Processes all VM allocations
   - Calculates energy consumption using non-linear power models
   - Returns: simulation results

5. **`getResults()`**
   - Returns Java Map with overall results:
     * totalITEnergyKWh
     * totalEnergyKWh (PUE-adjusted)
     * averagePUE
     * totalVMs, successfulVMs, failedVMs
     * avgCPUUtilization, avgRAMUtilization

6. **`getDatacenterStats(String datacenterId)`**
   - Returns Java Map with per-datacenter metrics:
     * itEnergyKWh, totalEnergyKWh
     * cpuUtilization, ramUtilization
     * huaweiRH2285Count, huaweiRH2288Count, lenovoSR655Count
     * vmCount

### Power Models

**Non-linear Power Curves (11 points from SpecPower)**

```
Utilization (%) → Power (W)
0%  → P_idle
10% → P_10
20% → P_20
...
100% → P_max

Linear interpolation between points
```

**Server Power Specifications:**

| Server | P_idle | P_max | TDP |
|--------|--------|-------|-----|
| Huawei RH2285 V2 | 58W | 189W | 131W |
| Huawei RH2288H V3 | 95W | 315W | 220W |
| Lenovo SR655 V3 | 150W | 520W | 370W |

---

## Utility Modules

### File: `unified_metrics.py` (244 lines)

**Purpose:** Standardized metrics calculation for comparison.

**Key Class: `UnifiedMetrics`**

**4 Research Metrics:**

1. **M1: Resource Utilization Efficiency**
   ```python
   def compute_m1_resource_utilization(self, total_energy_kwh, total_vms,
                                        avg_cpu_util, avg_ram_util):
       efficiency_score = avg_cpu_util / 100.0  # Normalized 0-1
   ```

2. **M2: Throughput**
   ```python
   def compute_m2_throughput(self, successful_vms, failed_vms, total_time_seconds):
       success_rate = successful_vms / total_vms * 100
       throughput_score = success_rate / 100.0
   ```

3. **M3: Response Time**
   ```python
   def compute_m3_response_time(self, avg_latency_ms, avg_vm_creation_time_s,
                                 total_simulation_time_s):
       response_score = 1.0 / max(avg_latency_ms, 1.0)  # Inverse
   ```

4. **M4: Carbon Intensity Reduction**
   ```python
   def compute_m4_carbon_reduction(self, total_carbon_gco2, baseline_carbon_gco2,
                                    avg_carbon_intensity, avg_renewable_pct):
       reduction_pct = (baseline - actual) / baseline * 100
       carbon_score = reduction_pct / 100.0
   ```

5. **M5: Green Datacenter Utilization**
   ```python
   def compute_m5_green_dc_utilization(self, green_placements, brown_placements):
       green_pct = green_placements / total_placements * 100
       green_score = green_pct / 100.0
   ```

**Output Methods:**

```python
def print_metrics(self):
    """Print metrics in standardized format with visual indicators"""

def compare_with(self, other_metrics):
    """Generate side-by-side comparison with improvement percentages"""

def to_json(self, output_file):
    """Export metrics to JSON for further analysis"""
```

### File: `process_comparison_results.py` (198 lines)

**Purpose:** Parse and process results from ECMR and C-MORL.

**Key Functions:**

1. **`parse_ecmr_output(filepath)`**
   - Reads ECMR text output
   - Extracts metrics using regex patterns
   - Returns UnifiedMetrics object

2. **`parse_cmorl_results(directory)`**
   - Loads C-MORL JSON results
   - Finds best/average solutions for each objective
   - Returns UnifiedMetrics object

3. **`generate_comparison_report(ecmr_metrics, cmorl_metrics, output_file)`**
   - Creates markdown comparison table
   - Calculates improvement percentages
   - Generates visualizations

### File: `run_comparison.py` (287 lines)

**Purpose:** Automated comparison execution.

**Workflow:**

```python
def main():
    1. Start Java gateway
    2. Run ECMR baseline
       - Execute ecmr_heterogeneous_integration.py
       - Capture output
       - Parse metrics
    3. Restart gateway (clean state)
    4. Train C-MORL agent
       - Execute train_cmorl.py
       - Monitor progress
       - Parse results
    5. Generate comparison report
       - Use unified_metrics.py
       - Create markdown report
       - Save to output directory
    6. Stop gateway
```

---

## Configuration

### Environment Variables

```bash
# Java heap size for CloudSim
JAVA_OPTS="-Xmx4G"

# Python paths
PYTHONPATH="."

# CloudSim gateway port (default: 25333)
PY4J_PORT=25333
```

### Configuration Files

**Dataset:** `output/synchronized_dataset_2024.csv`
```csv
timestamp,italy_carbon_intensity,italy_renewable_pct,italy_datacenter_type,...
2024-01-01 00:00:00,156.3,62.4,DG,...
```

**Format:**
- 8760 hourly records (full year 2024)
- For each country (italy, france, sweden, netherlands, spain):
  * `{country}_carbon_intensity`: gCO2/kWh
  * `{country}_renewable_pct`: Percentage (0-100)
  * `{country}_datacenter_type`: 'DG' (Green) or 'DB' (Brown)
  * `{country}_hydro`: MW
  * `{country}_solar`: MW
  * `{country}_wind`: MW

### Algorithm Parameters

**ECMR:**
```python
# Scoring weights (ecmr_heterogeneous_integration.py:103)
w_carbon = 0.5      # Carbon intensity weight
w_renewable = 0.3   # Renewable energy weight
w_latency = 0.2     # Network latency weight

# Datacenter type penalty
brown_penalty = 0.7  # 30% reduction for brown DCs
```

**C-MORL:**
```python
# PPO hyperparameters (cmorl_agent.py:40)
learning_rate = 3e-4
gamma = 0.99        # Discount factor
gae_lambda = 0.95   # GAE parameter
clip_epsilon = 0.2  # PPO clipping

# Training (train_cmorl.py:469)
n_policies = 6           # Stage 1 policies
timesteps_per_policy = 1500000
n_extend = 5             # Stage 2 extensions
n_steps = 60             # Extension steps
```

---

## Summary

### ECMR (ecmr_heterogeneous_integration.py)
- **Lines of Code:** 633
- **Algorithm:** Greedy multi-objective scoring
- **Complexity:** O(n × m) where n = VMs, m = datacenters
- **Strengths:** Fast, deterministic, explainable
- **Limitations:** No learning, fixed weights

### C-MORL (cmorl_*.py files, total ~2200 lines)
- **Lines of Code:** 670 (env) + 395 (agent) + 515 (train) + 380 (pareto) = 1960
- **Algorithm:** Multi-objective PPO with Pareto optimization
- **Complexity:** O(M × T + N × K) where M = policies, T = timesteps, N = extensions, K = steps
- **Strengths:** Learns optimal policy, Pareto front, adaptable
- **Limitations:** Slower training, requires hyperparameter tuning

### CloudSim Integration
- **Bridge:** Py4J (Java ↔ Python)
- **Datacenters:** 5 × 120 servers = 600 heterogeneous servers total
- **Power Models:** Non-linear 11-point curves from SpecPower
- **VM Types:** 4 types with realistic resource requirements

### Key Files Summary

| File | Purpose | Lines | Key Classes |
|------|---------|-------|-------------|
| ecmr_heterogeneous_integration.py | ECMR baseline | 633 | ECMRHeterogeneousScheduler, ECMRHeterogeneousIntegration |
| cmorl_environment.py | RL environment | 670 | CMORLEnvironment |
| cmorl_agent.py | Multi-objective PPO | 395 | CMORLAgent |
| train_cmorl.py | C-MORL training | 515 | CMORLTrainer |
| pareto_utils.py | Pareto operations | 380 | ParetoFront |
| unified_metrics.py | Metrics calculation | 244 | UnifiedMetrics |
| run_comparison.py | Automated comparison | 287 | - |

---

For step-by-step running instructions, see `RUNNING_TESTING_GUIDE.md`.
For test scenarios and expected results, see `TEST_SCENARIOS.md`.
