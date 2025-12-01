#!/usr/bin/env python3
"""
Comparison Visualizer
Creates charts and graphs comparing ECMR and C-MORL performance
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from typing import List, Dict
from unified_metrics import UnifiedMetrics


class ComparisonVisualizer:
    """Generate visualizations for ECMR vs C-MORL comparison"""

    def __init__(self, output_dir: str = 'enhanced_comparison_results/figures'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set plot style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = {
            'ecmr': '#FF6B6B',
            'cmorl': '#4ECDC4',
            'pareto': '#95E1D3',
            'green': '#6BCF7F',
            'brown': '#D4A574'
        }

    def plot_objectives_comparison(self, ecmr_metrics: UnifiedMetrics,
                                     cmorl_metrics_list: List[UnifiedMetrics],
                                     filename: str = 'objectives_comparison.png'):
        """
        Bar chart comparing Energy, Carbon, and Latency across solutions
        """
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle('Objectives Comparison: ECMR vs C-MORL Pareto Front', fontsize=16, fontweight='bold')

        objectives = ['Energy (kWh)', 'Carbon (gCO2)', 'Latency (ms)']
        metric_keys = [
            ('M1_resource_utilization', 'total_energy_kwh'),
            ('M4_carbon_reduction', 'total_carbon_emissions_gco2'),
            ('M3_response_time', 'avg_network_latency_ms')
        ]

        for idx, (obj_name, (metric_key, value_key)) in enumerate(zip(objectives, metric_keys)):
            ax = axes[idx]

            # Get ECMR value
            ecmr_val = ecmr_metrics.metrics[metric_key][value_key]

            # Get all C-MORL values
            cmorl_vals = [m.metrics[metric_key][value_key] for m in cmorl_metrics_list]

            # Plot
            x_pos = np.arange(len(cmorl_vals) + 1)
            values = [ecmr_val] + cmorl_vals
            colors = [self.colors['ecmr']] + [self.colors['cmorl']] * len(cmorl_vals)

            bars = ax.bar(x_pos, values, color=colors, alpha=0.8, edgecolor='black')

            # Highlight best C-MORL solution
            best_idx = np.argmin(cmorl_vals) + 1
            bars[best_idx].set_color(self.colors['green'])
            bars[best_idx].set_edgecolor('darkgreen')
            bars[best_idx].set_linewidth(2)

            ax.set_xlabel('Solution', fontweight='bold')
            ax.set_ylabel(obj_name, fontweight='bold')
            ax.set_title(obj_name, fontweight='bold')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(['ECMR'] + [f'C{i+1}' for i in range(len(cmorl_vals))])
            ax.grid(axis='y', alpha=0.3)

            # Add value labels on bars
            for i, (bar, val) in enumerate(zip(bars, values)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:.2f}',
                       ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {save_path}")

    def plot_pareto_front_3d(self, ecmr_metrics: UnifiedMetrics,
                              cmorl_metrics_list: List[UnifiedMetrics],
                              filename: str = 'pareto_front_3d.png'):
        """
        3D scatter plot of Pareto front (Energy, Carbon, Latency)
        """
        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection='3d')

        # ECMR point
        ecmr_energy = ecmr_metrics.metrics['M1_resource_utilization']['total_energy_kwh']
        ecmr_carbon = ecmr_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
        ecmr_latency = ecmr_metrics.metrics['M3_response_time']['avg_network_latency_ms']

        # C-MORL Pareto front
        cmorl_energies = [m.metrics['M1_resource_utilization']['total_energy_kwh'] for m in cmorl_metrics_list]
        cmorl_carbons = [m.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2'] for m in cmorl_metrics_list]
        cmorl_latencies = [m.metrics['M3_response_time']['avg_network_latency_ms'] for m in cmorl_metrics_list]

        # Plot
        ax.scatter(ecmr_energy, ecmr_carbon, ecmr_latency,
                  c=self.colors['ecmr'], s=200, marker='o', label='ECMR',
                  edgecolors='black', linewidths=2, alpha=0.9)

        ax.scatter(cmorl_energies, cmorl_carbons, cmorl_latencies,
                  c=self.colors['cmorl'], s=150, marker='^', label='C-MORL Pareto Front',
                  edgecolors='black', linewidths=1.5, alpha=0.8)

        # Labels
        ax.set_xlabel('Energy (kWh)', fontweight='bold', fontsize=11)
        ax.set_ylabel('Carbon (gCO2)', fontweight='bold', fontsize=11)
        ax.set_zlabel('Latency (ms)', fontweight='bold', fontsize=11)
        ax.set_title('3D Pareto Front: ECMR vs C-MORL', fontweight='bold', fontsize=14)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)

        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {save_path}")

    def plot_metrics_radar(self, ecmr_metrics: UnifiedMetrics,
                            cmorl_best_metrics: UnifiedMetrics,
                            filename: str = 'metrics_radar.png'):
        """
        Radar chart comparing M1-M5 scores between ECMR and best C-MORL
        """
        from math import pi

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        # Metrics to compare (normalized scores 0-1)
        metrics_names = ['M1: Resource\nUtilization', 'M2: Throughput',
                         'M3: Response\nTime', 'M4: Carbon\nReduction', 'M5: Green DC\nUtilization']

        score_keys = [
            ('M1_resource_utilization', 'efficiency_score'),
            ('M2_throughput', 'throughput_score'),
            ('M3_response_time', 'response_score'),
            ('M4_carbon_reduction', 'carbon_score'),
            ('M5_green_dc_utilization', 'green_dc_score')
        ]

        ecmr_scores = []
        cmorl_scores = []

        for metric_key, score_key in score_keys:
            ecmr_scores.append(ecmr_metrics.metrics[metric_key].get(score_key, 0.0))
            cmorl_scores.append(cmorl_best_metrics.metrics[metric_key].get(score_key, 0.0))

        # Number of variables
        num_vars = len(metrics_names)
        angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
        ecmr_scores += ecmr_scores[:1]
        cmorl_scores += cmorl_scores[:1]
        angles += angles[:1]

        # Plot
        ax.plot(angles, ecmr_scores, 'o-', linewidth=2, label='ECMR',
                color=self.colors['ecmr'], markersize=8)
        ax.fill(angles, ecmr_scores, alpha=0.25, color=self.colors['ecmr'])

        ax.plot(angles, cmorl_scores, 'o-', linewidth=2, label='C-MORL (Best)',
                color=self.colors['cmorl'], markersize=8)
        ax.fill(angles, cmorl_scores, alpha=0.25, color=self.colors['cmorl'])

        # Fix axis
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics_names, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.title('Metrics Comparison (Normalized Scores)', size=16, fontweight='bold', pad=20)
        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=12)

        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {save_path}")

    def plot_green_dc_utilization(self, ecmr_metrics: UnifiedMetrics,
                                    cmorl_metrics_list: List[UnifiedMetrics],
                                    filename: str = 'green_dc_utilization.png'):
        """
        Stacked bar chart showing Green vs Brown DC utilization
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Get M5 data
        solutions = ['ECMR'] + [f'C-MORL\nSol {i+1}' for i in range(len(cmorl_metrics_list))]
        all_metrics = [ecmr_metrics] + cmorl_metrics_list

        green_vms = []
        brown_vms = []

        for metrics in all_metrics:
            m5 = metrics.metrics.get('M5_green_dc_utilization', {})
            green_vms.append(m5.get('green_dc_vms', 0))
            brown_vms.append(m5.get('brown_dc_vms', 0))

        # Create stacked bar chart
        x_pos = np.arange(len(solutions))
        width = 0.6

        p1 = ax.bar(x_pos, green_vms, width, label='Green DCs (DG)',
                    color=self.colors['green'], edgecolor='black', linewidth=1.5)
        p2 = ax.bar(x_pos, brown_vms, width, bottom=green_vms,
                    label='Brown DCs (DB)', color=self.colors['brown'],
                    edgecolor='black', linewidth=1.5)

        # Add percentage labels
        for i, (g, b) in enumerate(zip(green_vms, brown_vms)):
            total = g + b
            if total > 0:
                green_pct = (g / total) * 100
                brown_pct = (b / total) * 100

                # Green label
                if g > 0:
                    ax.text(i, g/2, f'{green_pct:.1f}%', ha='center', va='center',
                           fontweight='bold', fontsize=10, color='darkgreen')

                # Brown label
                if b > 0:
                    ax.text(i, g + b/2, f'{brown_pct:.1f}%', ha='center', va='center',
                           fontweight='bold', fontsize=10, color='saddlebrown')

        ax.set_xlabel('Solution', fontweight='bold', fontsize=12)
        ax.set_ylabel('Number of VMs', fontweight='bold', fontsize=12)
        ax.set_title('M5: Green vs Brown Datacenter Utilization', fontweight='bold', fontsize=14)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(solutions, fontsize=10)
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {save_path}")

    def plot_improvement_summary(self, ecmr_metrics: UnifiedMetrics,
                                  cmorl_best_metrics: UnifiedMetrics,
                                  filename: str = 'improvement_summary.png'):
        """
        Horizontal bar chart showing percentage improvements
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        metrics = []
        improvements = []
        colors_list = []

        # Energy per VM
        ecmr_e = ecmr_metrics.metrics['M1_resource_utilization']['energy_per_vm_kwh']
        cmorl_e = cmorl_best_metrics.metrics['M1_resource_utilization']['energy_per_vm_kwh']
        if ecmr_e > 0:
            e_imp = ((ecmr_e - cmorl_e) / ecmr_e * 100)
            metrics.append('Energy per VM')
            improvements.append(e_imp)
            colors_list.append(self.colors['green'] if e_imp > 0 else self.colors['ecmr'])

        # Total Carbon
        ecmr_c = ecmr_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
        cmorl_c = cmorl_best_metrics.metrics['M4_carbon_reduction']['total_carbon_emissions_gco2']
        if ecmr_c > 0:
            c_imp = ((ecmr_c - cmorl_c) / ecmr_c * 100)
            metrics.append('Carbon Emissions')
            improvements.append(c_imp)
            colors_list.append(self.colors['green'] if c_imp > 0 else self.colors['ecmr'])

        # Latency
        ecmr_l = ecmr_metrics.metrics['M3_response_time']['avg_network_latency_ms']
        cmorl_l = cmorl_best_metrics.metrics['M3_response_time']['avg_network_latency_ms']
        if ecmr_l > 0:
            l_imp = ((ecmr_l - cmorl_l) / ecmr_l * 100)
            metrics.append('Network Latency')
            improvements.append(l_imp)
            colors_list.append(self.colors['green'] if l_imp > 0 else self.colors['ecmr'])

        # Green DC Utilization (percentage point difference)
        ecmr_g = ecmr_metrics.metrics['M5_green_dc_utilization'].get('green_utilization_pct', 0.0)
        cmorl_g = cmorl_best_metrics.metrics['M5_green_dc_utilization'].get('green_utilization_pct', 0.0)
        g_diff = cmorl_g - ecmr_g
        metrics.append('Green DC Util\n(pp difference)')
        improvements.append(g_diff)
        colors_list.append(self.colors['green'] if g_diff > 0 else self.colors['ecmr'])

        # Plot
        y_pos = np.arange(len(metrics))
        bars = ax.barh(y_pos, improvements, color=colors_list, edgecolor='black', linewidth=1.5, alpha=0.8)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, improvements)):
            width = bar.get_width()
            label_x_pos = width + (1 if width > 0 else -1)
            ax.text(label_x_pos, bar.get_y() + bar.get_height()/2,
                   f'{val:+.1f}%' if i < 3 else f'{val:+.1f}pp',
                   ha='left' if width > 0 else 'right', va='center',
                   fontweight='bold', fontsize=11)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(metrics, fontsize=11, fontweight='bold')
        ax.set_xlabel('Improvement (%)', fontweight='bold', fontsize=12)
        ax.set_title('C-MORL vs ECMR: Performance Improvements', fontweight='bold', fontsize=14)
        ax.axvline(x=0, color='black', linestyle='-', linewidth=1.5)
        ax.grid(axis='x', alpha=0.3)

        plt.tight_layout()
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {save_path}")

    def generate_all_plots(self, ecmr_metrics: UnifiedMetrics,
                            cmorl_metrics_list: List[UnifiedMetrics]):
        """Generate all comparison plots"""
        print("\n" + "="*80)
        print("GENERATING VISUALIZATIONS")
        print("="*80)

        # Find best C-MORL solution (energy-optimal)
        best_energy_idx = min(range(len(cmorl_metrics_list)),
                               key=lambda i: cmorl_metrics_list[i].metrics['M1_resource_utilization']['total_energy_kwh'])
        cmorl_best = cmorl_metrics_list[best_energy_idx]

        self.plot_objectives_comparison(ecmr_metrics, cmorl_metrics_list)
        self.plot_pareto_front_3d(ecmr_metrics, cmorl_metrics_list)
        self.plot_metrics_radar(ecmr_metrics, cmorl_best)
        self.plot_green_dc_utilization(ecmr_metrics, cmorl_metrics_list)
        self.plot_improvement_summary(ecmr_metrics, cmorl_best)

        print("="*80)
        print(f"✓ All visualizations saved to {self.output_dir}/")
        print("="*80)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Generate comparison visualizations')
    parser.add_argument('--results-dir', type=str, default='enhanced_comparison_results',
                        help='Results directory from run_enhanced_comparison.py')
    args = parser.parse_args()

    results_dir = Path(args.results_dir)

    # Load ECMR metrics
    ecmr_metrics_file = results_dir / 'ecmr' / 'metrics.json'
    if not ecmr_metrics_file.exists():
        print(f"Error: Could not find {ecmr_metrics_file}")
        print("Run run_enhanced_comparison.py first!")
        sys.exit(1)

    with open(ecmr_metrics_file, 'r') as f:
        ecmr_data = json.load(f)
    ecmr_metrics = UnifiedMetrics("ECMR")
    ecmr_metrics.metrics = ecmr_data['metrics']

    # Load C-MORL metrics
    cmorl_dir = results_dir / 'cmorl'
    cmorl_metrics_files = sorted(cmorl_dir.glob('solution_*_metrics.json'))

    if not cmorl_metrics_files:
        print(f"Error: Could not find C-MORL solution metrics in {cmorl_dir}")
        sys.exit(1)

    cmorl_metrics_list = []
    for metrics_file in cmorl_metrics_files:
        with open(metrics_file, 'r') as f:
            cmorl_data = json.load(f)
        metrics = UnifiedMetrics(cmorl_data['algorithm'])
        metrics.metrics = cmorl_data['metrics']
        metrics.raw_data = cmorl_data.get('raw_data', {})
        cmorl_metrics_list.append(metrics)

    # Generate visualizations
    visualizer = ComparisonVisualizer(output_dir=str(results_dir / 'figures'))
    visualizer.generate_all_plots(ecmr_metrics, cmorl_metrics_list)


if __name__ == "__main__":
    main()
