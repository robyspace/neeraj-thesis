#!/usr/bin/env python3
"""
Unified Metrics Module for ECMR vs C-MORL Comparison
Defines the 4 research metrics in a standardized format
"""

import json
from typing import Dict, Any
from pathlib import Path


class UnifiedMetrics:
    """
    Standardized metrics for both ECMR and C-MORL:
    M1: Resource Utilization Efficiency
    M2: Throughput
    M3: Response Time
    M4: Carbon Intensity Reduction
    M5: Green Datacenter Utilization
    """

    def __init__(self, algorithm_name: str):
        self.algorithm = algorithm_name
        self.metrics = {
            'M1_resource_utilization': {},
            'M2_throughput': {},
            'M3_response_time': {},
            'M4_carbon_reduction': {},
            'M5_green_dc_utilization': {}
        }
        self.raw_data = {}

    def compute_m1_resource_utilization(self, total_energy_kwh: float,
                                         total_vms: int,
                                         avg_cpu_util: float = None,
                                         avg_ram_util: float = None):
        """
        M1: Resource Utilization Efficiency
        - Energy per VM (lower is better)
        - CPU/RAM utilization (higher is better, indicates efficient packing)
        """
        energy_per_vm = total_energy_kwh / max(total_vms, 1)

        self.metrics['M1_resource_utilization'] = {
            'total_energy_kwh': total_energy_kwh,
            'total_vms': total_vms,
            'energy_per_vm_kwh': energy_per_vm,
            'avg_cpu_utilization_pct': avg_cpu_util or 0.0,
            'avg_ram_utilization_pct': avg_ram_util or 0.0,
            'efficiency_score': (avg_cpu_util or 50.0) / 100.0  # Normalized 0-1
        }

    def compute_m2_throughput(self, successful_vms: int,
                               failed_vms: int,
                               total_time_seconds: float):
        """
        M2: Throughput
        - Success rate (%)
        - VMs placed per second
        """
        total_vms = successful_vms + failed_vms
        success_rate = (successful_vms / max(total_vms, 1)) * 100
        vms_per_second = successful_vms / max(total_time_seconds, 1)

        self.metrics['M2_throughput'] = {
            'successful_vms': successful_vms,
            'failed_vms': failed_vms,
            'total_vms': total_vms,
            'success_rate_pct': success_rate,
            'vms_per_second': vms_per_second,
            'throughput_score': success_rate / 100.0  # Normalized 0-1
        }

    def compute_m3_response_time(self, avg_latency_ms: float = None,
                                  avg_vm_creation_time_s: float = None,
                                  total_simulation_time_s: float = None):
        """
        M3: Response Time
        - Average network latency (ms)
        - VM creation time (s)
        - Total simulation time (s)
        """
        self.metrics['M3_response_time'] = {
            'avg_network_latency_ms': avg_latency_ms or 0.0,
            'avg_vm_creation_time_s': avg_vm_creation_time_s or 0.0,
            'total_simulation_time_s': total_simulation_time_s or 0.0,
            'response_score': 1.0 / max(avg_latency_ms or 10.0, 1.0)  # Inverse for score (lower latency = better)
        }

    def compute_m4_carbon_reduction(self, total_carbon_gco2: float,
                                      baseline_carbon_gco2: float = None,
                                      avg_carbon_intensity: float = None,
                                      avg_renewable_pct: float = None):
        """
        M4: Carbon Intensity Reduction
        - Total carbon emissions (gCO2)
        - Reduction vs baseline (%)
        - Average carbon intensity (gCO2/kWh)
        - Renewable energy percentage (%)
        """
        reduction_pct = 0.0
        if baseline_carbon_gco2 and baseline_carbon_gco2 > 0:
            reduction_pct = ((baseline_carbon_gco2 - total_carbon_gco2) / baseline_carbon_gco2) * 100

        self.metrics['M4_carbon_reduction'] = {
            'total_carbon_emissions_gco2': total_carbon_gco2,
            'baseline_carbon_gco2': baseline_carbon_gco2 or 0.0,
            'reduction_vs_baseline_pct': reduction_pct,
            'avg_carbon_intensity_gco2_per_kwh': avg_carbon_intensity or 0.0,
            'avg_renewable_pct': avg_renewable_pct or 0.0,
            'carbon_score': 1.0 - (total_carbon_gco2 / max(baseline_carbon_gco2 or total_carbon_gco2, 1))  # Normalized 0-1
        }

    def compute_m5_green_dc_utilization(self, green_dc_vms: int,
                                         brown_dc_vms: int):
        """
        M5: Green Datacenter Utilization
        - Number of VMs placed in green DCs (DG)
        - Number of VMs placed in brown DCs (DB)
        - Percentage of VMs in green DCs (higher is better)
        """
        total_vms = green_dc_vms + brown_dc_vms
        green_utilization_pct = (green_dc_vms / max(total_vms, 1)) * 100
        brown_utilization_pct = (brown_dc_vms / max(total_vms, 1)) * 100

        self.metrics['M5_green_dc_utilization'] = {
            'green_dc_vms': green_dc_vms,
            'brown_dc_vms': brown_dc_vms,
            'total_vms': total_vms,
            'green_utilization_pct': green_utilization_pct,
            'brown_utilization_pct': brown_utilization_pct,
            'green_dc_score': green_utilization_pct / 100.0  # Normalized 0-1
        }

    def save_to_json(self, filepath: str):
        """Save metrics to JSON file"""
        output = {
            'algorithm': self.algorithm,
            'metrics': self.metrics,
            'raw_data': self.raw_data
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

    def print_summary(self, title: str = None):
        """Print formatted metrics summary"""
        if title:
            print("\n" + "="*80)
            print(f"{title}")
            print("="*80)

        print(f"\nAlgorithm: {self.algorithm}")
        print("="*80)

        # M1: Resource Utilization Efficiency
        m1 = self.metrics['M1_resource_utilization']
        print("\n📊 M1: RESOURCE UTILIZATION EFFICIENCY")
        print("-" * 80)
        print(f"  Total Energy:          {m1.get('total_energy_kwh', 0):.4f} kWh")
        print(f"  Total VMs:             {m1.get('total_vms', 0)}")
        print(f"  Energy per VM:         {m1.get('energy_per_vm_kwh', 0):.4f} kWh/VM")
        print(f"  Avg CPU Utilization:   {m1.get('avg_cpu_utilization_pct', 0):.2f}%")
        print(f"  Avg RAM Utilization:   {m1.get('avg_ram_utilization_pct', 0):.2f}%")
        print(f"  ➜ Efficiency Score:    {m1.get('efficiency_score', 0):.3f}/1.000")

        # M2: Throughput
        m2 = self.metrics['M2_throughput']
        print("\n⚡ M2: THROUGHPUT")
        print("-" * 80)
        print(f"  Successful VMs:        {m2.get('successful_vms', 0)}")
        print(f"  Failed VMs:            {m2.get('failed_vms', 0)}")
        print(f"  Success Rate:          {m2.get('success_rate_pct', 0):.2f}%")
        print(f"  VMs per Second:        {m2.get('vms_per_second', 0):.4f}")
        print(f"  ➜ Throughput Score:    {m2.get('throughput_score', 0):.3f}/1.000")

        # M3: Response Time
        m3 = self.metrics['M3_response_time']
        print("\n⏱️  M3: RESPONSE TIME")
        print("-" * 80)
        print(f"  Avg Network Latency:   {m3.get('avg_network_latency_ms', 0):.4f} ms")
        print(f"  Avg VM Creation Time:  {m3.get('avg_vm_creation_time_s', 0):.4f} s")
        print(f"  Total Simulation Time: {m3.get('total_simulation_time_s', 0):.2f} s")
        print(f"  ➜ Response Score:      {m3.get('response_score', 0):.3f}/1.000")

        # M4: Carbon Reduction
        m4 = self.metrics['M4_carbon_reduction']
        print("\n🌍 M4: CARBON INTENSITY REDUCTION")
        print("-" * 80)
        print(f"  Total Carbon Emissions: {m4.get('total_carbon_emissions_gco2', 0):.4f} gCO2")
        if m4.get('baseline_carbon_gco2', 0) > 0:
            print(f"  Baseline Carbon:        {m4.get('baseline_carbon_gco2', 0):.4f} gCO2")
            print(f"  Reduction vs Baseline:  {m4.get('reduction_vs_baseline_pct', 0):+.2f}%")
        print(f"  Avg Carbon Intensity:   {m4.get('avg_carbon_intensity_gco2_per_kwh', 0):.2f} gCO2/kWh")
        print(f"  Avg Renewable Energy:   {m4.get('avg_renewable_pct', 0):.2f}%")
        print(f"  ➜ Carbon Score:         {m4.get('carbon_score', 0):.3f}/1.000")

        # M5: Green DC Utilization
        m5 = self.metrics['M5_green_dc_utilization']
        if m5:  # Only print if M5 has been computed
            print("\n🌱 M5: GREEN DATACENTER UTILIZATION")
            print("-" * 80)
            print(f"  Green DC (DG) VMs:      {m5.get('green_dc_vms', 0)}")
            print(f"  Brown DC (DB) VMs:      {m5.get('brown_dc_vms', 0)}")
            print(f"  Total VMs:              {m5.get('total_vms', 0)}")
            print(f"  Green Utilization:      {m5.get('green_utilization_pct', 0):.2f}%")
            print(f"  Brown Utilization:      {m5.get('brown_utilization_pct', 0):.2f}%")
            print(f"  ➜ Green DC Score:       {m5.get('green_dc_score', 0):.3f}/1.000")

        print("\n" + "="*80)


def compare_metrics(ecmr_metrics: UnifiedMetrics, cmorl_metrics: UnifiedMetrics):
    """Compare two UnifiedMetrics instances and print comparison"""
    print("\n" + "="*80)
    print("📊 METRICS COMPARISON: ECMR vs C-MORL")
    print("="*80)

    metrics_order = [
        ('M1_resource_utilization', 'M1: Resource Utilization Efficiency', 'energy_per_vm_kwh', 'Energy per VM (kWh)', 'lower'),
        ('M2_throughput', 'M2: Throughput', 'success_rate_pct', 'Success Rate (%)', 'higher'),
        ('M3_response_time', 'M3: Response Time', 'avg_network_latency_ms', 'Avg Latency (ms)', 'lower'),
        ('M4_carbon_reduction', 'M4: Carbon Intensity Reduction', 'total_carbon_emissions_gco2', 'Total Carbon (gCO2)', 'lower'),
        ('M5_green_dc_utilization', 'M5: Green DC Utilization', 'green_utilization_pct', 'Green DC Util (%)', 'higher')
    ]

    for metric_key, metric_name, value_key, value_name, better in metrics_order:
        ecmr_val = ecmr_metrics.metrics[metric_key].get(value_key, 0)
        cmorl_val = cmorl_metrics.metrics[metric_key].get(value_key, 0)

        if better == 'lower':
            improvement = ((ecmr_val - cmorl_val) / ecmr_val * 100) if ecmr_val > 0 else 0
            winner = "C-MORL" if cmorl_val < ecmr_val else "ECMR"
        else:
            improvement = ((cmorl_val - ecmr_val) / ecmr_val * 100) if ecmr_val > 0 else 0
            winner = "C-MORL" if cmorl_val > ecmr_val else "ECMR"

        print(f"\n{metric_name}")
        print("-" * 80)
        print(f"  {value_name:30s}  ECMR: {ecmr_val:12.4f}  |  C-MORL: {cmorl_val:12.4f}")
        print(f"  Improvement:                    {improvement:+.2f}%  ({winner} wins)")

    print("\n" + "="*80)
    print("OVERALL SCORES (normalized 0-1, higher is better)")
    print("="*80)

    for metric_key, metric_name, _, _, _ in metrics_order:
        score_key = metric_key.split('_')[1] + '_score'
        ecmr_score = ecmr_metrics.metrics[metric_key].get(score_key, 0)
        cmorl_score = cmorl_metrics.metrics[metric_key].get(score_key, 0)

        print(f"  {metric_name:40s}  ECMR: {ecmr_score:.3f}  |  C-MORL: {cmorl_score:.3f}")

    print("="*80)


if __name__ == "__main__":
    # Test the metrics module
    print("Testing Unified Metrics Module")

    # Test ECMR metrics
    ecmr = UnifiedMetrics("ECMR")
    ecmr.compute_m1_resource_utilization(10.5, 100, 65.3, 58.2)
    ecmr.compute_m2_throughput(98, 2, 120.0)
    ecmr.compute_m3_response_time(8.5, 0.5, 120.0)
    ecmr.compute_m4_carbon_reduction(450.5, None, 85.3, 45.2)
    ecmr.compute_m5_green_dc_utilization(75, 25)
    ecmr.print_summary("ECMR BASELINE TEST")

    # Test C-MORL metrics
    cmorl = UnifiedMetrics("C-MORL")
    cmorl.compute_m1_resource_utilization(8.2, 100, 72.1, 68.5)
    cmorl.compute_m2_throughput(100, 0, 150.0)
    cmorl.compute_m3_response_time(6.2, 0.3, 150.0)
    cmorl.compute_m4_carbon_reduction(320.8, 450.5, 65.2, 62.3)
    cmorl.compute_m5_green_dc_utilization(92, 8)
    cmorl.print_summary("C-MORL TEST")

    # Compare
    compare_metrics(ecmr, cmorl)
