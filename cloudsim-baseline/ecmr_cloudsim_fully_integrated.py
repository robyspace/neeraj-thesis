#!/usr/bin/env python3
"""
ECMR Baseline FULLY INTEGRATED with CloudSimPlus
Uses enhanced ECMR algorithm (weighted scoring, RES checking, latency threshold)
to control CloudSim Plus VM placement via Py4J

Usage:
1. Build Java: mvn clean package
2. Start Java Gateway: java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.Py4JGateway
3. Run this script: python3 ecmr_cloudsim_fully_integrated.py --data output/synchronized_dataset_2024.csv --max-vms 100
"""

import pandas as pd
import numpy as np
from py4j.java_gateway import JavaGateway
import json
import time
import argparse
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import defaultdict
import math


@dataclass
class Datacenter:
    """Datacenter model for ECMR algorithm"""
    id: str
    name: str
    country: str
    latitude: float
    longitude: float
    total_cpus: int
    used_cpus: int
    total_ram_mb: int
    used_ram_mb: int
    num_servers: int
    cpu_per_server: int
    ram_per_server_mb: int
    power_idle_w: float
    power_max_w: float
    pue: float

    # Dynamic state (updated from dataset)
    renewable_generation_mw: float = 0.0
    renewable_pct: float = 0.0
    carbon_intensity_gco2_kwh: float = 0.0
    datacenter_type: str = 'DB'  # 'DG' (green) or 'DB' (brown)

    @property
    def available_cpus(self):
        return self.total_cpus - self.used_cpus

    @property
    def available_ram_mb(self):
        return self.total_ram_mb - self.used_ram_mb

    @property
    def cpu_utilization(self):
        return self.used_cpus / self.total_cpus if self.total_cpus > 0 else 0

    def can_host_vm(self, vm: Dict) -> bool:
        return (self.available_cpus >= vm['num_cpus'] and
                self.available_ram_mb >= vm['ram_mb'])

    def allocate_vm(self, vm: Dict):
        self.used_cpus += vm['num_cpus']
        self.used_ram_mb += vm['ram_mb']


