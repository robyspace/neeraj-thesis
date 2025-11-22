#!/usr/bin/env python3
"""
ECMR Algorithm + Heterogeneous CloudSim Infrastructure Integration

This integrates:
1. Complete ECMR placement algorithm
2. Heterogeneous servers (3 types from Miao2024.pdf Table 3)
3. Non-linear power models (11-point curves from Table 4)
4. VM types (4 types from Table 5)
5. Real carbon intensity data from synchronized_dataset_2024.csv
6. Multi-datacenter deployment across 5 European locations

Usage:
1. Build: mvn clean package
2. Start Gateway: java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.Py4JGatewayEnhanced
3. Run: python3 ecmr_heterogeneous_integration.py --data output/synchronized_dataset_2024.csv --hours 24 --vms-per-hour 10
"""

import pandas as pd
import numpy as np
from py4j.java_gateway import JavaGateway
import argparse
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

# European datacenter locations
DATACENTERS = {
    'DC_ITALY': {'name': 'Milan DC', 'country': 'italy', 'lat': 45.4642, 'lon': 9.1900, 'pue': 1.2},
    'DC_FRANCE': {'name': 'Paris DC', 'country': 'france', 'lat': 48.8566, 'lon': 2.3522, 'pue': 1.15},
    'DC_SWEDEN': {'name': 'Stockholm DC', 'country': 'sweden', 'lat': 59.3293, 'lon': 18.0686, 'pue': 1.1},
    'DC_NETHERLANDS': {'name': 'Amsterdam DC', 'country': 'netherlands', 'lat': 52.3676, 'lon': 4.9041, 'pue': 1.2},
    'DC_SPAIN': {'name': 'Madrid DC', 'country': 'spain', 'lat': 40.4168, 'lon': -3.7038, 'pue': 1.25}
}

# European cities for random user locations
EUROPEAN_CITIES = [
    ('Paris', 48.8566, 2.3522),
    ('London', 51.5074, -0.1278),
    ('Berlin', 52.5200, 13.4050),
    ('Madrid', 40.4168, -3.7038),
    ('Rome', 41.9028, 12.4964),
    ('Amsterdam', 52.3676, 4.9041),
    ('Brussels', 50.8503, 4.3517),
    ('Vienna', 48.2082, 16.3738),
    ('Stockholm', 59.3293, 18.0686),
    ('Copenhagen', 55.6761, 12.5683),
    ('Oslo', 59.9139, 10.7522),
    ('Helsinki', 60.1699, 24.9384),
    ('Warsaw', 52.2297, 21.0122),
    ('Prague', 50.0755, 14.4378),
    ('Budapest', 47.4979, 19.0402),
    ('Lisbon', 38.7223, -9.1393),
    ('Athens', 37.9838, 23.7275),
    ('Dublin', 53.3498, -6.2603),
    ('Zurich', 47.3769, 8.5417),
    ('Barcelona', 41.3851, 2.1734)
]

# VM type distribution (matches Miao2024.pdf Table 5)
VM_TYPES = ['small', 'medium', 'large', 'xlarge']
VM_TYPE_WEIGHTS = [0.4, 0.3, 0.2, 0.1]  # 40% small, 30% medium, 20% large, 10% xlarge


@dataclass
class DatacenterState:
    """Track datacenter state for ECMR algorithm"""
    id: str
    name: str
    country: str
    latitude: float
    longitude: float
    pue: float

    # Dynamic state updated from CSV
    carbon_intensity: float = 0.0  # gCO2/kWh
    renewable_pct: float = 0.0     # %
    dc_type: str = 'DG'            # 'DG' (Green) or 'DB' (Brown)
    hydro_mw: float = 0.0
    solar_mw: float = 0.0
    wind_mw: float = 0.0

    # Tracking
    vms_placed: int = 0
    energy_kwh: float = 0.0
    carbon_kg: float = 0.0


