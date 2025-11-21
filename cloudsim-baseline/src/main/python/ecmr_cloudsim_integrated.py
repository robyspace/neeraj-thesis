#!/usr/bin/env python3
"""
ECMR Baseline with CloudSimPlus Integration
Connects Python ECMR algorithm to Java CloudSimPlus via Py4J

Usage:
1. Start Java Gateway: java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar com.ecmr.baseline.Py4JGateway
2. Run this script: python3 ecmr_cloudsim_integrated.py
"""

import pandas as pd
import numpy as np
from py4j.java_gateway import JavaGateway, GatewayParameters
import json
import time
import argparse
from datetime import datetime


class ECMRCloudSimIntegration:
    """Integration between ECMR Python logic and CloudSimPlus Java simulation"""
    
    def __init__(self, gateway_address='localhost', gateway_port=25333):
        """
        Initialize connection to Java Gateway
        
        Parameters:
        - gateway_address: Java Gateway server address
        - gateway_port: Java Gateway server port (default: 25333)
        """
        print("="*80)
        print("ECMR-CloudSim Integration via Py4J")
        print("="*80)
        print()
        
        print(f"[1/4] Connecting to Java Gateway at {gateway_address}:{gateway_port}...")

        try:
            # Use simple connection without GatewayParameters for better compatibility
            import time
            time.sleep(1)  # Brief wait for gateway to be ready
            self.gateway = JavaGateway()

            # Get the entry point
            self.java_gateway = self.gateway.entry_point

            print("      Connected to Java Gateway successfully")
            print()
        except Exception as e:
            print(f"      Failed to connect: {e}")
            print()
            print("Make sure Java Gateway is running:")
            print("  java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \\")
            print("       com.ecmr.baseline.Py4JGateway")
            print()
            raise
    
    def initialize_simulation(self, config=None):
        """Initialize CloudSim simulation"""
        print("[2/4] Initializing CloudSim simulation...")
        
        if config is None:
            config = {}
        
        # Convert Python dict to Java Map
        java_config = self.gateway.jvm.java.util.HashMap()
        for key, value in config.items():
            java_config[key] = value
        
        self.java_gateway.initializeSimulation(java_config)
        print("      CloudSim initialized")
        print()
    
    def create_datacenters(self, datacenter_configs):
        """
        Create datacenters in CloudSim
        
        Parameters:
        - datacenter_configs: List of datacenter configurations
        """
        print("[3/4] Creating datacenters...")
        
        for dc_config in datacenter_configs:
            dc_id = self.java_gateway.createDatacenter(
                dc_config['id'],
                dc_config['num_servers'],
                dc_config['cpu_per_server'],
                dc_config['ram_per_server_mb'],
                dc_config['power_idle_w'],
                dc_config['power_max_w']
            )
            print(f"      Created datacenter: {dc_id}")
        
        print()
    
    def run_ecmr_scheduling(self, synchronized_data_path, max_vms=100):
        """
        Run ECMR scheduling algorithm with CloudSim
        
        Parameters:
        - synchronized_data_path: Path to synchronized dataset CSV
        - max_vms: Maximum number of VMs to schedule
        """
        print("[4/4] Running ECMR scheduling...")
        print()
        
        # Load synchronized data
        df = pd.read_csv(synchronized_data_path)
        print(f"  Loaded {len(df)} hours of data")
        print(f"  Total VMs in dataset: {df['vm_arrivals'].sum()}")
        print()
        
        # Submit VMs to CloudSim
        print("  Submitting VMs to CloudSim...")
        vm_count = 0
        
        for idx, row in df.iterrows():
            if vm_count >= max_vms:
                break
            
            # Generate VMs for this hour
            num_vms = int(row['vm_arrivals'])
            
            for i in range(num_vms):
                if vm_count >= max_vms:
                    break
                
                # Generate VM specifications
                vm_id = vm_count
                cpus = np.random.randint(1, 8)
                ram_mb = np.random.randint(2, 16) * 1024
                mips = cpus * 1000
                
                # Submit to CloudSim
                success = self.java_gateway.submitVM(vm_id, cpus, ram_mb, mips)
                
                if success:
                    vm_count += 1
                    
                    if vm_count % 10 == 0:
                        print(f"    Submitted {vm_count} VMs...")
        
        print(f"  Submitted {vm_count} VMs to CloudSim")
        print()
        
        # Run simulation
        print("  Running CloudSim simulation...")
        start_time = time.time()
        self.java_gateway.runSimulation()
        end_time = time.time()
        
        print(f"  Simulation completed in {end_time - start_time:.2f} seconds")
        print()
        
        return vm_count
    
    def get_results(self):
        """Get simulation results from CloudSim"""
        print("="*80)
        print("SIMULATION RESULTS")
        print("="*80)
        print()
        
        # Get overall results
        results = self.java_gateway.getResults()
        
        # Convert Java Map to Python dict
        results_dict = {
            'totalEnergy': results.get('totalEnergy'),
            'successfulVMs': results.get('successfulVMs'),
            'failedVMs': results.get('failedVMs'),
            'avgExecutionTime': results.get('avgExecutionTime'),
            'totalVMs': results.get('totalVMs'),
            'failureRate': results.get('failureRate')
        }
        
        print(f"Total VMs:          {results_dict['totalVMs']}")
        print(f"Successful VMs:     {results_dict['successfulVMs']}")
        print(f"Failed VMs:         {results_dict['failedVMs']}")
        print(f"Failure Rate:       {results_dict['failureRate']:.2f}%")
        print(f"Total Energy:       {results_dict['totalEnergy'] / 3600000:.2f} kWh")
        print(f"Avg Execution Time: {results_dict['avgExecutionTime']:.2f} seconds")
        print()
        
        # Get placement decisions
        placements = self.java_gateway.getPlacementDecisions()
        
        print(f"Retrieved {len(placements)} placement decisions")
        print("="*80)
        
        return results_dict, placements
    
    def save_results(self, results, placements, output_path='ecmr_cloudsim_results.json'):
        """Save results to JSON file"""
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'metrics': results,
            'placement_decisions': [dict(p) for p in placements]
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='ECMR-CloudSim Integration')
    parser.add_argument('--data', required=True,
                        help='Synchronized dataset CSV file')
    parser.add_argument('--max-vms', type=int, default=100,
                        help='Maximum VMs to simulate (default: 100)')
    parser.add_argument('--output', default='ecmr_cloudsim_results.json',
                        help='Output JSON file')
    parser.add_argument('--gateway-host', default='localhost',
                        help='Java Gateway host (default: localhost)')
    parser.add_argument('--gateway-port', type=int, default=25333,
                        help='Java Gateway port (default: 25333)')
    
    args = parser.parse_args()
    
    try:
        # Create integration instance
        integration = ECMRCloudSimIntegration(
            gateway_address=args.gateway_host,
            gateway_port=args.gateway_port
        )
        
        # Initialize simulation
        integration.initialize_simulation()
        
        # Create datacenters (5 European DCs)
        datacenters = [
            {
                'id': 'DC_IT',
                'num_servers': 100,
                'cpu_per_server': 32,
                'ram_per_server_mb': 256 * 1024,
                'power_idle_w': 200.0,
                'power_max_w': 400.0
            },
            {
                'id': 'DC_SE',
                'num_servers': 100,
                'cpu_per_server': 32,
                'ram_per_server_mb': 256 * 1024,
                'power_idle_w': 200.0,
                'power_max_w': 400.0
            },
            {
                'id': 'DC_ES',
                'num_servers': 100,
                'cpu_per_server': 32,
                'ram_per_server_mb': 256 * 1024,
                'power_idle_w': 200.0,
                'power_max_w': 400.0
            },
            {
                'id': 'DC_FR',
                'num_servers': 100,
                'cpu_per_server': 32,
                'ram_per_server_mb': 256 * 1024,
                'power_idle_w': 200.0,
                'power_max_w': 400.0
            },
            {
                'id': 'DC_DE',
                'num_servers': 100,
                'cpu_per_server': 32,
                'ram_per_server_mb': 256 * 1024,
                'power_idle_w': 200.0,
                'power_max_w': 400.0
            }
        ]
        
        integration.create_datacenters(datacenters)
        
        # Run ECMR scheduling
        vm_count = integration.run_ecmr_scheduling(args.data, args.max_vms)
        
        # Get results
        results, placements = integration.get_results()
        
        # Save results
        integration.save_results(results, placements, args.output)
        
        print("\n ECMR-CloudSim integration completed successfully!")
        
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