class ECMRScheduler:
    """Enhanced ECMR VM Scheduling Algorithm"""

    def __init__(self, datacenters: List[Datacenter],
                 weights=(0.33, 0.33, 0.34),
                 user_location=(48.8566, 2.3522),
                 latency_threshold_ms=100.0):
        self.datacenters = {dc.id: dc for dc in datacenters}
        self.w1, self.w2, self.w3 = weights
        self.user_location = user_location
        self.latency_threshold_ms = latency_threshold_ms

        self.metrics = {
            'total_vms': 0,
            'placed_vms': 0,
            'failed_vms': 0,
            'latency_rejections': 0,
            'res_rejections': 0,
            'placement_decisions': []
        }

    def calculate_distance(self, dc: Datacenter) -> float:
        """Haversine distance from user to datacenter (km)"""
        lat1, lon1 = self.user_location
        lat2, lon2 = dc.latitude, dc.longitude

        R = 6371  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def classify_datacenters(self) -> Tuple[List[Datacenter], List[Datacenter]]:
        """Classify as DG (green) or DB (brown)"""
        dg = []
        db = []
        for dc in self.datacenters.values():
            if dc.renewable_pct >= 50.0:  # Threshold: 50% renewable
                dc.datacenter_type = 'DG'
                dg.append(dc)
            else:
                dc.datacenter_type = 'DB'
                db.append(dc)
        return dg, db

    def estimate_vm_energy_kwh(self, vm: Dict, hours=1.0) -> float:
        """Estimate VM energy consumption (kWh)"""
        estimated_power_w = vm['num_cpus'] * 50.0
        return (estimated_power_w * hours) / 1000.0

    def check_res_availability(self, dc: Datacenter, vm: Dict) -> bool:
        """Check if datacenter has sufficient renewable energy"""
        if dc.datacenter_type == 'DB':
            return True

        energy_needed_kwh = self.estimate_vm_energy_kwh(vm, 1.0)
        available_res_kwh = dc.renewable_generation_mw * 1000.0
        return available_res_kwh > energy_needed_kwh

    def calculate_weighted_score(self, dc: Datacenter, vm: Dict) -> float:
        """Calculate multi-objective weighted score (lower is better)"""
        # Energy component
        current_util = dc.cpu_utilization
        new_util = (dc.used_cpus + vm['num_cpus']) / dc.total_cpus
        delta_util = new_util - current_util
        incremental_energy = (dc.power_max_w - dc.power_idle_w) * delta_util * dc.pue

        # Carbon component
        carbon_intensity = dc.carbon_intensity_gco2_kwh

        # Latency component
        distance_km = self.calculate_distance(dc)
        latency_ms = distance_km * 0.1

        # Normalize and weight
        norm_energy = incremental_energy / 1000.0
        norm_carbon = carbon_intensity / 500.0
        norm_latency = latency_ms / 100.0

        score = (self.w1 * norm_energy +
                self.w2 * norm_carbon +
                self.w3 * norm_latency)

        return score

    def schedule_vm(self, vm: Dict, current_time: datetime) -> Tuple[str, bool, Dict]:
        """
        Enhanced ECMR scheduling with weighted multi-objective optimization
        Returns: (datacenter_id, success, decision_details)
        """
        self.metrics['total_vms'] += 1

        # Classify datacenters
        dg_datacenters, db_datacenters = self.classify_datacenters()

        # Evaluate DG datacenters
        candidates = []

        for dc in dg_datacenters:
            if not dc.can_host_vm(vm):
                continue

            distance_km = self.calculate_distance(dc)
            latency_ms = distance_km * 0.1

            # Check latency threshold
            if latency_ms > self.latency_threshold_ms:
                self.metrics['latency_rejections'] += 1
                continue

            # Check RES availability
            if not self.check_res_availability(dc, vm):
                self.metrics['res_rejections'] += 1
                continue

            score = self.calculate_weighted_score(dc, vm)

            candidates.append({
                'datacenter': dc,
                'score': score,
                'distance_km': distance_km,
                'latency_ms': latency_ms,
                'type': 'DG'
            })

        # If no suitable DG, try DB datacenters
        if not candidates:
            for dc in db_datacenters:
                if not dc.can_host_vm(vm):
                    continue

                distance_km = self.calculate_distance(dc)
                latency_ms = distance_km * 0.1

                if latency_ms > self.latency_threshold_ms:
                    self.metrics['latency_rejections'] += 1
                    continue

                score = self.calculate_weighted_score(dc, vm)

                candidates.append({
                    'datacenter': dc,
                    'score': score,
                    'distance_km': distance_km,
                    'latency_ms': latency_ms,
                    'type': 'DB'
                })

        # Select best datacenter
        if candidates:
            candidates.sort(key=lambda x: x['score'])
            best = candidates[0]

            dc = best['datacenter']
            dc.allocate_vm(vm)

            self.metrics['placed_vms'] += 1

            decision = {
                'vm_id': vm['vm_id'],
                'ecmr_selected_datacenter': dc.id,
                'datacenter_type': best['type'],
                'distance_km': best['distance_km'],
                'latency_ms': best['latency_ms'],
                'weighted_score': best['score'],
                'timestamp': current_time.isoformat(),
                'success': True
            }

            self.metrics['placement_decisions'].append(decision)
            return dc.id, True, decision

        # VM failed to place
        self.metrics['failed_vms'] += 1

        decision = {
            'vm_id': vm['vm_id'],
            'ecmr_selected_datacenter': None,
            'datacenter_type': None,
            'success': False,
            'reason': 'No datacenter met constraints',
            'timestamp': current_time.isoformat()
        }

        self.metrics['placement_decisions'].append(decision)
        return None, False, decision


