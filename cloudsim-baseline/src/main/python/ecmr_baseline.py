#!/usr/bin/env python3
"""
ECMR Baseline Implementation (Miao et al. 2024)
Energy and Carbon-aware VM Dispatching with Multi-RES

Algorithm 1 Implementation:
Step 1: Classify datacenters as DG (green) or DB (brown)
Step 2: Sort DG by distance, allocate to nearest
Step 3: Use MESF (Most Effective Server First) for server selection
Step 4: Weighted sum optimization: w1(energy) + w2(carbon) + w3(latency)
Step 5: Collect metrics M1-M4

"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import argparse
from datetime import datetime
import json


@dataclass
class Datacenter:
    """Datacenter configuration"""
    id: str
    name: str
    country: str
    latitude: float
    longitude: float
    num_servers: int
    cpu_per_server: int
    ram_per_server_mb: int
    power_idle_w: float  # Idle power consumption
    power_max_w: float   # Max power consumption
    pue: float           # Power Usage Effectiveness
    
    # Dynamic state (updated each hour)
    renewable_generation_mw: float = 0.0
    carbon_intensity_gco2_kwh: float = 0.0
    renewable_pct: float = 0.0
    datacenter_type: str = 'DB'  # DG or DB
    
    # Current resource utilization
    used_cpus: int = 0
    used_ram_mb: int = 0
    active_vms: List[int] = None
    
    def __post_init__(self):
        if self.active_vms is None:
            self.active_vms = []
    
    @property
    def total_cpus(self):
        return self.num_servers * self.cpu_per_server
    
    @property
    def total_ram_mb(self):
        return self.num_servers * self.ram_per_server_mb
    
    @property
    def available_cpus(self):
        return self.total_cpus - self.used_cpus
    
    @property
    def available_ram_mb(self):
        return self.total_ram_mb - self.used_ram_mb
    
    @property
    def cpu_utilization(self):
        return self.used_cpus / self.total_cpus if self.total_cpus > 0 else 0
    
    @property
    def ram_utilization(self):
        return self.used_ram_mb / self.total_ram_mb if self.total_ram_mb > 0 else 0
    
    def can_host_vm(self, vm):
        """Check if datacenter has resources for VM"""
        return (self.available_cpus >= vm['num_cpus'] and 
                self.available_ram_mb >= vm['ram_mb'])
    
    def allocate_vm(self, vm):
        """Allocate VM to this datacenter"""
        self.used_cpus += vm['num_cpus']
        self.used_ram_mb += vm['ram_mb']
        self.active_vms.append(vm['vm_id'])
    
    def release_vm(self, vm):
        """Release VM resources"""
        self.used_cpus -= vm['num_cpus']
        self.used_ram_mb -= vm['ram_mb']
        if vm['vm_id'] in self.active_vms:
            self.active_vms.remove(vm['vm_id'])
    
    def calculate_power_consumption(self):
        """Calculate current power consumption (Watts)"""
        # Linear power model based on CPU utilization
        util = self.cpu_utilization
        return self.power_idle_w + (self.power_max_w - self.power_idle_w) * util
    
    def calculate_total_energy_kwh(self, hours=1):
        """Calculate total energy consumption including PUE"""
        power_w = self.calculate_power_consumption()
        energy_kwh = (power_w * hours) / 1000  # Convert W to kWh
        return energy_kwh * self.pue  # Apply PUE


@dataclass
class VM:
    """Virtual Machine request"""
    vm_id: int
    timestamp: datetime
    num_cpus: int
    ram_mb: int
    execution_time_sec: int
    mips: int
    
    # Assignment info
    assigned_datacenter: str = None
    assignment_time: datetime = None
    completion_time: datetime = None
    response_time_ms: float = 0.0
    failed: bool = False


class ECMRScheduler:
    """ECMR VM Scheduling Algorithm (Miao et al. 2024)"""
    
    def __init__(self, datacenters: List[Datacenter],
                 weights=(0.33, 0.33, 0.34),  # w1=energy, w2=carbon, w3=latency
                 user_location=(48.8566, 2.3522),  # Default: Paris
                 latency_threshold_ms=100.0):  # Max acceptable latency
        """
        Initialize ECMR scheduler

        Parameters:
        - datacenters: List of Datacenter objects
        - weights: (w1, w2, w3) for energy, carbon, latency optimization
        - user_location: (latitude, longitude) for distance calculation
        - latency_threshold_ms: Maximum acceptable latency in milliseconds
        """
        self.datacenters = {dc.id: dc for dc in datacenters}
        self.w1, self.w2, self.w3 = weights
        self.user_location = user_location
        self.latency_threshold_ms = latency_threshold_ms

        # Metrics tracking
        self.metrics = {
            'total_vms': 0,
            'placed_vms': 0,
            'failed_vms': 0,
            'total_energy_kwh': 0,
            'renewable_energy_kwh': 0,
            'carbon_emissions_kg': 0,
            'total_response_time_ms': 0,
            'placement_decisions': [],
            'latency_rejections': 0,  # Track latency-based rejections
            'res_rejections': 0  # Track RES availability rejections
        }
    
    def calculate_distance(self, dc: Datacenter) -> float:
        """Calculate haversine distance from user to datacenter (km)"""
        lat1, lon1 = self.user_location
        lat2, lon2 = dc.latitude, dc.longitude
        
        # Haversine formula
        R = 6371  # Earth radius in km
        
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat / 2) ** 2 + 
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * 
             np.sin(dlon / 2) ** 2)
        
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
    
    def classify_datacenters(self):
        """
        Algorithm 1, Step 1: Classify datacenters as DG or DB
        DG: renewable_pct > threshold (datacenter_type set by data pipeline)
        DB: renewable_pct <= threshold
        """
        dg_datacenters = []
        db_datacenters = []
        
        for dc in self.datacenters.values():
            if dc.datacenter_type == 'DG':
                dg_datacenters.append(dc)
            else:
                db_datacenters.append(dc)
        
        return dg_datacenters, db_datacenters
    
    def sort_dg_by_distance(self, dg_datacenters: List[Datacenter]) -> List[Datacenter]:
        """
        Algorithm 1, Step 2: Sort DG datacenters by distance from user
        """
        sorted_dg = sorted(dg_datacenters, 
                          key=lambda dc: self.calculate_distance(dc))
        return sorted_dg
    
    def calculate_server_efficiency(self, dc: Datacenter, vm: Dict) -> float:
        """
        Calculate server efficiency for MESF (Most Effective Server First)
        Lower value = more efficient
        
        This is a simplified version. Full implementation would calculate
        per-server efficiency based on current load.
        """
        # Calculate incremental energy if VM is added
        current_util = dc.cpu_utilization
        new_util = (dc.used_cpus + vm['num_cpus']) / dc.total_cpus
        
        # Energy increase per CPU allocated
        delta_util = new_util - current_util
        delta_power_w = (dc.power_max_w - dc.power_idle_w) * delta_util
        
        # Normalize by VM size (smaller = more efficient use)
        efficiency = delta_power_w / vm['num_cpus']

        return efficiency

    def estimate_vm_energy_kwh(self, vm: Dict, execution_hours=1.0) -> float:
        """
        Estimate energy consumption for a VM (kWh)
        Based on CPU utilization and execution time
        """
        # Assume VM uses power proportional to CPU count
        # Rough estimate: 50W per CPU core at full utilization
        estimated_power_w = vm['num_cpus'] * 50.0
        energy_kwh = (estimated_power_w * execution_hours) / 1000.0
        return energy_kwh

    def check_res_availability(self, dc: Datacenter, vm: Dict) -> bool:
        """
        Check if datacenter has sufficient renewable energy for VM
        Algorithm 1, Line 19-23: Verify RES_margin > E_r

        Returns True if renewable energy is sufficient or if it's a brown datacenter
        """
        if dc.datacenter_type == 'DB':
            # Brown datacenters don't need RES check
            return True

        # Estimate energy needed for this VM (assume 1 hour execution)
        energy_needed_kwh = self.estimate_vm_energy_kwh(vm, execution_hours=1.0)

        # Calculate available renewable energy
        # RES generation in MW, convert to kWh for 1 hour
        available_res_kwh = dc.renewable_generation_mw * 1000.0  # MW to kW, 1 hour

        # Check if there's enough renewable energy margin
        # (This is simplified - in reality would track cumulative usage)
        return available_res_kwh > energy_needed_kwh

    def calculate_weighted_score(self, dc: Datacenter, vm: Dict) -> float:
        """
        Calculate weighted multi-objective score for datacenter selection
        Lower score is better

        Score = w1 * normalized_energy + w2 * normalized_carbon + w3 * normalized_latency

        This implements the weighted sum optimization from the paper
        """
        # Energy component (incremental energy for this VM)
        current_util = dc.cpu_utilization
        new_util = (dc.used_cpus + vm['num_cpus']) / dc.total_cpus
        delta_util = new_util - current_util
        incremental_energy = (dc.power_max_w - dc.power_idle_w) * delta_util * dc.pue

        # Carbon component (carbon intensity of the datacenter)
        carbon_intensity = dc.carbon_intensity_gco2_kwh

        # Latency component
        distance_km = self.calculate_distance(dc)
        latency_ms = distance_km * 0.1

        # Normalize components to [0, 1] range for fair weighting
        # (Using rough normalization based on typical ranges)
        norm_energy = incremental_energy / 1000.0  # Normalize by 1kW
        norm_carbon = carbon_intensity / 500.0  # Normalize by 500 gCO2/kWh
        norm_latency = latency_ms / 100.0  # Normalize by 100ms

        # Calculate weighted score
        score = (self.w1 * norm_energy +
                self.w2 * norm_carbon +
                self.w3 * norm_latency)

        return score

    def schedule_vm(self, vm: Dict, current_time: datetime) -> Tuple[str, bool]:
        """
        Enhanced ECMR scheduling algorithm with weighted multi-objective optimization

        Implements Algorithm 1 from Miao et al. 2024 with:
        - Weighted scoring (w1*energy + w2*carbon + w3*latency)
        - RES availability checking
        - Latency threshold enforcement
        - Server-level efficiency consideration

        Returns:
        - (datacenter_id, success)
        """

        # Step 1: Classify datacenters as DG (green) or DB (brown)
        dg_datacenters, db_datacenters = self.classify_datacenters()

        # Step 2 & 3: Evaluate DG datacenters with constraints and scoring
        candidate_dcs = []

        for dc in dg_datacenters:
            # Check basic capacity
            if not dc.can_host_vm(vm):
                continue

            # Calculate latency (Algorithm 1, Line 19)
            distance_km = self.calculate_distance(dc)
            latency_ms = distance_km * 0.1  # 0.1ms per km

            # Check latency threshold (L_rj < T_thre)
            if latency_ms > self.latency_threshold_ms:
                self.metrics['latency_rejections'] += 1
                continue

            # Check RES availability (Algorithm 1, Lines 19-23: RES_margin > E_r)
            if not self.check_res_availability(dc, vm):
                self.metrics['res_rejections'] += 1
                continue

            # Calculate weighted score for this datacenter
            score = self.calculate_weighted_score(dc, vm)

            candidate_dcs.append({
                'datacenter': dc,
                'score': score,
                'distance_km': distance_km,
                'latency_ms': latency_ms,
                'type': 'DG'
            })

        # Step 4: If no suitable DG found, evaluate DB datacenters
        if not candidate_dcs:
            for dc in db_datacenters:
                if not dc.can_host_vm(vm):
                    continue

                distance_km = self.calculate_distance(dc)
                latency_ms = distance_km * 0.1

                # Check latency threshold for brown DCs too
                if latency_ms > self.latency_threshold_ms:
                    self.metrics['latency_rejections'] += 1
                    continue

                score = self.calculate_weighted_score(dc, vm)

                candidate_dcs.append({
                    'datacenter': dc,
                    'score': score,
                    'distance_km': distance_km,
                    'latency_ms': latency_ms,
                    'type': 'DB'
                })

        # Step 5: Select best datacenter based on weighted score (lower is better)
        if candidate_dcs:
            # Sort by score and pick the best
            candidate_dcs.sort(key=lambda x: x['score'])
            best = candidate_dcs[0]

            dc = best['datacenter']
            dc.allocate_vm(vm)

            # Track metrics
            self.metrics['placed_vms'] += 1
            self.metrics['total_response_time_ms'] += best['latency_ms']

            # Record placement decision with scoring details
            self.metrics['placement_decisions'].append({
                'vm_id': vm['vm_id'],
                'datacenter': dc.id,
                'datacenter_type': best['type'],
                'distance_km': best['distance_km'],
                'latency_ms': best['latency_ms'],
                'weighted_score': best['score'],
                'timestamp': current_time.isoformat()
            })

            return dc.id, True

        # Step 6: VM failed to place (no suitable datacenter found)
        self.metrics['failed_vms'] += 1

        self.metrics['placement_decisions'].append({
            'vm_id': vm['vm_id'],
            'datacenter': None,
            'datacenter_type': None,
            'distance_km': None,
            'latency_ms': None,
            'failed': True,
            'reason': 'No datacenter met constraints (capacity, latency, or RES)',
            'timestamp': current_time.isoformat()
        })

        return None, False
    
    def update_datacenter_state(self, hour_data: Dict):
        """Update datacenter states from synchronized dataset"""
        for dc_id, dc in self.datacenters.items():
            country = dc.country.lower()
            
            # Update renewable generation
            renewable_col = f'{country}_total_renewable_mw'
            if renewable_col in hour_data:
                dc.renewable_generation_mw = hour_data[renewable_col]
            
            # Update carbon intensity
            carbon_col = f'{country}_carbon_intensity'
            if carbon_col in hour_data:
                dc.carbon_intensity_gco2_kwh = hour_data[carbon_col]
            
            # Update renewable percentage
            renewable_pct_col = f'{country}_renewable_pct'
            if renewable_pct_col in hour_data:
                dc.renewable_pct = hour_data[renewable_pct_col]
            
            # Update datacenter classification
            dc_type_col = f'{country}_datacenter_type'
            if dc_type_col in hour_data:
                dc.datacenter_type = hour_data[dc_type_col]
    
    def calculate_hourly_metrics(self):
        """Calculate metrics for the current hour"""
        total_energy = 0
        renewable_energy = 0
        carbon_emissions = 0
        
        for dc in self.datacenters.values():
            # Energy consumption
            energy_kwh = dc.calculate_total_energy_kwh(hours=1)
            total_energy += energy_kwh
            
            # Renewable energy portion
            renewable_portion = energy_kwh * (dc.renewable_pct / 100)
            renewable_energy += renewable_portion
            
            # Carbon emissions (only from brown energy)
            brown_energy = energy_kwh - renewable_portion
            carbon_kg = (brown_energy * dc.carbon_intensity_gco2_kwh) / 1000
            carbon_emissions += carbon_kg
        
        self.metrics['total_energy_kwh'] += total_energy
        self.metrics['renewable_energy_kwh'] += renewable_energy
        self.metrics['carbon_emissions_kg'] += carbon_emissions
    
    def calculate_final_metrics(self) -> Dict:
        """
        Calculate M1-M4 metrics (Miao et al. 2024)
        
        M1: RES Utilization (%)
        M2: Carbon Reduction (%) - compared to baseline
        M3: Average Response Time (ms)
        M4: Failure Rate (%)
        """
        
        m1_res_utilization = (
            (self.metrics['renewable_energy_kwh'] / self.metrics['total_energy_kwh'] * 100)
            if self.metrics['total_energy_kwh'] > 0 else 0
        )
        
        # M2: Carbon reduction (need baseline for comparison - placeholder)
        m2_carbon_reduction = 0  # Will calculate after baseline run
        
        m3_avg_response_time = (
            self.metrics['total_response_time_ms'] / self.metrics['placed_vms']
            if self.metrics['placed_vms'] > 0 else 0
        )
        
        m4_failure_rate = (
            self.metrics['failed_vms'] / self.metrics['total_vms'] * 100
            if self.metrics['total_vms'] > 0 else 0
        )
        
        return {
            'M1_RES_Utilization_pct': m1_res_utilization,
            'M2_Carbon_Reduction_pct': m2_carbon_reduction,
            'M3_Avg_Response_Time_ms': m3_avg_response_time,
            'M4_Failure_Rate_pct': m4_failure_rate,
            'total_energy_kwh': self.metrics['total_energy_kwh'],
            'renewable_energy_kwh': self.metrics['renewable_energy_kwh'],
            'carbon_emissions_kg': self.metrics['carbon_emissions_kg'],
            'total_vms': self.metrics['total_vms'],
            'placed_vms': self.metrics['placed_vms'],
            'failed_vms': self.metrics['failed_vms'],
            'latency_rejections': self.metrics['latency_rejections'],
            'res_rejections': self.metrics['res_rejections']
        }


def create_sample_datacenters() -> List[Datacenter]:
    """Create 5 sample datacenters for testing"""
    
    # Based on European countries from dataset
    datacenters = [
        Datacenter(
            id='DC_IT',
            name='Milan Datacenter',
            country='Italy',
            latitude=45.4642,
            longitude=9.1900,
            num_servers=100,
            cpu_per_server=32,
            ram_per_server_mb=256 * 1024,  # 256 GB
            power_idle_w=200,
            power_max_w=400,
            pue=1.2
        ),
        Datacenter(
            id='DC_SE',
            name='Stockholm Datacenter',
            country='Sweden',
            latitude=59.3293,
            longitude=18.0686,
            num_servers=100,
            cpu_per_server=32,
            ram_per_server_mb=256 * 1024,
            power_idle_w=200,
            power_max_w=400,
            pue=1.1  # More efficient cooling
        ),
        Datacenter(
            id='DC_ES',
            name='Madrid Datacenter',
            country='Spain',
            latitude=40.4168,
            longitude=-3.7038,
            num_servers=100,
            cpu_per_server=32,
            ram_per_server_mb=256 * 1024,
            power_idle_w=200,
            power_max_w=400,
            pue=1.2
        ),
        Datacenter(
            id='DC_FR',
            name='Paris Datacenter',
            country='France',
            latitude=48.8566,
            longitude=2.3522,
            num_servers=100,
            cpu_per_server=32,
            ram_per_server_mb=256 * 1024,
            power_idle_w=200,
            power_max_w=400,
            pue=1.15
        ),
        Datacenter(
            id='DC_DE',
            name='Frankfurt Datacenter',
            country='Germany',
            latitude=50.1109,
            longitude=8.6821,
            num_servers=100,
            cpu_per_server=32,
            ram_per_server_mb=256 * 1024,
            power_idle_w=200,
            power_max_w=400,
            pue=1.1
        )
    ]
    
    return datacenters


def print_placement_analysis(scheduler: ECMRScheduler):
    """Print detailed placement distribution analysis"""
    from collections import defaultdict

    print()
    print("="*80)
    print("PLACEMENT DISTRIBUTION ANALYSIS")
    print("="*80)
    print()

    placements = scheduler.metrics['placement_decisions']

    # 1. VM Distribution by Datacenter
    print("[1] VM Distribution by Datacenter")
    print("-"*80)
    dc_counts = defaultdict(int)
    dc_types = {}
    dc_scores = defaultdict(list)
    dc_latencies = defaultdict(list)

    for p in placements:
        dc = p.get('datacenter')
        if dc:
            dc_counts[dc] += 1
            dc_types[dc] = p.get('datacenter_type', 'Unknown')
            if 'weighted_score' in p:
                dc_scores[dc].append(p['weighted_score'])
            if 'latency_ms' in p:
                dc_latencies[dc].append(p['latency_ms'])

    total_placed = sum(dc_counts.values())
    if total_placed > 0:
        for dc in sorted(dc_counts.keys()):
            count = dc_counts[dc]
            pct = (count / total_placed * 100)
            dc_type = dc_types.get(dc, 'Unknown')
            print(f'{dc:10} [{dc_type}]: {count:3d} VMs ({pct:5.1f}%)')
    else:
        print("No VMs placed")

    print()

    # 2. Green vs Brown Distribution
    print("[2] Green (DG) vs Brown (DB) Datacenter Usage")
    print("-"*80)
    green_count = sum(1 for p in placements if p.get('datacenter_type') == 'DG')
    brown_count = sum(1 for p in placements if p.get('datacenter_type') == 'DB')
    total = green_count + brown_count

    if total > 0:
        print(f'Green (DG) datacenters:  {green_count:3d} VMs ({green_count/total*100:5.1f}%)')
        print(f'Brown (DB) datacenters:  {brown_count:3d} VMs ({brown_count/total*100:5.1f}%)')

    print()

    # 3. Weighted Score Analysis
    print("[3] Weighted Score Analysis (Lower is Better)")
    print("-"*80)
    if dc_scores:
        for dc in sorted(dc_scores.keys()):
            scores = dc_scores[dc]
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            print(f'{dc:10}: Avg={avg_score:.3f}, Min={min_score:.3f}, Max={max_score:.3f} ({len(scores)} VMs)')

        all_scores = [s for scores in dc_scores.values() for s in scores]
        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
        print(f'\nOverall average score: {overall_avg:.3f}')

    print()

    # 4. Latency Analysis
    print("[4] Latency Distribution")
    print("-"*80)
    if dc_latencies:
        for dc in sorted(dc_latencies.keys()):
            latencies = dc_latencies[dc]
            avg_lat = sum(latencies) / len(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
            print(f'{dc:10}: Avg={avg_lat:.2f}ms, Min={min_lat:.2f}ms, Max={max_lat:.2f}ms')

        all_latencies = [l for lats in dc_latencies.values() for l in lats]
        overall_avg_lat = sum(all_latencies) / len(all_latencies) if all_latencies else 0
        print(f'\nOverall average latency: {overall_avg_lat:.2f}ms (Threshold: {scheduler.latency_threshold_ms}ms)')

    print()

    # 5. Constraint Enforcement Summary
    print("[5] Constraint Enforcement Summary")
    print("-"*80)
    lat_rej = scheduler.metrics.get('latency_rejections', 0)
    res_rej = scheduler.metrics.get('res_rejections', 0)
    total_vms = scheduler.metrics.get('total_vms', 0)
    placed_vms = scheduler.metrics.get('placed_vms', 0)
    failed_vms = scheduler.metrics.get('failed_vms', 0)

    print(f"Latency threshold rejections: {lat_rej}")
    print(f"RES availability rejections:  {res_rej}")
    print(f"Total VMs processed:          {total_vms}")
    print(f"Successfully placed:          {placed_vms}")
    print(f"Failed placements:            {failed_vms}")

    total_rejections = lat_rej + res_rej
    if total_vms > 0:
        avg_rejections = total_rejections / total_vms
        print(f"\nAverage rejections per VM:    {avg_rejections:.1f}")
        print(f"(Algorithm evaluated ~{int(avg_rejections+1)} datacenters per VM on average)")

    print()
    print("="*80)


def run_ecmr_simulation(synchronized_data_path: str, 
                        duration_hours: int = 24,
                        max_vms: int = 100,
                        seed: int = 42):
    """
    Run ECMR baseline simulation
    
    Parameters:
    - synchronized_data_path: Path to synchronized dataset CSV
    - duration_hours: Simulation duration
    - max_vms: Maximum VMs to simulate
    - seed: Random seed
    """
    
    np.random.seed(seed)
    
    print("="*80)
    print("ECMR BASELINE SIMULATION")
    print("="*80)
    
    # Load synchronized data
    print(f"\n[1] Loading synchronized dataset: {synchronized_data_path}")
    df = pd.read_csv(synchronized_data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Limit duration
    df = df.head(duration_hours)
    print(f"    Simulating {len(df)} hours")
    print(f"    Total VM arrivals in dataset: {df['vm_arrivals'].sum()}")
    
    # Initialize datacenters
    print(f"\n[2] Initializing {5} datacenters...")
    datacenters = create_sample_datacenters()
    for dc in datacenters:
        print(f"    {dc.id}: {dc.name} ({dc.country}) - "
              f"{dc.total_cpus} CPUs, {dc.total_ram_mb/1024:.0f} GB RAM")
    
    # Initialize scheduler with enhanced parameters
    scheduler = ECMRScheduler(datacenters, weights=(0.33, 0.33, 0.34), latency_threshold_ms=100.0)
    print(f"\n[3] Initialized ECMR scheduler:")
    print(f"    Weights: w1(energy)={scheduler.w1}, w2(carbon)={scheduler.w2}, w3(latency)={scheduler.w3}")
    print(f"    Latency threshold: {scheduler.latency_threshold_ms} ms")
    
    # Simulate hour by hour
    print(f"\n[4] Running simulation...")
    
    total_vms_simulated = 0
    
    for idx, row in df.iterrows():
        hour = row['timestamp']
        vm_arrivals = int(row['vm_arrivals'])
        
        # Update datacenter states
        scheduler.update_datacenter_state(row)
        
        # Generate and schedule VMs for this hour
        for i in range(vm_arrivals):
            if total_vms_simulated >= max_vms:
                break
            
            # Create VM request
            vm = {
                'vm_id': total_vms_simulated + 1,
                'timestamp': hour,
                'num_cpus': np.random.randint(1, 8),  # 1-8 CPUs
                'ram_mb': np.random.randint(2, 16) * 1024,  # 2-16 GB
                'execution_time_sec': np.random.randint(300, 7200),  # 5min-2hrs
                'mips': np.random.randint(1000, 5000)
            }
            
            # Schedule VM
            scheduler.metrics['total_vms'] += 1
            dc_id, success = scheduler.schedule_vm(vm, hour)
            
            total_vms_simulated += 1
        
        if total_vms_simulated >= max_vms:
            break
        
        # Calculate hourly metrics
        scheduler.calculate_hourly_metrics()
        
        if (idx + 1) % 6 == 0:
            print(f"    Hour {idx+1:3d}: {vm_arrivals:3d} VMs, "
                  f"Placed: {scheduler.metrics['placed_vms']:4d}, "
                  f"Failed: {scheduler.metrics['failed_vms']:3d}")
    
    # Calculate final metrics
    print(f"\n[5] Calculating final metrics...")
    final_metrics = scheduler.calculate_final_metrics()
    
    print("\n" + "="*80)
    print("FINAL METRICS (M1-M4)")
    print("="*80)
    print(f"M1: RES Utilization:        {final_metrics['M1_RES_Utilization_pct']:.2f}%")
    print(f"M2: Carbon Reduction:       {final_metrics['M2_Carbon_Reduction_pct']:.2f}%")
    print(f"M3: Avg Response Time:      {final_metrics['M3_Avg_Response_Time_ms']:.2f} ms")
    print(f"M4: Failure Rate:           {final_metrics['M4_Failure_Rate_pct']:.2f}%")
    print(f"\nTotal Energy:               {final_metrics['total_energy_kwh']:.2f} kWh")
    print(f"Renewable Energy:           {final_metrics['renewable_energy_kwh']:.2f} kWh")
    print(f"Carbon Emissions:           {final_metrics['carbon_emissions_kg']:.2f} kg")
    print(f"\nTotal VMs:                  {final_metrics['total_vms']}")
    print(f"Placed VMs:                 {final_metrics['placed_vms']}")
    print(f"Failed VMs:                 {final_metrics['failed_vms']}")
    print(f"\nConstraint Rejections:")
    print(f"  Latency threshold:        {final_metrics['latency_rejections']}")
    print(f"  RES availability:         {final_metrics['res_rejections']}")
    print("="*80)

    # Print placement distribution analysis
    print_placement_analysis(scheduler)

    return scheduler, final_metrics


def main():
    parser = argparse.ArgumentParser(description='ECMR Baseline Simulation')
    parser.add_argument('--data', required=True, 
                        help='Synchronized dataset CSV file')
    parser.add_argument('--duration', type=int, default=24,
                        help='Simulation duration in hours (default: 24)')
    parser.add_argument('--max-vms', type=int, default=100,
                        help='Maximum VMs to simulate (default: 100)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--output', '-o', default='ecmr_results.json',
                        help='Output JSON file for results')
    
    args = parser.parse_args()
    
    # Run simulation
    scheduler, final_metrics = run_ecmr_simulation(
        synchronized_data_path=args.data,
        duration_hours=args.duration,
        max_vms=args.max_vms,
        seed=args.seed
    )
    
    # Save results
    results = {
        'configuration': {
            'duration_hours': args.duration,
            'max_vms': args.max_vms,
            'seed': args.seed,
            'weights': {'w1_energy': scheduler.w1, 'w2_carbon': scheduler.w2, 'w3_latency': scheduler.w3}
        },
        'metrics': final_metrics,
        'placement_decisions': scheduler.metrics['placement_decisions']
    }
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {args.output}")


if __name__ == '__main__':
    main()