class ECMRHeterogeneousScheduler:
    """
    ECMR Algorithm adapted for heterogeneous infrastructure

    Selects optimal datacenter based on:
    - Carbon intensity (primary)
    - Renewable energy percentage
    - Energy efficiency (PUE)
    - Network latency
    """

    def __init__(self, datacenters: Dict[str, DatacenterState],
                 user_location: Tuple[float, float] = (48.8566, 2.3522),  # Default: Paris
                 weights: Tuple[float, float, float] = (0.5, 0.3, 0.2)):  # carbon, renewable, latency
        """
        Initialize ECMR scheduler

        Args:
            datacenters: Dict of datacenter states
            user_location: (lat, lon) of user
            weights: (w_carbon, w_renewable, w_latency) importance weights
        """
        self.datacenters = datacenters
        self.user_location = user_location
        self.w_carbon, self.w_renewable, self.w_latency = weights

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great circle distance between two points"""
        R = 6371  # Earth radius in km

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def calculate_latency(self, dc: DatacenterState) -> float:
        """Estimate network latency based on distance"""
        distance_km = self.haversine_distance(
            self.user_location[0], self.user_location[1],
            dc.latitude, dc.longitude
        )
        # Rough estimate: 1ms per 100km + 10ms base latency
        return 10 + (distance_km / 100)

    def normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to [0, 1] range"""
        if max_val == min_val:
            return 0.5
        return (value - min_val) / (max_val - min_val)

    def select_datacenter(self, vm: Dict) -> str:
        """
        ECMR Algorithm: Select optimal datacenter for VM placement

        Scoring function:
        Score = w_carbon * S_carbon + w_renewable * S_renewable + w_latency * S_latency

        Where:
        - S_carbon: Lower carbon intensity is better (inverse normalized)
        - S_renewable: Higher renewable % is better (normalized)
        - S_latency: Lower latency is better (inverse normalized)

        Returns: Selected datacenter ID
        """

        if not self.datacenters:
            raise ValueError("No datacenters available")

        # Calculate metrics for all datacenters
        carbon_values = [dc.carbon_intensity for dc in self.datacenters.values()]
        renewable_values = [dc.renewable_pct for dc in self.datacenters.values()]
        latency_values = [self.calculate_latency(dc) for dc in self.datacenters.values()]

        # Normalize to [0, 1]
        min_carbon, max_carbon = min(carbon_values), max(carbon_values)
        min_renewable, max_renewable = min(renewable_values), max(renewable_values)
        min_latency, max_latency = min(latency_values), max(latency_values)

        scores = {}
        for dc_id, dc in self.datacenters.items():
            # Lower carbon is better (invert normalization)
            s_carbon = 1 - self.normalize(dc.carbon_intensity, min_carbon, max_carbon)

            # Higher renewable is better
            s_renewable = self.normalize(dc.renewable_pct, min_renewable, max_renewable)

            # Lower latency is better (invert normalization)
            latency = self.calculate_latency(dc)
            s_latency = 1 - self.normalize(latency, min_latency, max_latency)

            # Datacenter type penalty: Penalize brown datacenters
            # Brown (DB) datacenters have higher carbon, so we reduce their score
            dc_type_multiplier = 0.7 if dc.dc_type == 'DB' else 1.0  # 30% penalty for brown

            # Weighted score (with brown datacenter penalty)
            base_score = (self.w_carbon * s_carbon +
                         self.w_renewable * s_renewable +
                         self.w_latency * s_latency)
            score = base_score * dc_type_multiplier

            scores[dc_id] = {
                'score': score,
                'carbon_intensity': dc.carbon_intensity,
                'renewable_pct': dc.renewable_pct,
                'dc_type': dc.dc_type,
                'latency_ms': latency,
                's_carbon': s_carbon,
                's_renewable': s_renewable,
                's_latency': s_latency,
                'dc_type_multiplier': dc_type_multiplier
            }

        # Select datacenter with highest score
        best_dc = max(scores.items(), key=lambda x: x[1]['score'])

        return best_dc[0]


