#!/usr/bin/env python3
"""
Enhanced C-MORL Parser
Extracts all metrics including M5 from C-MORL evaluation results
Parses both final_results.json and the detailed evaluation output
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from unified_metrics import UnifiedMetrics


def parse_cmorl_results(results_dir: str, evaluation_output: str = None) -> Tuple[List[UnifiedMetrics], Dict]:
    """
    Parse C-MORL results directory and extract metrics for ALL Pareto solutions

    Args:
        results_dir: Path to C-MORL output directory (contains final_results.json)
        evaluation_output: Optional path to full training/evaluation output text

    Returns:
        (List of UnifiedMetrics for each solution, raw_data dict)
    """
    results_path = Path(results_dir)
    final_results_file = results_path / 'final_results.json'

    if not final_results_file.exists():
        raise FileNotFoundError(f"Could not find {final_results_file}")

    with open(final_results_file, 'r') as f:
        cmorl_data = json.load(f)

    # Load evaluation output if available
    eval_text = ""
    if evaluation_output and Path(evaluation_output).exists():
        with open(evaluation_output, 'r') as f:
            eval_text = f.read()

    # Extract detailed solution results from evaluation output
    solution_details = extract_solution_details_from_output(eval_text) if eval_text else {}

    # Create metrics for each Pareto solution
    all_metrics = []
    solutions = cmorl_data.get('solutions', [])

    for idx, solution in enumerate(solutions):
        policy_id = solution['metadata'].get('policy_id')
        preference = solution['metadata'].get('preference', [0, 0, 0])

        # Get detailed results for this solution if available
        solution_detail = solution_details.get(idx + 1, {})

        metrics = create_metrics_for_solution(
            solution=solution,
            solution_idx=idx,
            solution_detail=solution_detail,
            cmorl_data=cmorl_data
        )

        all_metrics.append(metrics)

    # Aggregate raw data
    raw_data = {
        'pareto_front_size': cmorl_data.get('pareto_front_size', len(solutions)),
        'hypervolume': cmorl_data.get('hypervolume', 0.0),
        'expected_utility': cmorl_data.get('expected_utility', 0.0),
        'solutions': solutions,
        'solution_details': solution_details
    }

    return all_metrics, raw_data


def extract_solution_details_from_output(text: str) -> Dict[int, Dict]:
    """
    Extract detailed evaluation results for each solution from training output
    Returns: {solution_number: {details_dict}}
    """
    solution_details = {}

    # Find all solution result blocks
    solution_pattern = r'C-MORL SOLUTION #(\d+) RESULTS.*?(?=C-MORL SOLUTION #|\Z)'
    solution_blocks = re.finditer(solution_pattern, text, re.DOTALL)

    for match in solution_blocks:
        solution_num = int(match.group(1))
        block_text = match.group(0)

        details = {}

        # Extract overall statistics
        details['overall_stats'] = extract_solution_overall_stats(block_text)

        # Extract carbon metrics
        details['carbon_metrics'] = extract_solution_carbon_metrics(block_text)

        # Extract M5: Green DC Utilization
        details['green_dc_util'] = extract_solution_green_dc_util(block_text)

        # Extract per-datacenter stats
        details['datacenter_stats'] = extract_solution_dc_stats(block_text)

        # Extract datacenter selection
        details['dc_selection'] = extract_solution_dc_selection(block_text)

        # Extract VM distribution
        details['vm_distribution'] = extract_solution_vm_distribution(block_text)

        # Extract C-MORL objectives
        details['objectives'] = extract_solution_objectives(block_text)

        solution_details[solution_num] = details

    return solution_details


def extract_solution_overall_stats(text: str) -> Dict:
    """Extract overall statistics from solution block"""
    stats = {}

    patterns = {
        'total_it_energy_kwh': r'Total IT Energy:\s+([\d.]+)\s+kWh',
        'total_facility_energy_kwh': r'Total Facility Energy.*?:\s+([\d.]+)\s+kWh',
        'average_pue': r'Average PUE:\s+([\d.]+)',
        'total_vms': r'Total VMs Requested:\s+(\d+)',
        'successful_vms': r'Successful VMs:\s+(\d+)',
        'failed_vms': r'Failed VMs:\s+(\d+)',
        'success_rate_pct': r'Success Rate:\s+([\d.]+)%'
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1)
            stats[key] = float(value) if '.' in value else int(value)
        else:
            stats[key] = 0.0 if 'pct' in key or 'pue' in key or 'kwh' in key else 0

    return stats


def extract_solution_carbon_metrics(text: str) -> Dict:
    """Extract carbon metrics from solution block"""
    carbon = {}

    # Total carbon
    match = re.search(r'Total Carbon Emissions:\s+([\d.]+)\s+kg CO2', text)
    if match:
        carbon['total_carbon_kg'] = float(match.group(1))
        carbon['total_carbon_gco2'] = carbon['total_carbon_kg'] * 1000
    else:
        carbon['total_carbon_kg'] = 0.0
        carbon['total_carbon_gco2'] = 0.0

    # Weighted avg carbon intensity
    match = re.search(r'Weighted Avg Carbon Intensity:\s+([\d.]+)\s+gCO2/kWh', text)
    carbon['avg_carbon_intensity'] = float(match.group(1)) if match else 0.0

    # Weighted avg renewable
    match = re.search(r'Weighted Avg Renewable %:\s+([\d.]+)%', text)
    carbon['avg_renewable_pct'] = float(match.group(1)) if match else 0.0

    return carbon


def extract_solution_green_dc_util(text: str) -> Dict:
    """Extract M5: Green DC Utilization from solution block"""
    green_util = {}

    # Find M5 section
    m5_match = re.search(
        r'M5:\s*GREEN DATACENTER UTILIZATION\s*-+\s*(.*?)(?=\n\s*PER-DATACENTER|\n\s*VM TYPE|$)',
        text,
        re.DOTALL | re.IGNORECASE
    )

    if not m5_match:
        return {}

    m5_section = m5_match.group(1)

    # Extract green and brown DC VMs
    green_match = re.search(r'Green Datacenter.*?VMs:\s+(\d+)\s+\(([\d.]+)%\)', m5_section)
    brown_match = re.search(r'Brown Datacenter.*?VMs:\s+(\d+)\s+\(([\d.]+)%\)', m5_section)

    if green_match and brown_match:
        green_util['green_dc_vms'] = int(green_match.group(1))
        green_util['green_pct'] = float(green_match.group(2))
        green_util['brown_dc_vms'] = int(brown_match.group(1))
        green_util['brown_pct'] = float(brown_match.group(2))
        green_util['total_vms'] = green_util['green_dc_vms'] + green_util['brown_dc_vms']

    # Extract utilization score
    score_match = re.search(r'Green DC Utilization Score:\s+([\d.]+)', m5_section)
    if score_match:
        green_util['green_dc_score'] = float(score_match.group(1))

    return green_util


def extract_solution_dc_stats(text: str) -> Dict[str, Dict]:
    """Extract per-datacenter statistics"""
    dc_stats = {}

    # Find the PER-DATACENTER STATISTICS section
    dc_section_match = re.search(
        r'PER-DATACENTER STATISTICS\s*-+\s*(.*?)(?=\n\s*VM TYPE DISTRIBUTION|\n\s*DATACENTER SELECTION|$)',
        text,
        re.DOTALL
    )

    if not dc_section_match:
        return dc_stats

    dc_section = dc_section_match.group(1)

    # Split by datacenter entries
    dc_entries = re.split(r'\n\s+(DC_\w+)\s+\(', dc_section)

    for i in range(1, len(dc_entries), 2):
        if i + 1 >= len(dc_entries):
            break

        dc_id = dc_entries[i]
        dc_content = dc_entries[i + 1]

        stats = {}

        # Extract VMs
        vm_match = re.search(r'VMs:\s+(\d+)\s+\(([\d.]+)%', dc_content)
        if vm_match:
            stats['vms_placed'] = int(vm_match.group(1))
            stats['vm_percentage'] = float(vm_match.group(2))

        # Extract energy
        energy_match = re.search(r'IT Energy:\s+([\d.]+)\s+kWh.*?Total.*?:\s+([\d.]+)\s+kWh', dc_content)
        if energy_match:
            stats['it_energy_kwh'] = float(energy_match.group(1))
            stats['total_energy_kwh'] = float(energy_match.group(2))

        # Extract PUE
        pue_match = re.search(r'PUE\s+([\d.]+)', dc_content)
        if pue_match:
            stats['pue'] = float(pue_match.group(1))

        # Extract carbon
        carbon_match = re.search(r'Carbon:\s+(\d+)\s+gCO2/kWh.*?Emissions:\s+([\d.]+)\s+kg CO2', dc_content)
        if carbon_match:
            stats['carbon_intensity'] = float(carbon_match.group(1))
            stats['carbon_emissions_kg'] = float(carbon_match.group(2))

        # Extract renewable
        renewable_match = re.search(r'Renewable:\s+([\d.]+)%', dc_content)
        if renewable_match:
            stats['renewable_pct'] = float(renewable_match.group(1))

        # Extract utilization
        util_match = re.search(r'Utilization:\s+CPU\s+([\d.]+)%,\s+RAM\s+([\d.]+)%', dc_content)
        if util_match:
            stats['cpu_utilization'] = float(util_match.group(1))
            stats['ram_utilization'] = float(util_match.group(2))
        else:
            stats['cpu_utilization'] = 0.0
            stats['ram_utilization'] = 0.0

        dc_stats[dc_id] = stats

    return dc_stats


def extract_solution_dc_selection(text: str) -> Dict:
    """Extract datacenter selection distribution"""
    dc_selection = {}

    dc_sel_match = re.search(
        r'DATACENTER SELECTION DISTRIBUTION\s*-+\s*(.*?)(?=\n\s*C-MORL OBJECTIVES|$)',
        text,
        re.DOTALL
    )

    if not dc_sel_match:
        return dc_selection

    dc_sel_section = dc_sel_match.group(1)

    dc_pattern = r'(DC_\w+)\s*:\s*(\d+)\s+\(([\d.]+)%\)'
    for match in re.finditer(dc_pattern, dc_sel_section):
        dc_id = match.group(1)
        vms = int(match.group(2))
        percentage = float(match.group(3))
        dc_selection[dc_id] = {'vms': vms, 'percentage': percentage}

    return dc_selection


def extract_solution_vm_distribution(text: str) -> Dict:
    """Extract VM type distribution"""
    vm_dist = {'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0}

    vm_section_match = re.search(
        r'VM TYPE DISTRIBUTION\s*-+\s*(.*?)(?=\n\s*DATACENTER SELECTION|$)',
        text,
        re.DOTALL
    )

    if not vm_section_match:
        return vm_dist

    vm_section = vm_section_match.group(1)

    for vm_type in ['small', 'medium', 'large', 'xlarge']:
        pattern = rf'{vm_type}\s*:\s*(\d+)'
        match = re.search(pattern, vm_section, re.IGNORECASE)
        if match:
            vm_dist[vm_type] = int(match.group(1))

    return vm_dist


def extract_solution_objectives(text: str) -> Dict:
    """Extract C-MORL objectives (learned trade-offs)"""
    objectives = {}

    obj_match = re.search(
        r'C-MORL OBJECTIVES.*?-+\s*Energy:\s+([\d.]+)\s+kWh\s*Carbon:\s+([\d.]+)\s+gCO2\s*Latency:\s+([\d.]+)\s+ms',
        text,
        re.DOTALL
    )

    if obj_match:
        objectives['energy_kwh'] = float(obj_match.group(1))
        objectives['carbon_gco2'] = float(obj_match.group(2))
        objectives['latency_ms'] = float(obj_match.group(3))

    return objectives


def create_metrics_for_solution(solution: Dict, solution_idx: int,
                                  solution_detail: Dict, cmorl_data: Dict) -> UnifiedMetrics:
    """
    Create UnifiedMetrics object for a single Pareto solution

    Args:
        solution: Solution dict from final_results.json
        solution_idx: Index in Pareto front
        solution_detail: Detailed evaluation results from output
        cmorl_data: Full C-MORL data
    """
    policy_id = solution['metadata'].get('policy_id', f"solution_{solution_idx + 1}")
    preference = solution['metadata'].get('preference', [0, 0, 0])

    metrics = UnifiedMetrics(f"C-MORL Solution #{solution_idx + 1} (Policy {policy_id})")

    # Get objectives
    objectives = solution.get('objectives', [0, 0, 0])
    energy_kwh = objectives[0]
    carbon_gco2 = objectives[1]
    latency_ms = objectives[2]

    # Get detailed stats if available
    if solution_detail:
        overall_stats = solution_detail.get('overall_stats', {})
        carbon_metrics = solution_detail.get('carbon_metrics', {})
        green_dc_util = solution_detail.get('green_dc_util', {})
        dc_stats = solution_detail.get('datacenter_stats', {})
        dc_selection = solution_detail.get('dc_selection', {})

        # Use actual values from evaluation
        total_energy = overall_stats.get('total_facility_energy_kwh', energy_kwh)
        total_vms = overall_stats.get('total_vms', 10)
        successful_vms = overall_stats.get('successful_vms', total_vms)
        failed_vms = overall_stats.get('failed_vms', 0)
        avg_pue = overall_stats.get('average_pue', 1.18)

        # Compute average utilization
        avg_cpu, avg_ram = compute_weighted_utilization(dc_stats, dc_selection)

    else:
        # Fallback to objectives from final_results.json
        total_energy = energy_kwh
        total_vms = 10  # Default episode size
        successful_vms = 10
        failed_vms = 0
        avg_cpu = 50.0  # Estimate
        avg_ram = 50.0  # Estimate
        green_dc_util = {}
        carbon_metrics = {'total_carbon_gco2': carbon_gco2}

    # M1: Resource Utilization
    metrics.compute_m1_resource_utilization(
        total_energy_kwh=total_energy,
        total_vms=total_vms,
        avg_cpu_util=avg_cpu,
        avg_ram_util=avg_ram
    )

    # M2: Throughput
    # Use training time from metadata or default
    training_time = 60.0  # Default for single episode evaluation
    metrics.compute_m2_throughput(
        successful_vms=successful_vms,
        failed_vms=failed_vms,
        total_time_seconds=training_time
    )

    # M3: Response Time
    metrics.compute_m3_response_time(
        avg_latency_ms=latency_ms,
        avg_vm_creation_time_s=0.05,  # RL-optimized placement
        total_simulation_time_s=training_time
    )

    # M4: Carbon Reduction (baseline will be set later)
    metrics.compute_m4_carbon_reduction(
        total_carbon_gco2=carbon_metrics.get('total_carbon_gco2', carbon_gco2),
        baseline_carbon_gco2=None,  # Set during comparison
        avg_carbon_intensity=carbon_metrics.get('avg_carbon_intensity', 0.0),
        avg_renewable_pct=carbon_metrics.get('avg_renewable_pct', 0.0)
    )

    # M5: Green DC Utilization
    if green_dc_util:
        metrics.compute_m5_green_dc_utilization(
            green_dc_vms=green_dc_util.get('green_dc_vms', 0),
            brown_dc_vms=green_dc_util.get('brown_dc_vms', 0)
        )

    # Store raw solution data
    metrics.raw_data = {
        'solution_idx': solution_idx,
        'policy_id': policy_id,
        'preference': preference,
        'objectives': objectives,
        'stage': solution['metadata'].get('stage'),
        'detail': solution_detail
    }

    return metrics


def compute_weighted_utilization(dc_stats: Dict, dc_selection: Dict) -> Tuple[float, float]:
    """Compute weighted average CPU and RAM utilization"""
    if not dc_stats or not dc_selection:
        return 0.0, 0.0

    total_vms = sum(data.get('vms', 0) for data in dc_selection.values())
    if total_vms == 0:
        return 0.0, 0.0

    weighted_cpu = 0.0
    weighted_ram = 0.0

    for dc_id, selection in dc_selection.items():
        vms = selection.get('vms', 0)
        if vms == 0:
            continue

        stats = dc_stats.get(dc_id, {})
        cpu_util = stats.get('cpu_utilization', 0.0)
        ram_util = stats.get('ram_utilization', 0.0)

        weight = vms / total_vms
        weighted_cpu += cpu_util * weight
        weighted_ram += ram_util * weight

    return weighted_cpu, weighted_ram


if __name__ == "__main__":
    # Test the parser
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_cmorl_parser.py <cmorl_results_dir> [evaluation_output.txt]")
        sys.exit(1)

    results_dir = sys.argv[1]
    eval_output = sys.argv[2] if len(sys.argv) > 2 else None

    all_metrics, raw_data = parse_cmorl_results(results_dir, eval_output)

    print(f"\n{'='*80}")
    print(f"FOUND {len(all_metrics)} PARETO SOLUTIONS")
    print(f"{'='*80}")

    for i, metrics in enumerate(all_metrics):
        metrics.print_summary()

    print(f"\n{'='*80}")
    print("PARETO FRONT SUMMARY")
    print(f"{'='*80}")
    print(f"Pareto Front Size: {raw_data['pareto_front_size']}")
    print(f"Hypervolume: {raw_data['hypervolume']:.4f}")
    print(f"Expected Utility: {raw_data['expected_utility']:.4f}")
