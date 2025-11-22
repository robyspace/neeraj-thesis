#!/usr/bin/env python3
"""
Comparison Script: ECMR vs C-MORL
Runs both algorithms under identical conditions and saves results for comparison
"""

import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
import argparse

def run_ecmr(hours=24, vms_per_hour=10, output_dir='comparison_results/ecmr'):
    """Run ECMR baseline"""
    print("\n" + "="*80)
    print("RUNNING ECMR BASELINE")
    print("="*80)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        'python', 'ecmr_heterogeneous_integration.py',
        '--data', 'output/synchronized_dataset_2024.csv',
        '--hours', str(hours),
        '--vms-per-hour', str(vms_per_hour)
    ]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time

    # Save output
    with open(f'{output_dir}/output.txt', 'w') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)

    # Parse and save metrics
    metrics = parse_ecmr_output(result.stdout)
    metrics['duration_seconds'] = duration
    metrics['algorithm'] = 'ECMR'
    metrics['config'] = {
        'hours': hours,
        'vms_per_hour': vms_per_hour,
        'total_vms': hours * vms_per_hour
    }

    with open(f'{output_dir}/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"✓ ECMR completed in {duration:.1f}s")
    print(f"✓ Results saved to {output_dir}/")

    return metrics

def parse_ecmr_output(output):
    """Parse ECMR output to extract key metrics"""
    metrics = {}

    for line in output.split('\n'):
        line = line.strip()

        # Overall Statistics
        if 'Total IT Energy:' in line:
            metrics['it_energy_kwh'] = float(line.split(':')[1].strip().split()[0])
        elif 'Total Facility Energy' in line:
            metrics['total_energy_kwh'] = float(line.split(':')[1].strip().split()[0])
        elif 'Average PUE:' in line:
            metrics['average_pue'] = float(line.split(':')[1].strip())
        elif 'Successful VMs:' in line:
            metrics['successful_vms'] = int(line.split(':')[1].strip())
        elif 'Failed VMs:' in line:
            metrics['failed_vms'] = int(line.split(':')[1].strip())
        elif 'Success Rate:' in line:
            metrics['success_rate_pct'] = float(line.split(':')[1].strip().rstrip('%'))

        # Carbon Metrics
        elif 'Total Carbon Emissions:' in line:
            metrics['total_carbon_gco2'] = float(line.split(':')[1].strip().split()[0])
        elif 'Weighted Avg Carbon Intensity:' in line:
            metrics['avg_carbon_intensity'] = float(line.split(':')[1].strip().split()[0])
        elif 'Weighted Avg Renewable:' in line:
            metrics['avg_renewable_pct'] = float(line.split(':')[1].strip().rstrip('%'))

    return metrics

def run_cmorl(hours=2, vms_per_hour=5, n_policies=3, timesteps=1000,
              n_extend=2, output_dir='comparison_results/cmorl', seed=42):
    """Run C-MORL"""
    print("\n" + "="*80)
    print("RUNNING C-MORL")
    print("="*80)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        'python', 'train_cmorl.py',
        '--simulation-hours', str(hours),
        '--vms-per-hour', str(vms_per_hour),
        '--n-policies', str(n_policies),
        '--timesteps', str(timesteps),
        '--n-extend', str(n_extend),
        '--output-dir', output_dir,
        '--seed', str(seed)
    ]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time

    # Save output
    with open(f'{output_dir}/training_log.txt', 'w') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)

    # Load final results
    try:
        with open(f'{output_dir}/final_results.json', 'r') as f:
            final_results = json.load(f)

        # Compute aggregate metrics from Pareto front
        metrics = compute_cmorl_metrics(final_results, output_dir)
        metrics['duration_seconds'] = duration
        metrics['algorithm'] = 'C-MORL'
        metrics['config'] = {
            'hours': hours,
            'vms_per_hour': vms_per_hour,
            'total_vms': hours * vms_per_hour,
            'n_policies': n_policies,
            'timesteps_per_policy': timesteps,
            'n_extend': n_extend
        }

        with open(f'{output_dir}/comparison_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"✓ C-MORL completed in {duration:.1f}s")
        print(f"✓ Results saved to {output_dir}/")

        return metrics

    except FileNotFoundError:
        print(f"❌ ERROR: Could not find final_results.json")
        return None

def compute_cmorl_metrics(final_results, output_dir):
    """Compute aggregate metrics from C-MORL Pareto front"""
    solutions = final_results['solutions']

    # Extract objectives (energy, carbon, latency)
    energies = [sol['objectives'][0] for sol in solutions]
    carbons = [sol['objectives'][1] for sol in solutions]
    latencies = [sol['objectives'][2] for sol in solutions]

    metrics = {
        'pareto_front_size': final_results['pareto_front_size'],
        'hypervolume': final_results['hypervolume'],
        'expected_utility': final_results['expected_utility'],

        # Best solutions for each objective
        'best_energy_kwh': min(energies),
        'best_carbon_gco2': min(carbons),
        'best_latency_ms': min(latencies),

        # Worst solutions
        'worst_energy_kwh': max(energies),
        'worst_carbon_gco2': max(carbons),
        'worst_latency_ms': max(latencies),

        # Average across Pareto front
        'avg_energy_kwh': sum(energies) / len(energies),
        'avg_carbon_gco2': sum(carbons) / len(carbons),
        'avg_latency_ms': sum(latencies) / len(latencies),

        # Solutions
        'all_solutions': solutions
    }

    return metrics

def create_comparison_report(ecmr_metrics, cmorl_metrics, output_file='comparison_results/comparison.md'):
    """Create a markdown comparison report"""
    with open(output_file, 'w') as f:
        f.write("# ECMR vs C-MORL Comparison Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Configuration\n\n")
        f.write(f"- **ECMR**: {ecmr_metrics['config']['hours']} hours × {ecmr_metrics['config']['vms_per_hour']} VMs/hour = {ecmr_metrics['config']['total_vms']} total VMs\n")
        f.write(f"- **C-MORL**: {cmorl_metrics['config']['hours']} hours × {cmorl_metrics['config']['vms_per_hour']} VMs/hour × {cmorl_metrics['config']['timesteps_per_policy']} timesteps\n\n")

        f.write("## Performance Comparison\n\n")
        f.write("| Metric | ECMR | C-MORL (Best) | C-MORL (Avg) | Improvement |\n")
        f.write("|--------|------|---------------|--------------|-------------|\n")

        # Energy
        ecmr_energy = ecmr_metrics.get('total_energy_kwh', 0)
        cmorl_best_energy = cmorl_metrics.get('best_energy_kwh', 0)
        cmorl_avg_energy = cmorl_metrics.get('avg_energy_kwh', 0)
        energy_imp = ((ecmr_energy - cmorl_best_energy) / ecmr_energy * 100) if ecmr_energy > 0 else 0

        f.write(f"| Energy (kWh) | {ecmr_energy:.2f} | {cmorl_best_energy:.2f} | {cmorl_avg_energy:.2f} | {energy_imp:+.1f}% |\n")

        # Carbon
        ecmr_carbon = ecmr_metrics.get('total_carbon_gco2', 0)
        cmorl_best_carbon = cmorl_metrics.get('best_carbon_gco2', 0)
        cmorl_avg_carbon = cmorl_metrics.get('avg_carbon_gco2', 0)
        carbon_imp = ((ecmr_carbon - cmorl_best_carbon) / ecmr_carbon * 100) if ecmr_carbon > 0 else 0

        f.write(f"| Carbon (gCO2) | {ecmr_carbon:.2f} | {cmorl_best_carbon:.2f} | {cmorl_avg_carbon:.2f} | {carbon_imp:+.1f}% |\n")

        # Training time
        f.write(f"| Runtime (s) | {ecmr_metrics.get('duration_seconds', 0):.1f} | {cmorl_metrics.get('duration_seconds', 0):.1f} | - | - |\n\n")

        f.write("## C-MORL Pareto Front\n\n")
        f.write(f"- **Size**: {cmorl_metrics['pareto_front_size']} solutions\n")
        f.write(f"- **Hypervolume**: {cmorl_metrics['hypervolume']:.2f}\n")
        f.write(f"- **Expected Utility**: {cmorl_metrics['expected_utility']:.2f}\n\n")

        f.write("### All Solutions\n\n")
        f.write("| Solution | Energy (kWh) | Carbon (gCO2) | Latency (ms) | Stage | Preference |\n")
        f.write("|----------|--------------|---------------|--------------|-------|------------|\n")

        for i, sol in enumerate(cmorl_metrics['all_solutions'], 1):
            obj = sol['objectives']
            meta = sol['metadata']
            pref = meta.get('preference', [0,0,0])
            f.write(f"| {i} | {obj[0]:.2f} | {obj[1]:.2f} | {obj[2]:.2f} | {meta.get('stage', '-')} | [{pref[0]:.2f}, {pref[1]:.2f}, {pref[2]:.2f}] |\n")

        f.write("\n## Key Findings\n\n")
        if energy_imp > 0:
            f.write(f"- ✅ C-MORL achieves {energy_imp:.1f}% energy reduction\n")
        if carbon_imp > 0:
            f.write(f"- ✅ C-MORL achieves {carbon_imp:.1f}% carbon reduction\n")
        f.write(f"- C-MORL provides {cmorl_metrics['pareto_front_size']} trade-off solutions vs ECMR's single solution\n")

    print(f"\n✓ Comparison report saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Run ECMR vs C-MORL comparison')
    parser.add_argument('--hours', type=int, default=2, help='Simulation hours')
    parser.add_argument('--vms-per-hour', type=int, default=5, help='VMs per hour')
    parser.add_argument('--cmorl-timesteps', type=int, default=1000, help='C-MORL timesteps per policy')
    parser.add_argument('--output-dir', type=str, default='comparison_results', help='Output directory')
    args = parser.parse_args()

    print("="*80)
    print("ECMR vs C-MORL COMPARISON")
    print("="*80)
    print(f"Configuration: {args.hours} hours × {args.vms_per_hour} VMs/hour")
    print(f"Output: {args.output_dir}/")

    # Run ECMR
    ecmr_metrics = run_ecmr(
        hours=args.hours,
        vms_per_hour=args.vms_per_hour,
        output_dir=f'{args.output_dir}/ecmr'
    )

    # Run C-MORL
    cmorl_metrics = run_cmorl(
        hours=args.hours,
        vms_per_hour=args.vms_per_hour,
        n_policies=3,
        timesteps=args.cmorl_timesteps,
        n_extend=2,
        output_dir=f'{args.output_dir}/cmorl',
        seed=42
    )

    if ecmr_metrics and cmorl_metrics:
        # Create comparison report
        create_comparison_report(ecmr_metrics, cmorl_metrics, f'{args.output_dir}/comparison.md')

        print("\n" + "="*80)
        print("✓ COMPARISON COMPLETE")
        print("="*80)
        print(f"Results saved to {args.output_dir}/")
    else:
        print("\n❌ ERROR: Comparison failed")

if __name__ == "__main__":
    main()
