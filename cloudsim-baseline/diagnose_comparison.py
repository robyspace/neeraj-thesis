#!/usr/bin/env python3
"""
Diagnostic tool to estimate comparison runtime and identify bottlenecks
"""

import argparse
import json
from pathlib import Path


def estimate_runtime(hours, vms_per_hour, timesteps_per_policy, n_policies):
    """Estimate total comparison runtime"""

    total_vms = hours * vms_per_hour

    print("="*80)
    print("COMPARISON RUNTIME ESTIMATION")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Simulation: {hours} hours × {vms_per_hour} VMs/hour = {total_vms} VMs per episode")
    print(f"  C-MORL Training: {n_policies} policies × {timesteps_per_policy} timesteps")
    print()

    # ECMR estimation
    ecmr_time_per_vm = 0.04  # ~40ms per VM based on small test
    ecmr_total_time = total_vms * ecmr_time_per_vm
    print(f"ECMR Estimation:")
    print(f"  Time per VM: {ecmr_time_per_vm:.3f}s")
    print(f"  Total VMs: {total_vms}")
    print(f"  Estimated time: {ecmr_total_time:.1f}s ({ecmr_total_time/60:.1f} minutes)")
    print()

    # C-MORL estimation
    episodes_per_policy = timesteps_per_policy // total_vms
    total_episodes = episodes_per_policy * n_policies

    # Time per episode (scales with VMs)
    base_episode_time = 1.0  # 1 second for 10 VMs
    episode_time = base_episode_time * (total_vms / 10) ** 0.5  # Sublinear scaling

    # Training overhead
    training_overhead_per_episode = 0.5

    total_episode_time = episode_time + training_overhead_per_episode
    cmorl_total_time = total_episodes * total_episode_time

    print(f"C-MORL Estimation:")
    print(f"  Episodes per policy: {episodes_per_policy}")
    print(f"  Total episodes: {total_episodes}")
    print(f"  Time per episode: ~{total_episode_time:.1f}s")
    print(f"  Estimated time: {cmorl_total_time:.1f}s ({cmorl_total_time/60:.1f} minutes)")
    print()

    total_time = ecmr_total_time + cmorl_total_time
    print(f"TOTAL ESTIMATED TIME: {total_time:.1f}s ({total_time/60:.1f} minutes, {total_time/3600:.1f} hours)")
    print()

    # Warnings
    print("⚠️  WARNINGS:")
    if total_vms > 200:
        print(f"  - Large episode size ({total_vms} VMs) may cause memory issues")
        print(f"    Recommendation: Reduce hours or VMs/hour")
    if episodes_per_policy < 20:
        print(f"  - Few episodes per policy ({episodes_per_policy}) may not train well")
        print(f"    Recommendation: Increase timesteps to at least {total_vms * 50}")
    if cmorl_total_time > 3600:
        print(f"  - Training will take > 1 hour")
        print(f"    Recommendation: Run overnight or reduce parameters")
    if total_vms > 100:
        print(f"  - Consider increasing gateway memory to 8-12 GB")
    print()

    # Recommendations
    print("💡 RECOMMENDED CONFIGURATIONS:")
    print()

    configs = [
        ("Quick Test", 2, 5, 10000, 3),
        ("Medium Scale", 12, 10, 15000, 3),
        ("Full Scale (Overnight)", 24, 10, 20000, 5),
    ]

    for name, h, v, t, p in configs:
        tvms = h * v
        eps = t // tvms
        est_time = tvms * 0.04 + (eps * p * (1 + 0.5 * (tvms / 10) ** 0.5))
        print(f"  {name}:")
        print(f"    --hours {h} --vms-per-hour {v} --cmorl-timesteps {t} --cmorl-policies {p}")
        print(f"    Total VMs: {tvms}, Episodes: {eps}, Est. Time: {est_time/60:.1f} min")
        print()

    return total_time


def check_existing_results(output_dir):
    """Check what results already exist"""
    output_path = Path(output_dir)

    print("="*80)
    print("EXISTING RESULTS CHECK")
    print("="*80)
    print()

    if not output_path.exists():
        print(f"❌ Directory does not exist: {output_dir}")
        return

    ecmr_dir = output_path / 'ecmr'
    cmorl_dir = output_path / 'cmorl'

    # Check ECMR
    if ecmr_dir.exists():
        ecmr_output = ecmr_dir / 'output.txt'
        ecmr_metrics = ecmr_dir / 'metrics.json'

        if ecmr_output.exists() and ecmr_metrics.exists():
            print("✅ ECMR results found")
            with open(ecmr_metrics, 'r') as f:
                data = json.load(f)
                print(f"   Total VMs: {data['metrics']['M1_resource_utilization']['total_vms']}")
                print(f"   Energy: {data['metrics']['M1_resource_utilization']['total_energy_kwh']:.2f} kWh")
        else:
            print("⚠️  ECMR directory exists but incomplete")
    else:
        print("❌ No ECMR results")

    print()

    # Check C-MORL
    if cmorl_dir.exists():
        final_results = cmorl_dir / 'final_results.json'
        training_log = cmorl_dir / 'training_log.txt'

        if final_results.exists():
            with open(final_results, 'r') as f:
                data = json.load(f)
                print(f"✅ C-MORL results found")
                print(f"   Pareto front size: {data['pareto_front_size']}")
                print(f"   Hypervolume: {data['hypervolume']:.2f}")

            # Check if training completed
            if training_log.exists():
                with open(training_log, 'r') as f:
                    log_content = f.read()
                    if 'TRAINING & EVALUATION COMPLETE' in log_content:
                        print("   Status: ✅ Complete")
                    else:
                        print("   Status: ⚠️  Incomplete (may have crashed)")
        else:
            print("⚠️  C-MORL directory exists but no final_results.json")
            if training_log.exists():
                # Check progress
                with open(training_log, 'r') as f:
                    log_content = f.read()
                    episodes = log_content.count('Episode ')
                    print(f"   Episodes logged: {episodes}")
    else:
        print("❌ No C-MORL results")

    print()


def main():
    parser = argparse.ArgumentParser(description='Diagnose and estimate comparison runtime')
    parser.add_argument('--hours', type=int, default=24, help='Simulation hours')
    parser.add_argument('--vms-per-hour', type=int, default=10, help='VMs per hour')
    parser.add_argument('--cmorl-timesteps', type=int, default=15000, help='Timesteps per policy')
    parser.add_argument('--cmorl-policies', type=int, default=5, help='Number of policies')
    parser.add_argument('--check-results', type=str, help='Check existing results directory')

    args = parser.parse_args()

    if args.check_results:
        check_existing_results(args.check_results)
    else:
        estimate_runtime(args.hours, args.vms_per_hour, args.cmorl_timesteps, args.cmorl_policies)


if __name__ == "__main__":
    main()
