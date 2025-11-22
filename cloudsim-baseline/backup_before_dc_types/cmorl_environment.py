#!/usr/bin/env python3
"""
C-MORL Environment for Carbon-Aware Workload Scheduling
Gymnasium-compatible environment wrapping CloudSim infrastructure
Implements 127-dimensional state space and multi-objective rewards

Architecture (same as ECMR baseline):
- Python: Episode management, state calculation, reward calculation, RL agent
- CloudSim: Datacenter simulation, VM placement, energy calculation
- Py4J: Bridge between Python and Java
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from py4j.java_gateway import JavaGateway
import pandas as pd
from typing import Dict, List, Tuple, Optional
from collections import deque
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# European Datacenter Locations (EXACT match with ECMR baseline)
DATACENTERS = {
    'DC_MADRID': {'country': 'spain', 'lat': 40.4168, 'lon': -3.7038, 'pue': 1.25},
    'DC_AMSTERDAM': {'country': 'netherlands', 'lat': 52.3676, 'lon': 4.9041, 'pue': 1.2},
    'DC_PARIS': {'country': 'france', 'lat': 48.8566, 'lon': 2.3522, 'pue': 1.15},
    'DC_MILAN': {'country': 'italy', 'lat': 45.4642, 'lon': 9.1900, 'pue': 1.2},
    'DC_STOCKHOLM': {'country': 'sweden', 'lat': 59.3293, 'lon': 18.0686, 'pue': 1.1}
}

# VM Types (EXACT match with ECMR baseline)
VM_TYPES = ['small', 'medium', 'large', 'xlarge']
VM_TYPE_WEIGHTS = [0.4, 0.3, 0.2, 0.1]  # 40% small, 30% medium, 20% large, 10% xlarge

VM_SPECS = {
    'small': {'cores': 1, 'ram_mb': 2048, 'storage_mb': 256000, 'mips': 500},
    'medium': {'cores': 2, 'ram_mb': 4096, 'storage_mb': 500000, 'mips': 1000},
    'large': {'cores': 4, 'ram_mb': 8192, 'storage_mb': 750000, 'mips': 1500},
    'xlarge': {'cores': 8, 'ram_mb': 16384, 'storage_mb': 1000000, 'mips': 2000}
}


class CMORLEnvironment(gym.Env):
    """
    Multi-Objective RL Environment for Carbon-Aware Scheduling

    State Space: 127 dimensions
        [0:4]     VM requirements (cores, ram, storage, latency_sensitivity)
        [4:44]    Per-datacenter metrics (5 DCs × 8 features)
        [44:74]   Renewable forecasts (5 DCs × 3 sources × 2 horizons)
        [74:127]  Historical performance (53 dimensions)

    Action Space: Discrete(5) - Select datacenter for current VM

    Rewards: Multi-objective (dict with 3 keys)
        - R_energy: Negative normalized energy consumption
        - R_carbon: Negative normalized carbon emissions
        - R_latency: Negative normalized response time
    """

    metadata = {'render.modes': ['human']}

    def __init__(self,
                 carbon_data_path: str = 'output/synchronized_dataset_2024.csv',
                 simulation_hours: int = 24,
                 vms_per_hour: int = 10,
                 user_location: Tuple[float, float] = (48.8566, 2.3522),  # Default: Paris
                 random_seed: int = 42):
        """
        Initialize C-MORL environment

        Args:
            carbon_data_path: Path to carbon intensity dataset
            simulation_hours: Duration of simulation in hours
            vms_per_hour: Number of VM requests per hour
            user_location: (latitude, longitude) of user
            random_seed: Random seed for reproducibility
        """
        super().__init__()

        self.simulation_hours = simulation_hours
        self.vms_per_hour = vms_per_hour
        self.user_location = user_location
        self.random_seed = random_seed

        # Action space: 5 datacenters
        self.action_space = spaces.Discrete(5)

        # State space: 127-dimensional continuous
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(127,),
            dtype=np.float32
        )

        # Datacenter mapping
        self.datacenter_ids = list(DATACENTERS.keys())
        self.num_datacenters = len(self.datacenter_ids)

        # Load carbon intensity data (REAL data from ENTSO-E/ElectricityMaps)
        logger.info(f"Loading carbon data from {carbon_data_path}")
        self.carbon_data = pd.read_csv(carbon_data_path)
        self.carbon_data['timestamp'] = pd.to_datetime(self.carbon_data['timestamp'])
        logger.info(f"Loaded {len(self.carbon_data)} hourly records")

        # Initialize CloudSim gateway (same as ECMR)
        logger.info("Connecting to CloudSim gateway...")
        self.gateway = JavaGateway()
        self.app = self.gateway.entry_point
        logger.info("Connected to CloudSim")

        # Episode state (managed in Python, same as ECMR)
        self.current_hour = 0
        self.current_vm_in_hour = 0
        self.vm_id_counter = 0
        self.episode_step = 0

        # VM queue for current episode
        self.vm_queue = []
        self.current_vm = None

        # Datacenter state tracking (Python side, updated from real data)
        self.datacenter_states = {dc_id: self._init_datacenter_state()
                                  for dc_id in self.datacenter_ids}

        # Historical performance tracking (for state representation)
        self.energy_history = deque(maxlen=10)
        self.carbon_history = deque(maxlen=10)
        self.latency_history = deque(maxlen=10)

        # Baseline metrics for normalization (EMA)
        self.baseline_energy = 100.0
        self.baseline_carbon = 1000.0
        self.baseline_latency = 50.0

        # Episode metrics
        self.episode_energy = 0.0
        self.episode_carbon = 0.0
        self.episode_latency = 0.0
        self.episode_placements = []
        self.episode_failures = 0

        logger.info("C-MORL Environment initialized")

    def _init_datacenter_state(self) -> Dict:
        """Initialize datacenter state tracking"""
        return {
            'carbon_intensity': 0.0,
            'renewable_pct': 0.0,
            'solar_mw': 0.0,
            'wind_mw': 0.0,
            'hydro_mw': 0.0,
            'electricity_price': 50.0,
            'network_latency': 0.0,
            'vms_placed': 0,
            'queue_length': 0
        }

    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment for new episode (same as ECMR episode start)

        Returns:
            state: 127-dimensional state vector
            info: Additional information
        """
        super().reset(seed=seed)

        if seed is not None:
            self.random_seed = seed
            np.random.seed(seed)

        logger.info(f"=== RESET: Starting new episode (seed={self.random_seed}) ===")

        # Reset CloudSim simulation (same as ECMR)
        self.app.initializeSimulation()

        # Create 5 heterogeneous datacenters (same as ECMR)
        for dc_id, dc_info in DATACENTERS.items():
            self.app.createHeterogeneousDatacenter(dc_id, 40, dc_info['pue'])

        # Reset episode state
        self.current_hour = 0
        self.current_vm_in_hour = 0
        self.vm_id_counter = 0
        self.episode_step = 0

        # Reset metrics
        self.episode_energy = 0.0
        self.episode_carbon = 0.0
        self.episode_latency = 0.0
        self.episode_placements = []
        self.episode_failures = 0

        # Reset datacenter states
        for dc_id in self.datacenter_ids:
            self.datacenter_states[dc_id] = self._init_datacenter_state()

        # Generate VM queue for entire episode (same as ECMR generates VMs)
        self._generate_vm_queue()

        # Get first VM
        self.current_vm = self.vm_queue[0] if self.vm_queue else None

        # Update datacenter states with hour 0 data
        self._update_datacenter_states()

        # Get initial state
        state = self._get_state()

        info = {
            'hour': self.current_hour,
            'vm_id': self.current_vm['id'] if self.current_vm else -1,
            'total_vms': len(self.vm_queue)
        }

        logger.info(f"Episode reset complete: {len(self.vm_queue)} VMs queued")

        return state, info

    def step(self, action: int) -> Tuple[np.ndarray, Dict[str, float], bool, bool, Dict]:
        """
        Execute one step: Submit VM to selected datacenter (same as ECMR submitVM)

        Args:
            action: Datacenter selection (0-4)

        Returns:
            state: Next state (127-dim)
            reward: Multi-objective reward dict
            terminated: Whether episode finished
            truncated: Always False
            info: Additional information
        """
        if self.current_vm is None:
            raise ValueError("No VM to place. Call reset() first.")

        # Map action to datacenter ID
        selected_dc = self.datacenter_ids[action]

        # Submit VM to CloudSim (same as ECMR: self.app.submitVMByType)
        vm_type = self.current_vm['type']
        vm_id = self.current_vm['id']

        success = self.app.submitVMByType(vm_id, vm_type, selected_dc)

        if success:
            # Track placement
            self.episode_placements.append({
                'vm_id': vm_id,
                'datacenter': selected_dc,
                'hour': self.current_hour,
                'type': vm_type,
                'carbon_intensity': self.datacenter_states[selected_dc]['carbon_intensity'],
                'renewable_pct': self.datacenter_states[selected_dc]['renewable_pct']
            })

            # Update datacenter state
            self.datacenter_states[selected_dc]['vms_placed'] += 1
        else:
            self.episode_failures += 1
            logger.warning(f"Failed to place VM {vm_id} at {selected_dc}")

        # Calculate immediate reward
        reward = self._calculate_reward(success, selected_dc)

        # Move to next VM
        self.episode_step += 1
        self.current_vm_in_hour += 1

        # Check if we need to advance to next hour
        if self.current_vm_in_hour >= self.vms_per_hour:
            self.current_hour += 1
            self.current_vm_in_hour = 0

            # Update datacenter states with new hour data (same as ECMR)
            if self.current_hour < self.simulation_hours:
                self._update_datacenter_states()

        # Check if episode is done
        done = self.episode_step >= len(self.vm_queue)

        if done:
            # Run CloudSim simulation (same as ECMR: self.app.runSimulation())
            logger.info("Episode complete. Running CloudSim simulation...")
            self.app.runSimulation()

            # Get results from CloudSim
            results = self.app.getResults()
            self.episode_energy = results.get('totalEnergyKWh', 0.0)

            # Calculate carbon emissions (CloudSim energy × real carbon intensity)
            self.episode_carbon = self._calculate_episode_carbon()

            # Calculate average latency
            self.episode_latency = self._calculate_average_latency()

            # Update baselines (EMA)
            alpha = 0.1
            if self.episode_energy > 0:
                self.baseline_energy = alpha * self.episode_energy + (1 - alpha) * self.baseline_energy
            if self.episode_carbon > 0:
                self.baseline_carbon = alpha * self.episode_carbon + (1 - alpha) * self.baseline_carbon
            if self.episode_latency > 0:
                self.baseline_latency = alpha * self.episode_latency + (1 - alpha) * self.baseline_latency

            # Add to history
            self.energy_history.append(self.episode_energy)
            self.carbon_history.append(self.episode_carbon)
            self.latency_history.append(self.episode_latency)

            logger.info(f"Episode results: Energy={self.episode_energy:.3f} kWh, "
                       f"Carbon={self.episode_carbon:.3f} gCO2, "
                       f"Latency={self.episode_latency:.3f} ms")

        # Get next VM (if any)
        if self.episode_step < len(self.vm_queue):
            self.current_vm = self.vm_queue[self.episode_step]
        else:
            self.current_vm = None

        # Get next state
        next_state = self._get_state() if not done else np.zeros(127, dtype=np.float32)

        # Info dict
        info = {
            'hour': self.current_hour,
            'vm_id': vm_id,
            'selected_dc': selected_dc,
            'success': success,
            'episode_energy': self.episode_energy if done else 0.0,
            'episode_carbon': self.episode_carbon if done else 0.0,
            'episode_latency': self.episode_latency if done else 0.0,
            'episode_failures': self.episode_failures,
            'total_placements': len(self.episode_placements)
        }

        return next_state, reward, done, False, info

    def _calculate_reward(self, success: bool, selected_dc: str) -> Dict[str, float]:
        """
        Calculate multi-objective rewards (immediate per-step rewards)

        Returns:
            Dict with three reward signals: R_energy, R_carbon, R_latency
        """
        if not success:
            # Penalty for failed placement
            return {'R_energy': -1.0, 'R_carbon': -1.0, 'R_latency': -1.0}

        dc_state = self.datacenter_states[selected_dc]

        # Energy reward: Prefer high renewable %
        renewable_bonus = dc_state['renewable_pct'] / 100.0
        r_energy = renewable_bonus - 0.5  # Range: [-0.5, 0.5]

        # Carbon reward: Prefer low carbon intensity
        max_carbon = 500.0
        normalized_carbon = min(dc_state['carbon_intensity'] / max_carbon, 1.0)
        r_carbon = -normalized_carbon  # Range: [-1.0, 0.0]

        # Latency reward: Prefer low network latency
        max_latency = 50.0
        normalized_latency = min(dc_state['network_latency'] / max_latency, 1.0)
        r_latency = -normalized_latency  # Range: [-1.0, 0.0]

        return {
            'R_energy': float(r_energy),
            'R_carbon': float(r_carbon),
            'R_latency': float(r_latency)
        }

    def _get_state(self) -> np.ndarray:
        """
        Build 127-dimensional state vector (from paper specification)

        State composition:
            [0:4]     VM requirements
            [4:44]    Per-datacenter metrics (5 × 8)
            [44:74]   Renewable forecasts (5 × 3 × 2)
            [74:127]  Historical performance (53)
        """
        state = np.zeros(127, dtype=np.float32)
        idx = 0

        # 1. Current VM requirements (4 dimensions)
        if self.current_vm:
            vm_spec = VM_SPECS[self.current_vm['type']]
            state[idx:idx+4] = [
                vm_spec['cores'] / 8.0,
                vm_spec['ram_mb'] / 16384.0,
                vm_spec['storage_mb'] / 1000000.0,
                self.current_vm.get('latency_sensitive', 0.5)
            ]
        idx += 4

        # 2. Per-datacenter metrics (40 dimensions: 5 DCs × 8 features)
        for dc_id in self.datacenter_ids:
            dc_state = self.datacenter_states[dc_id]

            # Get utilization from CloudSim (if episode started)
            cpu_util = 0.0
            ram_util = 0.0
            storage_util = 0.0

            if self.episode_step > 0:
                try:
                    dc_stats = self.app.getDatacenterStats(dc_id)
                    cpu_util = dc_stats.get('cpuUtilization', 0.0) / 100.0
                    ram_util = dc_stats.get('ramUtilization', 0.0) / 100.0
                    storage_util = 0.5  # Approximation
                except:
                    pass

            state[idx:idx+8] = [
                cpu_util,
                ram_util,
                storage_util,
                dc_state['queue_length'] / 100.0,
                dc_state['renewable_pct'] / 100.0,
                dc_state['carbon_intensity'] / 500.0,
                dc_state['electricity_price'] / 100.0,
                dc_state['network_latency'] / 50.0
            ]
            idx += 8

        # 3. Renewable energy forecasts (30 dimensions: 5 DCs × 3 sources × 2 horizons)
        for dc_id in self.datacenter_ids:
            dc_country = DATACENTERS[dc_id]['country']

            # Get current + next hour data (simple forecast)
            for horizon in [0, 1]:
                hour_idx = min(self.current_hour + horizon, len(self.carbon_data) - 1)
                row = self.carbon_data.iloc[hour_idx]

                # Get renewable percentages
                solar_pct = row.get(f'{dc_country}_solar_pct', 0.0) / 100.0
                wind_pct = row.get(f'{dc_country}_wind_pct', 0.0) / 100.0
                hydro_pct = row.get(f'{dc_country}_hydro_pct', 0.0) / 100.0

                state[idx:idx+3] = [solar_pct, wind_pct, hydro_pct]
                idx += 3

        # 4. Historical performance (53 dimensions)
        energy_ma = np.mean(self.energy_history) if self.energy_history else 0.0
        carbon_ma = np.mean(self.carbon_history) if self.carbon_history else 0.0
        latency_ma = np.mean(self.latency_history) if self.latency_history else 0.0

        state[idx:idx+53] = [
            # Recent performance (3)
            energy_ma / self.baseline_energy,
            carbon_ma / self.baseline_carbon,
            latency_ma / self.baseline_latency,

            # Episode progress (2)
            self.episode_step / max(1, len(self.vm_queue)),
            self.current_hour / max(1, self.simulation_hours),

            # Episode statistics (5)
            len(self.episode_placements) / max(1, self.episode_step or 1),
            self.episode_failures / max(1, self.episode_step or 1),
            0.0,  # Placeholder: episode energy (unknown until end)
            0.0,  # Placeholder: episode carbon
            0.0,  # Placeholder: episode latency

            # Per-datacenter placement counts (5)
            *[sum(1 for p in self.episode_placements if p['datacenter'] == dc_id) / max(1, len(self.episode_placements) or 1)
              for dc_id in self.datacenter_ids],

            # Time-of-day features (4)
            np.sin(2 * np.pi * self.current_hour / 24),
            np.cos(2 * np.pi * self.current_hour / 24),
            np.sin(2 * np.pi * self.current_vm_in_hour / max(1, self.vms_per_hour)),
            np.cos(2 * np.pi * self.current_vm_in_hour / max(1, self.vms_per_hour)),

            # Current renewable percentages (5)
            *[self.datacenter_states[dc_id]['renewable_pct'] / 100.0
              for dc_id in self.datacenter_ids],

            # Current carbon intensities (5)
            *[self.datacenter_states[dc_id]['carbon_intensity'] / 500.0
              for dc_id in self.datacenter_ids],

            # Network latencies to user (5)
            *[self.datacenter_states[dc_id]['network_latency'] / 50.0
              for dc_id in self.datacenter_ids],

            # VM type distribution so far (4)
            *[sum(1 for p in self.episode_placements if p['type'] == vm_type) / max(1, len(self.episode_placements) or 1)
              for vm_type in VM_TYPES],

            # Success rate per datacenter (5)
            *[sum(1 for p in self.episode_placements if p['datacenter'] == dc_id) / max(1, self.datacenter_states[dc_id]['vms_placed'] or 1)
              for dc_id in self.datacenter_ids],

            # Additional features to reach 53 dimensions (10 more)
            # Energy variance indicators (5 - one per datacenter)
            *[float(self.datacenter_states[dc_id]['vms_placed']) / max(1, self.episode_step or 1)
              for dc_id in self.datacenter_ids],

            # Historical performance variance (5)
            np.std(self.energy_history) if len(self.energy_history) > 1 else 0.0,
            np.std(self.carbon_history) if len(self.carbon_history) > 1 else 0.0,
            np.std(self.latency_history) if len(self.latency_history) > 1 else 0.0,
            float(len(self.energy_history)) / 10.0,  # History fill ratio
            float(self.episode_failures) / max(1, len(self.vm_queue))  # Overall failure rate
        ]

        return state

    def _generate_vm_queue(self):
        """Generate VM requests for the episode (same distribution as ECMR)"""
        self.vm_queue = []

        for hour in range(self.simulation_hours):
            for vm_in_hour in range(self.vms_per_hour):
                # Random VM type (same distribution as ECMR)
                vm_type = np.random.choice(VM_TYPES, p=VM_TYPE_WEIGHTS)

                # Latency sensitivity (30% are latency-sensitive)
                latency_sensitive = np.random.random() < 0.3

                self.vm_queue.append({
                    'id': self.vm_id_counter,
                    'type': vm_type,
                    'hour': hour,
                    'latency_sensitive': float(latency_sensitive)
                })

                self.vm_id_counter += 1

        logger.info(f"Generated {len(self.vm_queue)} VMs for {self.simulation_hours}-hour episode")

    def _update_datacenter_states(self):
        """Update datacenter states with current hour carbon/renewable data (from REAL data)"""
        if self.current_hour >= len(self.carbon_data):
            logger.warning(f"Hour {self.current_hour} exceeds carbon data length")
            return

        row = self.carbon_data.iloc[self.current_hour]

        for dc_id in self.datacenter_ids:
            dc_country = DATACENTERS[dc_id]['country']

            # Update with REAL carbon intensity data
            carbon_col = f'{dc_country}_carbon_intensity'
            self.datacenter_states[dc_id]['carbon_intensity'] = row.get(carbon_col, 0)

            # Update with REAL renewable percentage
            renewable_col = f'{dc_country}_renewable_pct'
            self.datacenter_states[dc_id]['renewable_pct'] = row.get(renewable_col, 0)

            # Update renewable breakdown
            self.datacenter_states[dc_id]['solar_mw'] = row.get(f'{dc_country}_solar', 0)
            self.datacenter_states[dc_id]['wind_mw'] = row.get(f'{dc_country}_wind', 0)
            self.datacenter_states[dc_id]['hydro_mw'] = row.get(f'{dc_country}_hydro', 0)

            # Calculate network latency to user
            dc_lat = DATACENTERS[dc_id]['lat']
            dc_lon = DATACENTERS[dc_id]['lon']
            self.datacenter_states[dc_id]['network_latency'] = self._calculate_latency(
                dc_lat, dc_lon, self.user_location[0], self.user_location[1]
            )

            # Electricity price (simplified)
            self.datacenter_states[dc_id]['electricity_price'] = 50.0 + np.random.normal(0, 10)

    @staticmethod
    def _calculate_latency(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate network latency based on geographic distance (Haversine formula)"""
        import math

        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c

        # Latency model: 5ms base + 0.01ms per km
        latency = 5.0 + distance * 0.01
        return latency

    def _calculate_episode_carbon(self) -> float:
        """Calculate total carbon emissions (CloudSim energy × real carbon intensity)"""
        if not self.episode_placements:
            return 0.0

        total_carbon = 0.0
        energy_per_vm = self.episode_energy / len(self.episode_placements)

        for placement in self.episode_placements:
            carbon_intensity = placement['carbon_intensity']
            total_carbon += energy_per_vm * carbon_intensity

        return total_carbon

    def _calculate_average_latency(self) -> float:
        """Calculate average network latency for placed VMs"""
        if not self.episode_placements:
            return 0.0

        total_latency = 0.0
        for placement in self.episode_placements:
            dc_id = placement['datacenter']
            dc_lat = DATACENTERS[dc_id]['lat']
            dc_lon = DATACENTERS[dc_id]['lon']

            latency = self._calculate_latency(
                dc_lat, dc_lon,
                self.user_location[0], self.user_location[1]
            )
            total_latency += latency

        return total_latency / len(self.episode_placements)

    def render(self, mode='human'):
        """Render environment state"""
        if mode == 'human':
            print(f"\n=== C-MORL Environment ===")
            print(f"Hour: {self.current_hour}/{self.simulation_hours}")
            print(f"Step: {self.episode_step}/{len(self.vm_queue)}")
            print(f"Current VM: {self.current_vm}")
            print(f"Placements: {len(self.episode_placements)}, Failures: {self.episode_failures}")
            print(f"\nDatacenter States:")
            for dc_id, state in self.datacenter_states.items():
                print(f"  {dc_id}: C={state['carbon_intensity']:.0f} gCO2/kWh, "
                      f"R={state['renewable_pct']:.0f}%, VMs={state['vms_placed']}")

    def close(self):
        """Clean up resources"""
        # NOTE: Do NOT shut down the gateway here!
        # The gateway is shared across multiple environments/policies
        # Only shut it down when the entire training process is complete
        logger.info("Environment closed")


if __name__ == "__main__":
    # Test the environment with random actions
    print("="*80)
    print("C-MORL ENVIRONMENT TEST")
    print("="*80)

    env = CMORLEnvironment(
        simulation_hours=2,
        vms_per_hour=5,
        random_seed=42
    )

    print(f"\n✓ Environment created")
    print(f"  State space: {env.observation_space.shape}")
    print(f"  Action space: {env.action_space.n}")

    # Reset
    state, info = env.reset()
    print(f"\n✓ Environment reset")
    print(f"  Total VMs: {info['total_vms']}")
    print(f"  State shape: {state.shape}")
    print(f"  State range: [{state.min():.3f}, {state.max():.3f}]")

    # Run episode with random actions
    print(f"\n✓ Running episode with random actions...")
    done = False
    step = 0

    while not done and step < 20:
        action = env.action_space.sample()
        next_state, reward, done, truncated, info = env.step(action)

        if step % 5 == 0:
            print(f"\n  Step {step+1}:")
            print(f"    Action: {env.datacenter_ids[action]}")
            print(f"    Rewards: E={reward['R_energy']:.3f}, C={reward['R_carbon']:.3f}, L={reward['R_latency']:.3f}")
            print(f"    Success: {info['success']}")

        step += 1

    if done:
        print(f"\n✓ Episode finished!")
        print(f"  Total energy: {info['episode_energy']:.3f} kWh")
        print(f"  Total carbon: {info['episode_carbon']:.3f} gCO2")
        print(f"  Avg latency: {info['episode_latency']:.3f} ms")
        print(f"  Failures: {info['episode_failures']}")

    env.close()
    print("\n" + "="*80)
    print("✓ TEST COMPLETED")
    print("="*80)
