#!/usr/bin/env python3
"""
Enhanced Comparison Runner: ECMR vs C-MORL
Uses enhanced parsers to extract complete metrics including M5
Ensures fair comparison with identical configurations
"""

import subprocess
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

from enhanced_ecmr_parser import parse_ecmr_results
from enhanced_cmorl_parser import parse_cmorl_results
from unified_metrics import UnifiedMetrics, compare_metrics


class EnhancedComparisonRunner:
    """Manages fair comparison between ECMR and C-MORL"""

    def __init__(self, output_dir: str = 'enhanced_comparison_results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.config = {}
        self.ecmr_metrics = None
        self.cmorl_metrics_list = []
        self.raw_ecmr_data = {}
        self.raw_cmorl_data = {}

    def run_ecmr(self, hours: int = 24, vms_per_hour: int = 10,
                 data_path: str = 'output/synchronized_dataset_2024.csv') -> Tuple[UnifiedMetrics, Dict]:
        """
        Run ECMR baseline with specified configuration

        Returns:
            (UnifiedMetrics, raw_data)
        """
        print("\n" + "="*80)
        print("RUNNING ECMR BASELINE")
        print("="*80)
        print(f"Configuration: {hours} hours × {vms_per_hour} VMs/hour = {hours * vms_per_hour} total VMs")
        print(f"Data: {data_path}")

        ecmr_output_dir = self.output_dir / 'ecmr'
        ecmr_output_dir.mkdir(exist_ok=True)

        cmd = [
            'python3', 'ecmr_heterogeneous_integration.py',
            '--data', data_path,
            '--hours', str(hours),
            '--vms-per-hour', str(vms_per_hour)
        ]

        print(f"\nCommand: {' '.join(cmd)}")
        print("Running...\n")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time

        # Save output
        output_file = ecmr_output_dir / 'output.txt'
        with open(output_file, 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)

        print(f"✓ ECMR completed in {duration:.1f}s")
        print(f"✓ Output saved to {output_file}")

        # Parse results using enhanced parser
        print("\nParsing ECMR results...")
        metrics, raw_data = parse_ecmr_results(result.stdout)
        raw_data['runtime_seconds'] = duration
        raw_data['config'] = {
            'hours': hours,
            'vms_per_hour': vms_per_hour,
            'total_vms': hours * vms_per_hour,
            'data_path': data_path
        }

        # Save metrics
        metrics.save_to_json(str(ecmr_output_dir / 'metrics.json'))

        # Save raw data
        with open(ecmr_output_dir / 'raw_data.json', 'w') as f:
            json.dump(raw_data, f, indent=2, default=str)

        print(f"✓ Metrics saved to {ecmr_output_dir}/")

        return metrics, raw_data

    def run_cmorl(self, hours: int = 24, vms_per_hour: int = 10,
                  n_policies: int = 3, timesteps: int = 10000,
                  n_extend: int = 2, seed: int = 42) -> Tuple[List[UnifiedMetrics], Dict]:
        """
        Run C-MORL training with specified configuration

        Returns:
            (List of UnifiedMetrics for each solution, raw_data)
        """
        print("\n" + "="*80)
        print("RUNNING C-MORL")
        print("="*80)
        print(f"Configuration: {hours} hours × {vms_per_hour} VMs/hour = {hours * vms_per_hour} total VMs")
        print(f"Training: {n_policies} policies × {timesteps} timesteps")
        print(f"Extension: {n_extend} sparse solutions")
        print(f"Seed: {seed}")

        cmorl_output_dir = self.output_dir / 'cmorl'
        cmorl_output_dir.mkdir(exist_ok=True)

        cmd = [
            'python3', 'train_cmorl.py',
            '--simulation-hours', str(hours),
            '--vms-per-hour', str(vms_per_hour),
            '--n-policies', str(n_policies),
            '--timesteps', str(timesteps),
            '--n-extend', str(n_extend),
            '--output-dir', str(cmorl_output_dir),
            '--seed', str(seed)
        ]

        print(f"\nCommand: {' '.join(cmd)}")
        print("Running (this may take a while)...\n")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time

        # Save output
        output_file = cmorl_output_dir / 'training_log.txt'
        with open(output_file, 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)

        print(f"\n✓ C-MORL completed in {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"✓ Output saved to {output_file}")

        # Parse results using enhanced parser
        print("\nParsing C-MORL results...")
        all_metrics, raw_data = parse_cmorl_results(
            str(cmorl_output_dir),
            str(output_file)
        )

        raw_data['runtime_seconds'] = duration
        raw_data['config'] = {
            'hours': hours,
            'vms_per_hour': vms_per_hour,
            'total_vms': hours * vms_per_hour,
            'n_policies': n_policies,
            'timesteps_per_policy': timesteps,
            'n_extend': n_extend,
            'seed': seed
        }

        # Save individual solution metrics
        for i, metrics in enumerate(all_metrics):
            metrics.save_to_json(str(cmorl_output_dir / f'solution_{i+1}_metrics.json'))

        # Save raw data
        with open(cmorl_output_dir / 'raw_data.json', 'w') as f:
            json.dump(raw_data, f, indent=2, default=str)

        print(f"✓ Metrics for {len(all_metrics)} solutions saved to {cmorl_output_dir}/")

        return all_metrics, raw_data

    def create_comparison_report(self, ecmr_metrics: UnifiedMetrics,
                                   cmorl_metrics_list: List[UnifiedMetrics],
                                   ecmr_data: Dict, cmorl_data: Dict):
        """Create comprehensive comparison report in Markdown"""

        report_file = self.output_dir / 'comparison_report.md'

        with open(report_file, 'w') as f:
            # Header
            f.write("# Enhanced Comparison Report: ECMR vs C-MORL\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            # Configuration
            f.write("## Configuration\n\n")
            ecmr_config = ecmr_data['config']
            cmorl_config = cmorl_data['config']

            f.write("### ECMR Baseline\n")
            f.write(f"- Simulation: {ecmr_config['hours']} hours × {ecmr_config['vms_per_hour']} VMs/hour\n")
            f.write(f"- Total VMs: {ecmr_config['total_vms']}\n")
            f.write(f"- Runtime: {ecmr_data['runtime_seconds']:.1f}s\n\n")

            f.write("### C-MORL\n")
            f.write(f"- Simulation: {cmorl_config['hours']} hours × {cmorl_config['vms_per_hour']} VMs/hour\n")
            f.write(f"- Total VMs: {cmorl_config['total_vms']}\n")
            f.write(f"- Training: {cmorl_config['n_policies']} policies × {cmorl_config['timesteps_per_policy']} timesteps\n")
            f.write(f"- Extensions: {cmorl_config['n_extend']} sparse solutions\n")
            f.write(f"- Runtime: {cmorl_data['runtime_seconds']:.1f}s ({cmorl_data['runtime_seconds']/60:.1f} min)\n")
            f.write(f"- Pareto Front Size: {cmorl_data['pareto_front_size']} solutions\n\n")

            f.write("---\n\n")

            # Metrics Comparison - All Solutions
            f.write("## C-MORL Pareto Front Solutions\n\n")
            f.write("All solutions discovered by C-MORL:\n\n")
            f.write("| # | Policy ID | Stage | Energy (kWh) | Carbon (gCO2) | Latency (ms) | Green DC % |\n")
            f.write("|---|-----------|-------|--------------|---------------|--------------|------------|\n")

            for i, metrics in enumerate(cmorl_metrics_list, 1):
                obj = metrics.raw_data.get('objectives', [0, 0, 0])
                policy_id = metrics.raw_data.get('policy_id', '-')
                stage = metrics.raw_data.get('stage', '-')
                m5 = metrics.metrics.get('M5_green_dc_utilization', {})
                green_pct = m5.get('green_utilization_pct', 0.0)

                f.write(f"| {i} | {policy_id} | {stage} | {obj[0]:.2f} | {obj[1]:.2f} | {obj[2]:.2f} | {green_pct:.1f}% |\n")

            f.write("\n---\n\n")

            # Best Solutions Comparison
            f.write("## Best Solutions Comparison\n\n")
            f.write("Comparing ECMR against the best C-MORL solution for each objective:\n\n")

            # Find best C-MORL solutions
            best_energy_idx = min(range(len(cmorl_metrics_list)),
                                   key=lambda i: cmorl_metrics_list[i].raw_data['objectives'][0])
            best_carbon_idx = min(range(len(cmorl_metrics_list)),
                                   key=lambda i: cmorl_metrics_list[i].raw_data['objectives'][1])
            best_latency_idx = min(range(len(cmorl_metrics_list)),
                                    key=lambda i: cmorl_metrics_list[i].raw_data['objectives'][2])

            comparisons = [
                ("Energy", cmorl_metrics_list[best_energy_idx]),
                ("Carbon", cmorl_metrics_list[best_carbon_idx]),
                ("Latency", cmorl_metrics_list[best_latency_idx])
            ]

            for objective_name, cmorl_best in comparisons:
                f.write(f"### Best {objective_name} Solution\n\n")
                policy_id = cmorl_best.raw_data.get('policy_id', '-')
                f.write(f"**C-MORL Solution:** #{cmorl_metrics_list.index(cmorl_best) + 1} (Policy {policy_id})\n\n")

                # Comparison table
                f.write("| Metric | ECMR | C-MORL | Improvement |\n")
                f.write("|--------|------|--------|-------------|\n")

                # M1: Energy per VM
                ecmr_energy = ecmr_metrics.metrics['M1_resource_utilization']['energy_per_vm_kwh']
                cmorl_energy = cmorl_best.metrics['M1_resource_utilization']['energy_per_vm_kwh']
                energy_imp = ((ecmr_energy - cmorl_energy) / ecmr_energy * 100) if ecmr_energy > 0 else 0
                f.write(f"| Energy per VM (kWh) | {ecmr_energy:.4f} | {cmorl_energy:.4f} | {energy_imp:+.1f}% |\n")

                # M4: Total Carbon
                ecmr_carbon = ecmr_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
                cmorl_carbon = cmorl_best.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
                carbon_imp = ((ecmr_carbon - cmorl_carbon) / ecmr_carbon * 100) if ecmr_carbon > 0 else 0
                f.write(f"| Total Carbon (gCO2) | {ecmr_carbon:.2f} | {cmorl_carbon:.2f} | {carbon_imp:+.1f}% |\n")

                # M3: Latency
                ecmr_latency = ecmr_metrics.metrics['M3_response_time']['avg_network_latency_ms']
                cmorl_latency = cmorl_best.metrics['M3_response_time']['avg_network_latency_ms']
                latency_imp = ((ecmr_latency - cmorl_latency) / ecmr_latency * 100) if ecmr_latency > 0 else 0
                f.write(f"| Avg Latency (ms) | {ecmr_latency:.2f} | {cmorl_latency:.2f} | {latency_imp:+.1f}% |\n")

                # M5: Green DC Utilization
                ecmr_green = ecmr_metrics.metrics['M5_green_dc_utilization'].get('green_utilization_pct', 0.0)
                cmorl_green = cmorl_best.metrics['M5_green_dc_utilization'].get('green_utilization_pct', 0.0)
                green_imp = cmorl_green - ecmr_green
                f.write(f"| Green DC Util (%) | {ecmr_green:.1f}% | {cmorl_green:.1f}% | {green_imp:+.1f}pp |\n")

                # M2: Success Rate
                ecmr_success = ecmr_metrics.metrics['M2_throughput']['success_rate_pct']
                cmorl_success = cmorl_best.metrics['M2_throughput']['success_rate_pct']
                f.write(f"| Success Rate (%) | {ecmr_success:.1f}% | {cmorl_success:.1f}% | - |\n")

                f.write("\n")

            f.write("---\n\n")

            # Detailed Metrics Comparison
            f.write("## Detailed Metrics: ECMR vs Best C-MORL (Energy-optimal)\n\n")

            best_overall = cmorl_metrics_list[best_energy_idx]

            metrics_details = [
                ('M1', 'Resource Utilization Efficiency', [
                    ('total_energy_kwh', 'Total Energy (kWh)', 'lower'),
                    ('energy_per_vm_kwh', 'Energy per VM (kWh)', 'lower'),
                    ('avg_cpu_utilization_pct', 'Avg CPU Util (%)', 'higher'),
                    ('avg_ram_utilization_pct', 'Avg RAM Util (%)', 'higher'),
                ]),
                ('M2', 'Throughput', [
                    ('success_rate_pct', 'Success Rate (%)', 'higher'),
                    ('vms_per_second', 'VMs per Second', 'higher'),
                ]),
                ('M3', 'Response Time', [
                    ('avg_network_latency_ms', 'Avg Latency (ms)', 'lower'),
                ]),
                ('M4', 'Carbon Intensity Reduction', [
                    ('total_carbon_emissions_gco2', 'Total Carbon (gCO2)', 'lower'),
                    ('avg_carbon_intensity_gco2_per_kwh', 'Avg Carbon Intensity (gCO2/kWh)', 'lower'),
                    ('avg_renewable_pct', 'Avg Renewable (%)', 'higher'),
                ]),
                ('M5', 'Green DC Utilization', [
                    ('green_utilization_pct', 'Green DC Util (%)', 'higher'),
                    ('brown_utilization_pct', 'Brown DC Util (%)', 'lower'),
                ]),
            ]

            for metric_code, metric_name, details in metrics_details:
                f.write(f"### {metric_code}: {metric_name}\n\n")
                f.write("| Metric | ECMR | C-MORL | Winner |\n")
                f.write("|--------|------|--------|--------|\n")

                metric_key = f"{metric_code}_{'_'.join(metric_name.lower().split()[:2])}"
                for value_key, value_name, better in details:
                    ecmr_val = ecmr_metrics.metrics.get(metric_key, {}).get(value_key, 0.0)
                    cmorl_val = best_overall.metrics.get(metric_key, {}).get(value_key, 0.0)

                    if better == 'lower':
                        winner = "C-MORL ✓" if cmorl_val < ecmr_val else "ECMR"
                    else:
                        winner = "C-MORL ✓" if cmorl_val > ecmr_val else "ECMR"

                    f.write(f"| {value_name} | {ecmr_val:.4f} | {cmorl_val:.4f} | {winner} |\n")

                f.write("\n")

            # Key Findings
            f.write("---\n\n")
            f.write("## Key Findings\n\n")
            f.write(f"1. **Pareto Front**: C-MORL discovered {cmorl_data['pareto_front_size']} non-dominated solutions\n")
            f.write(f"2. **Hypervolume**: {cmorl_data['hypervolume']:.2f}\n")
            f.write(f"3. **Trade-offs**: C-MORL provides multiple solutions with different objective trade-offs\n")
            f.write(f"4. **ECMR**: Single-objective greedy solution, fast execution\n\n")

            f.write("### Performance Improvements (Best C-MORL vs ECMR)\n\n")

            best = cmorl_metrics_list[best_energy_idx]
            improvements = []

            # Energy
            ecmr_e = ecmr_metrics.metrics['M1_resource_utilization']['total_energy_kwh']
            cmorl_e = best.metrics['M1_resource_utilization']['total_energy_kwh']
            if ecmr_e > 0:
                e_imp = ((ecmr_e - cmorl_e) / ecmr_e * 100)
                if e_imp > 0:
                    improvements.append(f"-  **Energy**: {e_imp:.1f}% reduction")
                elif e_imp < 0:
                    improvements.append(f"-  **Energy**: {abs(e_imp):.1f}% increase")

            # Carbon
            ecmr_c = ecmr_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
            cmorl_c = best.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
            if ecmr_c > 0:
                c_imp = ((ecmr_c - cmorl_c) / ecmr_c * 100)
                if c_imp > 0:
                    improvements.append(f"-  **Carbon**: {c_imp:.1f}% reduction")
                elif c_imp < 0:
                    improvements.append(f"-  **Carbon**: {abs(c_imp):.1f}% increase")

            # Green DC
            ecmr_g = ecmr_metrics.metrics['M5_green_dc_utilization'].get('green_utilization_pct', 0.0)
            cmorl_g = best.metrics['M5_green_dc_utilization'].get('green_utilization_pct', 0.0)
            g_diff = cmorl_g - ecmr_g
            if g_diff > 0:
                improvements.append(f"-  **Green DC Utilization**: +{g_diff:.1f} percentage points")
            elif g_diff < 0:
                improvements.append(f"-  **Green DC Utilization**: {g_diff:.1f} percentage points")

            for imp in improvements:
                f.write(imp + "\n")

        print(f"\n✓ Comparison report saved to {report_file}")
        return report_file


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Comparison: ECMR vs C-MORL with full M1-M5 metrics'
    )
    parser.add_argument('--hours', type=int, default=2,
                        help='Simulation hours (default: 24)')
    parser.add_argument('--vms-per-hour', type=int, default=5,
                        help='VMs per hour (default: 10)')
    parser.add_argument('--cmorl-timesteps', type=int, default=10000,
                        help='C-MORL timesteps per policy (default: 10000)')
    parser.add_argument('--cmorl-policies', type=int, default=3,
                        help='C-MORL number of Stage 1 policies (default: 3)')
    parser.add_argument('--cmorl-extend', type=int, default=2,
                        help='C-MORL Stage 2 extensions (default: 2)')
    parser.add_argument('--output-dir', type=str, default='enhanced_comparison_results',
                        help='Output directory (default: enhanced_comparison_results)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for C-MORL (default: 42)')
    parser.add_argument('--skip-ecmr', action='store_true',
                        help='Skip ECMR run (use existing results)')
    parser.add_argument('--skip-cmorl', action='store_true',
                        help='Skip C-MORL run (use existing results)')

    args = parser.parse_args()

    runner = EnhancedComparisonRunner(output_dir=args.output_dir)

    print("="*80)
    print("ENHANCED COMPARISON: ECMR vs C-MORL")
    print("="*80)
    print(f"Configuration: {args.hours} hours × {args.vms_per_hour} VMs/hour")
    print(f"C-MORL: {args.cmorl_policies} policies × {args.cmorl_timesteps} timesteps")
    print(f"Output: {args.output_dir}/")
    print("="*80)

    # Run ECMR
    if not args.skip_ecmr:
        ecmr_metrics, ecmr_data = runner.run_ecmr(
            hours=args.hours,
            vms_per_hour=args.vms_per_hour
        )
    else:
        print("\n  Skipping ECMR run, loading existing results...")
        # Load existing results
        ecmr_output_file = Path(args.output_dir) / 'ecmr' / 'output.txt'
        with open(ecmr_output_file, 'r') as f:
            ecmr_output = f.read()
        ecmr_metrics, ecmr_data = parse_ecmr_results(ecmr_output)

    # Run C-MORL
    if not args.skip_cmorl:
        cmorl_metrics_list, cmorl_data = runner.run_cmorl(
            hours=args.hours,
            vms_per_hour=args.vms_per_hour,
            n_policies=args.cmorl_policies,
            timesteps=args.cmorl_timesteps,
            n_extend=args.cmorl_extend,
            seed=args.seed
        )
    else:
        print("\n  Skipping C-MORL run, loading existing results...")
        # Load existing results
        cmorl_dir = Path(args.output_dir) / 'cmorl'
        cmorl_log = cmorl_dir / 'training_log.txt'
        cmorl_metrics_list, cmorl_data = parse_cmorl_results(str(cmorl_dir), str(cmorl_log))

    # Set ECMR carbon as baseline for C-MORL
    ecmr_carbon = ecmr_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
    for cmorl_metrics in cmorl_metrics_list:
        current_carbon = cmorl_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
        current_intensity = cmorl_metrics.metrics['M4_carbon_reduction']['avg_carbon_intensity_gco2_per_kwh']
        current_renewable = cmorl_metrics.metrics['M4_carbon_reduction']['avg_renewable_pct']

        cmorl_metrics.compute_m4_carbon_reduction(
            total_carbon_gco2=current_carbon,
            baseline_carbon_gco2=ecmr_carbon,
            avg_carbon_intensity=current_intensity,
            avg_renewable_pct=current_renewable
        )

    # Create comparison report
    runner.create_comparison_report(ecmr_metrics, cmorl_metrics_list, ecmr_data, cmorl_data)

    # Print summary
    print("\n" + "="*80)
    print("✓ COMPARISON COMPLETE")
    print("="*80)
    print(f"Results saved to: {args.output_dir}/")
    print(f"  - ECMR metrics: {args.output_dir}/ecmr/metrics.json")
    print(f"  - C-MORL metrics: {args.output_dir}/cmorl/solution_*_metrics.json")
    print(f"  - Comparison report: {args.output_dir}/comparison_report.md")
    print("="*80)


if __name__ == "__main__":
    main()