class ECMRHeterogeneousIntegration:
    """
    Complete ECMR + Heterogeneous CloudSim Integration
    """

    def __init__(self, csv_path: str):
        print("="*80)
        print("ECMR + HETEROGENEOUS CLOUDSIM INTEGRATION")
        print("="*80)
        print()

        # Load carbon intensity data
        print("[1/6] Loading carbon intensity data...")
        self.df = pd.read_csv(csv_path)
        print(f"      Loaded {len(self.df)} hourly records")
        print()

        # Connect to Java gateway
        print("[2/6] Connecting to Java gateway...")
        self.gateway = JavaGateway()
        self.app = self.gateway.entry_point
        print("      ✓ Connected to Py4JGatewayEnhanced")
        print()

        # Initialize simulation
        print("[3/6] Initializing CloudSim simulation...")
        self.app.initializeSimulation()
        print("      ✓ CloudSim initialized")
        print()

        # Create datacenters
        self.datacenters = {}
        self.create_heterogeneous_datacenters()

        # Initialize ECMR scheduler
        self.scheduler = ECMRHeterogeneousScheduler(self.datacenters)

        # Results tracking
        self.placement_decisions = []
        self.hourly_stats = []

    def create_heterogeneous_datacenters(self):
        """Create 5 datacenters with heterogeneous servers"""
        print("[4/6] Creating heterogeneous datacenters...")
        print("      Each datacenter: 40 servers of each type (120 total)")
        print("      - 40 × Huawei RH2285 V2 (16 cores, 24GB, 2.3GHz)")
        print("      - 40 × Huawei RH2288H V3 (40 cores, 64GB, 3.6GHz)")
        print("      - 40 × Lenovo SR655 V3 (96 cores, 192GB, 2.4GHz)")
        print()

        for dc_id, config in DATACENTERS.items():
            # Create heterogeneous datacenter in CloudSim
            self.app.createHeterogeneousDatacenter(dc_id, 40, config['pue'])

            # Create Python state tracker
            self.datacenters[dc_id] = DatacenterState(
                id=dc_id,
                name=config['name'],
                country=config['country'],
                latitude=config['lat'],
                longitude=config['lon'],
                pue=config['pue']
            )

            print(f"      ✓ {dc_id}: {config['name']} (PUE {config['pue']})")

        print()

    def update_datacenter_state(self, hour_data: pd.Series):
        """Update datacenter states with current carbon intensity data"""
        for dc_id, dc in self.datacenters.items():
            country = dc.country

            # Update carbon intensity (CSV format: {country}_carbon_intensity)
            carbon_col = f'{country}_carbon_intensity'
            if carbon_col in hour_data:
                dc.carbon_intensity = hour_data[carbon_col]

            # Update renewable percentage (CSV format: {country}_renewable_pct)
            renewable_col = f'{country}_renewable_pct'
            if renewable_col in hour_data:
                dc.renewable_pct = hour_data[renewable_col]

            # Update datacenter type (CSV format: {country}_datacenter_type)
            dc_type_col = f'{country}_datacenter_type'
            if dc_type_col in hour_data:
                dc.dc_type = hour_data[dc_type_col]

            # Update renewable energy breakdown (CSV format: {country}_{type})
            hydro_col = f'{country}_hydro'
            solar_col = f'{country}_solar'
            wind_col = f'{country}_wind'

            if hydro_col in hour_data:
                dc.hydro_mw = hour_data[hydro_col]
            if solar_col in hour_data:
                dc.solar_mw = hour_data[solar_col]
            if wind_col in hour_data:
                dc.wind_mw = hour_data[wind_col]

    def generate_vm(self, vm_id: int) -> Dict:
        """Generate a VM with random type"""
        vm_type = np.random.choice(VM_TYPES, p=VM_TYPE_WEIGHTS)
        return {'vm_id': vm_id, 'type': vm_type}

    def run_simulation(self, hours: int = 24, vms_per_hour: int = 10):
        """
        Run ECMR simulation for specified hours with random user locations

        Args:
            hours: Number of hours to simulate
            vms_per_hour: VMs to place each hour
        """
        print(f"[5/6] Running simulation ({hours} hours, {vms_per_hour} VMs/hour)...")
        print(f"      Using random user locations across {len(EUROPEAN_CITIES)} European cities")
        print()

        vm_id = 0
        hour_carbon_totals = []

        for hour in range(min(hours, len(self.df))):
            hour_data = self.df.iloc[hour]
            timestamp = hour_data.get('timestamp', f'Hour {hour}')

            print(f"  Hour {hour + 1}/{hours} ({timestamp})")

            # Update datacenter states with current carbon data
            self.update_datacenter_state(hour_data)

            # Display carbon intensities
            carbon_summary = {dc_id: f"{dc.carbon_intensity:.0f}"
                            for dc_id, dc in self.datacenters.items()}
            print(f"    Carbon (gCO2/kWh): {carbon_summary}")

            # Display renewable percentages
            renewable_summary = {dc_id: f"{dc.renewable_pct:.1f}%"
                               for dc_id, dc in self.datacenters.items()}
            print(f"    Renewable: {renewable_summary}")

            # Generate and place VMs with random user locations
            placements = {}
            user_locations_used = []

            for i in range(vms_per_hour):
                vm = self.generate_vm(vm_id)

                # Randomly select user location for this VM
                city_name, user_lat, user_lon = EUROPEAN_CITIES[vm_id % len(EUROPEAN_CITIES)]
                user_locations_used.append(city_name)

                # Update scheduler with new user location
                self.scheduler.user_location = (user_lat, user_lon)

                # ECMR algorithm selects datacenter based on this user's location
                selected_dc = self.scheduler.select_datacenter(vm)

                # Submit VM to CloudSim
                success = self.app.submitVMByType(vm_id, vm['type'], selected_dc)

                if success:
                    self.datacenters[selected_dc].vms_placed += 1
                    placements[selected_dc] = placements.get(selected_dc, 0) + 1

                    self.placement_decisions.append({
                        'hour': hour,
                        'vm_id': vm_id,
                        'vm_type': vm['type'],
                        'datacenter': selected_dc,
                        'user_city': city_name,
                        'user_lat': user_lat,
                        'user_lon': user_lon,
                        'carbon_intensity': self.datacenters[selected_dc].carbon_intensity,
                        'renewable_pct': self.datacenters[selected_dc].renewable_pct,
                        'dc_type': self.datacenters[selected_dc].dc_type,
                        'timestamp': timestamp
                    })

                vm_id += 1

            # Show placement distribution
            placement_str = ", ".join([f"{dc}: {count}" for dc, count in placements.items()])
            print(f"    Placements: {placement_str}")

            # Show unique user cities this hour
            unique_cities = set(user_locations_used)
            print(f"    User cities: {', '.join(list(unique_cities)[:5])}{' ...' if len(unique_cities) > 5 else ''}")

            # Calculate hour carbon total
            hour_carbon = sum(dc.carbon_intensity * (dc.vms_placed / vm_id)
                            for dc in self.datacenters.values())
            hour_carbon_totals.append(hour_carbon)
            print()

        print(f"  ✓ Placed {vm_id} VMs across {hours} hours")
        print(f"  ✓ Used {len(set([d['user_city'] for d in self.placement_decisions]))} unique user locations")
        print()

        # Run CloudSim simulation
        print("[6/6] Running CloudSim simulation...")
        start_time = time.time()
        self.app.runSimulation()
        duration = time.time() - start_time
        print(f"      ✓ Simulation completed in {duration:.2f}s")
        print()

    def print_results(self):
        """Print comprehensive results with enhanced metrics"""
        print("="*80)
        print("SIMULATION RESULTS")
        print("="*80)
        print()

        # Get CloudSim results
        results = self.app.getResults()
        placements_df = pd.DataFrame(self.placement_decisions)

        # === SECTION 1: Overall Statistics ===
        print("📊 OVERALL STATISTICS")
        print("-" * 80)
        print(f"  Total IT Energy: {results.get('totalITEnergyKWh') or 0:.4f} kWh")
        print(f"  Total Facility Energy (PUE-adjusted): {results.get('totalEnergyKWh') or 0:.4f} kWh")
        print(f"  Average PUE: {results.get('averagePUE') or 0:.2f}")
        print(f"  Total VMs Requested: {results.get('totalVMs') or 0}")
        print(f"  Successful VMs: {results.get('successfulVMs') or 0}")
        print(f"  Failed VMs: {results.get('failedVMs') or 0}")
        success_rate = (results.get('successfulVMs') or 0) / max(results.get('totalVMs') or 1, 1) * 100
        print(f"  Success Rate: {success_rate:.1f}%")
        print()

        # === SECTION 2: Carbon Metrics ===
        print("🌍 CARBON & RENEWABLE METRICS")
        print("-" * 80)

        total_carbon = 0
        weighted_carbon_avg = 0
        weighted_renewable_avg = 0
        total_vms = len(placements_df) if not placements_df.empty else 1

        dc_carbon_details = []
        for dc_id, dc in self.datacenters.items():
            stats = self.app.getDatacenterStats(dc_id)
            dc_energy = stats.get('totalEnergyKWh') or 0
            dc_carbon = dc_energy * (dc.carbon_intensity / 1000)  # gCO2/kWh to kgCO2
            total_carbon += dc_carbon

            # Weight by VMs placed
            weighted_carbon_avg += dc.carbon_intensity * (dc.vms_placed / total_vms)
            weighted_renewable_avg += dc.renewable_pct * (dc.vms_placed / total_vms)

            dc_carbon_details.append((dc_id, dc, dc_energy, dc_carbon, stats))

        print(f"  Total Carbon Emissions: {total_carbon:.4f} kg CO2")
        print(f"  Weighted Avg Carbon Intensity: {weighted_carbon_avg:.1f} gCO2/kWh")
        print(f"  Weighted Avg Renewable %: {weighted_renewable_avg:.1f}%")

        if not placements_df.empty:
            avg_vm_carbon = placements_df['carbon_intensity'].mean()
            min_vm_carbon = placements_df['carbon_intensity'].min()
            max_vm_carbon = placements_df['carbon_intensity'].max()
            print(f"  VM Carbon Intensity: avg={avg_vm_carbon:.1f}, min={min_vm_carbon:.1f}, max={max_vm_carbon:.1f} gCO2/kWh")
        print()

        # === SECTION 2.5: Green Datacenter Utilization (M5) ===
        print("🌱 M5: GREEN DATACENTER UTILIZATION")
        print("-" * 80)

        if not placements_df.empty and 'dc_type' in placements_df.columns:
            green_dc_placements = sum(1 for _, row in placements_df.iterrows() if row['dc_type'] == 'DG')
            brown_dc_placements = sum(1 for _, row in placements_df.iterrows() if row['dc_type'] == 'DB')
            total_placements = len(placements_df)

            green_utilization_pct = (green_dc_placements / total_placements * 100) if total_placements > 0 else 0
            brown_utilization_pct = (brown_dc_placements / total_placements * 100) if total_placements > 0 else 0

            print(f"  Green Datacenter (DG) VMs: {green_dc_placements} ({green_utilization_pct:.2f}%)")
            print(f"  Brown Datacenter (DB) VMs: {brown_dc_placements} ({brown_utilization_pct:.2f}%)")
            print(f"  ➜ Green DC Utilization Score: {green_utilization_pct/100:.3f}/1.000")

            # Visual bar representation
            green_bar = '█' * int(green_utilization_pct / 2)
            brown_bar = '█' * int(brown_utilization_pct / 2)
            print(f"  Green: {green_bar}")
            print(f"  Brown: {brown_bar}")
        else:
            print("  [DC type data not available in placement decisions]")
        print()

        # === SECTION 3: Per-Datacenter Details ===
        print("🏢 PER-DATACENTER STATISTICS")
        print("-" * 80)

        for dc_id, dc, dc_energy, dc_carbon, stats in dc_carbon_details:
            placement_pct = (dc.vms_placed / total_vms) * 100 if total_vms > 0 else 0

            print(f"  {dc_id} ({dc.name}):")
            print(f"    VMs: {dc.vms_placed} ({placement_pct:.1f}% of total)")
            print(f"    IT Energy: {stats.get('itEnergyKWh') or 0:.4f} kWh | "
                  f"Total (PUE {dc.pue}): {dc_energy:.4f} kWh")
            print(f"    Carbon: {dc.carbon_intensity:.0f} gCO2/kWh | "
                  f"Emissions: {dc_carbon:.4f} kg CO2")
            print(f"    Renewable: {dc.renewable_pct:.1f}% "
                  f"(Hydro: {dc.hydro_mw:.1f} MW, Solar: {dc.solar_mw:.1f} MW, Wind: {dc.wind_mw:.1f} MW)")
            print(f"    Utilization: CPU {stats.get('cpuUtilization') or 0:.1%}, "
                  f"RAM {stats.get('ramUtilization') or 0:.1%}")
            print(f"    Server Mix: RH2285: {stats.get('huaweiRH2285Count') or 0}, "
                  f"RH2288: {stats.get('huaweiRH2288Count') or 0}, "
                  f"SR655: {stats.get('lenovoSR655Count') or 0}")
            print()

        # === SECTION 4: VM Distribution ===
        print("📦 VM TYPE DISTRIBUTION")
        print("-" * 80)
        if not placements_df.empty:
            type_counts = placements_df['vm_type'].value_counts()
            for vm_type in ['small', 'medium', 'large', 'xlarge']:
                count = type_counts.get(vm_type, 0)
                pct = (count / len(placements_df)) * 100
                bar = '█' * int(pct / 2)
                print(f"  {vm_type:8s}: {count:4d} ({pct:5.1f}%) {bar}")
        print()

        # === SECTION 5: Datacenter Selection ===
        print("🎯 DATACENTER SELECTION DISTRIBUTION")
        print("-" * 80)
        if not placements_df.empty:
            dc_counts = placements_df['datacenter'].value_counts()
            for dc_id in self.datacenters.keys():
                count = dc_counts.get(dc_id, 0)
                pct = (count / len(placements_df)) * 100
                bar = '█' * int(pct / 2)
                print(f"  {dc_id:15s}: {count:4d} ({pct:5.1f}%) {bar}")
        print()

        # === SECTION 6: User Location Analysis ===
        print("🌐 USER LOCATION ANALYSIS")
        print("-" * 80)
        if not placements_df.empty and 'user_city' in placements_df.columns:
            unique_cities = placements_df['user_city'].nunique()
            top_cities = placements_df['user_city'].value_counts().head(5)
            print(f"  Unique User Cities: {unique_cities}")
            print(f"  Top 5 Cities:")
            for city, count in top_cities.items():
                pct = (count / len(placements_df)) * 100
                print(f"    {city}: {count} VMs ({pct:.1f}%)")
        print()

        # === SECTION 7: Time-based Analysis ===
        print("⏰ HOURLY ANALYSIS")
        print("-" * 80)
        if not placements_df.empty:
            hourly_carbon = placements_df.groupby('hour')['carbon_intensity'].mean()
            hourly_renewable = placements_df.groupby('hour')['renewable_pct'].mean()

            print(f"  Hours Simulated: {len(hourly_carbon)}")
            print(f"  Avg Carbon per Hour: {hourly_carbon.mean():.1f} gCO2/kWh")
            print(f"  Avg Renewable per Hour: {hourly_renewable.mean():.1f}%")
            print(f"  Best Hour (lowest carbon): Hour {hourly_carbon.idxmin() + 1} ({hourly_carbon.min():.1f} gCO2/kWh)")
            print(f"  Worst Hour (highest carbon): Hour {hourly_carbon.idxmax() + 1} ({hourly_carbon.max():.1f} gCO2/kWh)")
        print()

        # === SECTION 8: ECMR Algorithm Effectiveness ===
        print("🎯 ECMR ALGORITHM EFFECTIVENESS")
        print("-" * 80)
        if not placements_df.empty:
            # Compare actual placement vs random/worst-case
            actual_carbon = placements_df['carbon_intensity'].mean()

            # Random baseline: equal distribution across all DCs
            all_carbon_values = [dc.carbon_intensity for dc in self.datacenters.values()]
            random_carbon = sum(all_carbon_values) / len(all_carbon_values)

            # Worst case: always highest carbon
            worst_carbon = max(all_carbon_values)

            carbon_saved_vs_random = random_carbon - actual_carbon
            carbon_saved_vs_worst = worst_carbon - actual_carbon

            improvement_vs_random = (carbon_saved_vs_random / random_carbon * 100) if random_carbon > 0 else 0
            improvement_vs_worst = (carbon_saved_vs_worst / worst_carbon * 100) if worst_carbon > 0 else 0

            print(f"  Actual Avg Carbon: {actual_carbon:.1f} gCO2/kWh")
            print(f"  Random Placement: {random_carbon:.1f} gCO2/kWh")
            print(f"  Worst Case: {worst_carbon:.1f} gCO2/kWh")
            print(f"  Improvement vs Random: {improvement_vs_random:.1f}% ({carbon_saved_vs_random:.1f} gCO2/kWh saved)")
            print(f"  Improvement vs Worst: {improvement_vs_worst:.1f}% ({carbon_saved_vs_worst:.1f} gCO2/kWh saved)")
        print()

        print("="*80)
        print("✓ SIMULATION COMPLETED SUCCESSFULLY")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description='ECMR + Heterogeneous CloudSim Integration')
    parser.add_argument('--data', type=str,
                       default='output/synchronized_dataset_2024.csv',
                       help='Path to synchronized dataset CSV')
    parser.add_argument('--hours', type=int, default=24,
                       help='Number of hours to simulate')
    parser.add_argument('--vms-per-hour', type=int, default=10,
                       help='VMs to place per hour')

    args = parser.parse_args()

    try:
        # Create and run integration
        integration = ECMRHeterogeneousIntegration(args.data)
        integration.run_simulation(hours=args.hours, vms_per_hour=args.vms_per_hour)
        integration.print_results()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\nShutting down gateway...")


if __name__ == "__main__":
    main()