class ECMRCloudSimFullyIntegrated:
    """Fully integrated ECMR + CloudSim simulation"""

    def __init__(self):
        print("="*80)
        print("ECMR-CloudSim FULLY INTEGRATED SIMULATION")
        print("="*80)
        print()

        print("[1/5] Connecting to Java Gateway at localhost:25333...")
        time.sleep(1)
        self.gateway = JavaGateway()
        self.java_gateway = self.gateway.entry_point
        print("      Connected to Java Gateway successfully")
        print()

        self.datacenters = []
        self.scheduler = None

    def initialize(self):
        """Initialize CloudSim simulation"""
        print("[2/5] Initializing CloudSim simulation...")
        java_config = self.gateway.jvm.java.util.HashMap()
        self.java_gateway.initializeSimulation(java_config)
        print("      CloudSim initialized")
        print()

    def create_datacenters_with_ecmr(self):
        """Create both CloudSim datacenters AND Python ECMR datacenter models"""
        print("[3/5] Creating datacenters (CloudSim + ECMR models)...")

        # Datacenter configurations
        dc_configs = [
            {'id': 'DC_IT', 'name': 'Milan Datacenter', 'country': 'italy',
             'lat': 45.4642, 'lon': 9.1900, 'num_servers': 100, 'pue': 1.2},
            {'id': 'DC_SE', 'name': 'Stockholm Datacenter', 'country': 'sweden',
             'lat': 59.3293, 'lon': 18.0686, 'num_servers': 100, 'pue': 1.1},
            {'id': 'DC_ES', 'name': 'Madrid Datacenter', 'country': 'spain',
             'lat': 40.4168, 'lon': -3.7038, 'num_servers': 100, 'pue': 1.2},
            {'id': 'DC_FR', 'name': 'Paris Datacenter', 'country': 'france',
             'lat': 48.8566, 'lon': 2.3522, 'num_servers': 100, 'pue': 1.1},
            {'id': 'DC_DE', 'name': 'Frankfurt Datacenter', 'country': 'germany',
             'lat': 50.1109, 'lon': 8.6821, 'num_servers': 100, 'pue': 1.15}
        ]

        for config in dc_configs:
            # Create CloudSim datacenter (Java)
            self.java_gateway.createDatacenter(
                config['id'],
                config['num_servers'],
                32,  # CPUs per server
                256 * 1024,  # RAM per server (256 GB)
                100.0,  # Power idle
                300.0   # Power max
            )

            # Create ECMR datacenter model (Python)
            dc = Datacenter(
                id=config['id'],
                name=config['name'],
                country=config['country'],
                latitude=config['lat'],
                longitude=config['lon'],
                total_cpus=config['num_servers'] * 32,
                used_cpus=0,
                total_ram_mb=config['num_servers'] * 256 * 1024,
                used_ram_mb=0,
                num_servers=config['num_servers'],
                cpu_per_server=32,
                ram_per_server_mb=256 * 1024,
                power_idle_w=100.0,
                power_max_w=300.0,
                pue=config['pue']
            )

            self.datacenters.append(dc)
            print(f"      Created: {config['id']} ({config['name']})")

        print()

    def run_integrated_simulation(self, data_path, max_vms=100):
        """Run simulation with ECMR deciding placement, CloudSim executing"""
        print("[4/5] Running integrated ECMR + CloudSim simulation...")
        print()

        # Load synchronized data
        df = pd.read_csv(data_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"  Loaded {len(df)} hours of data")
        print()

        # Initialize ECMR scheduler
        self.scheduler = ECMRScheduler(
            self.datacenters,
            weights=(0.33, 0.33, 0.34),
            latency_threshold_ms=100.0
        )

        print(f"  ECMR Configuration:")
        print(f"    Weights: w1(energy)={self.scheduler.w1}, w2(carbon)={self.scheduler.w2}, w3(latency)={self.scheduler.w3}")
        print(f"    Latency threshold: {self.scheduler.latency_threshold_ms}ms")
        print()

        # Process VMs
        print(f"  Processing VMs with ECMR scheduling...")
        vm_count = 0
        ecmr_placements = {}  # Track ECMR decisions

        for idx, row in df.iterrows():
            if vm_count >= max_vms:
                break

            # Update datacenter states from data
            for dc in self.datacenters:
                country_col = dc.country.lower()
                dc.renewable_generation_mw = row.get(f'{country_col}_total_renewable_mw', 0)
                dc.renewable_pct = row.get(f'{country_col}_renewable_pct', 0)
                dc.carbon_intensity_gco2_kwh = row.get(f'{country_col}_carbon_intensity', 0)

            # Generate VMs for this hour
            num_vms = min(int(row['vm_arrivals']), max_vms - vm_count)

            for i in range(num_vms):
                vm_id = vm_count
                vm = {
                    'vm_id': vm_id,
                    'num_cpus': np.random.randint(1, 8),
                    'ram_mb': np.random.randint(2, 16) * 1024
                }
                vm['mips'] = vm['num_cpus'] * 1000

                # ECMR decides which datacenter
                selected_dc_id, success, decision = self.scheduler.schedule_vm(
                    vm, row['timestamp']
                )

                if success:
                    # Submit to CloudSim with ECMR's decision
                    cloudsim_success = self.java_gateway.submitVMToDatacenter(
                        vm_id, vm['num_cpus'], vm['ram_mb'], vm['mips'], selected_dc_id
                    )

                    ecmr_placements[vm_id] = {
                        'ecmr_decision': selected_dc_id,
                        'cloudsim_success': cloudsim_success
                    }

                    vm_count += 1

                    if vm_count % 10 == 0:
                        print(f"    Processed {vm_count} VMs...")

        print(f"  Total VMs processed: {vm_count}")
        print()

        # Run CloudSim simulation
        print(f"  Running CloudSim simulation...")
        start_time = time.time()
        self.java_gateway.runSimulation()
        elapsed = time.time() - start_time
        print(f"  CloudSim simulation completed in {elapsed:.2f} seconds")
        print()

        return ecmr_placements

    def get_results(self):
        """Get results from both ECMR and CloudSim"""
        print("[5/5] Collecting results...")
        print()

        # Get CloudSim results (returns Java Map, convert to Python dict)
        java_results = self.java_gateway.getResults()
        cloudsim_results = {}
        for key in java_results:
            cloudsim_results[str(key)] = java_results[key]

        # Combine with ECMR metrics
        combined_results = {
            'ecmr_metrics': {
                'total_vms': self.scheduler.metrics['total_vms'],
                'placed_vms': self.scheduler.metrics['placed_vms'],
                'failed_vms': self.scheduler.metrics['failed_vms'],
                'latency_rejections': self.scheduler.metrics['latency_rejections'],
                'res_rejections': self.scheduler.metrics['res_rejections']
            },
            'cloudsim_metrics': cloudsim_results,
            'ecmr_decisions': self.scheduler.metrics['placement_decisions']
        }

        # Print summary
        print("="*80)
        print("SIMULATION RESULTS")
        print("="*80)
        print()
        print("ECMR Algorithm:")
        print(f"  Total VMs: {combined_results['ecmr_metrics']['total_vms']}")
        print(f"  Successfully placed: {combined_results['ecmr_metrics']['placed_vms']}")
        print(f"  Failed: {combined_results['ecmr_metrics']['failed_vms']}")
        print(f"  Latency rejections: {combined_results['ecmr_metrics']['latency_rejections']}")
        print(f"  RES rejections: {combined_results['ecmr_metrics']['res_rejections']}")
        print()
        print("CloudSim Execution:")
        print(f"  Total VMs: {cloudsim_results.get('total_vms', 0)}")
        print(f"  Successful: {cloudsim_results.get('successful_vms', 0)}")
        print(f"  Failed: {cloudsim_results.get('failed_vms', 0)}")
        print(f"  Total Energy: {cloudsim_results.get('total_energy_kwh', 0):.2f} kWh")
        print()

        # Placement distribution
        self.print_placement_distribution()

        return combined_results

    def print_placement_distribution(self):
        """Print ECMR placement distribution analysis"""
        print("="*80)
        print("ECMR PLACEMENT DISTRIBUTION")
        print("="*80)
        print()

        dc_counts = defaultdict(int)
        dc_types = {}

        for decision in self.scheduler.metrics['placement_decisions']:
            if decision.get('success'):
                dc = decision['ecmr_selected_datacenter']
                dc_counts[dc] += 1
                dc_types[dc] = decision['datacenter_type']

        print("VM Distribution by Datacenter (ECMR Decisions):")
        print("-"*80)
        total = sum(dc_counts.values())
        for dc in sorted(dc_counts.keys()):
            count = dc_counts[dc]
            pct = (count / total * 100) if total > 0 else 0
            dc_type = dc_types.get(dc, '?')
            print(f"  {dc:10} [{dc_type}]: {count:3d} VMs ({pct:5.1f}%)")

        print()
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description='ECMR-CloudSim Fully Integrated Simulation')
    parser.add_argument('--data', required=True, help='Synchronized dataset CSV')
    parser.add_argument('--max-vms', type=int, default=100, help='Max VMs to simulate')
    parser.add_argument('--output', default='ecmr_cloudsim_integrated_results.json',
                       help='Output JSON file')

    args = parser.parse_args()

    try:
        # Create integration
        integration = ECMRCloudSimFullyIntegrated()

        # Initialize
        integration.initialize()

        # Create datacenters
        integration.create_datacenters_with_ecmr()

        # Run simulation
        placements = integration.run_integrated_simulation(args.data, args.max_vms)

        # Get results
        results = integration.get_results()

        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n Results saved to: {args.output}")
        print()
        print(" ECMR-CloudSim integration completed successfully!")
        print()

    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
