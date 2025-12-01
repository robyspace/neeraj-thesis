#!/usr/bin/env python3
"""
Enhanced ECMR Parser
Extracts all metrics including M5 (Green DC Utilization) from ECMR output
"""

import re
from typing import Dict, Tuple, List
from unified_metrics import UnifiedMetrics


def parse_ecmr_results(output_text: str) -> Tuple[UnifiedMetrics, Dict]:
    """
    Parse ECMR output and extract comprehensive metrics

    Returns:
        (UnifiedMetrics object, raw_data dict)
    """
    metrics = UnifiedMetrics("ECMR")
    raw_data = {}

    # ========== SECTION 1: Overall Statistics ==========
    overall_stats = extract_overall_statistics(output_text)
    raw_data['overall_stats'] = overall_stats

    # ========== SECTION 2: Carbon Metrics ==========
    carbon_metrics = extract_carbon_metrics(output_text)
    raw_data['carbon_metrics'] = carbon_metrics

    # ========== SECTION 3: Per-Datacenter Stats ==========
    dc_stats = extract_datacenter_stats(output_text)
    raw_data['datacenter_stats'] = dc_stats

    # ========== SECTION 4: VM Distribution ==========
    vm_distribution = extract_vm_distribution(output_text)
    raw_data['vm_distribution'] = vm_distribution

    # ========== SECTION 5: Datacenter Selection (for M5) ==========
    dc_selection = extract_datacenter_selection(output_text)
    raw_data['datacenter_selection'] = dc_selection

    # ========== SECTION 6: M5 - Green DC Utilization ==========
    green_dc_util = extract_green_dc_utilization(output_text)
    raw_data['green_dc_utilization'] = green_dc_util

    # ========== Compute Unified Metrics ==========

    # M1: Resource Utilization Efficiency
    avg_cpu_util, avg_ram_util = compute_average_utilization(dc_stats, dc_selection)
    metrics.compute_m1_resource_utilization(
        total_energy_kwh=overall_stats['total_facility_energy_kwh'],
        total_vms=overall_stats['total_vms'],
        avg_cpu_util=avg_cpu_util,
        avg_ram_util=avg_ram_util
    )

    # M2: Throughput
    # Extract actual runtime from output or use placeholder
    runtime_seconds = extract_runtime(output_text) or 10.0
    metrics.compute_m2_throughput(
        successful_vms=overall_stats['successful_vms'],
        failed_vms=overall_stats['failed_vms'],
        total_time_seconds=runtime_seconds
    )

    # M3: Response Time
    avg_latency = compute_weighted_avg_latency(dc_stats, dc_selection)
    metrics.compute_m3_response_time(
        avg_latency_ms=avg_latency,
        avg_vm_creation_time_s=0.1,  # ECMR is greedy, fast placement
        total_simulation_time_s=runtime_seconds
    )

    # M4: Carbon Reduction
    metrics.compute_m4_carbon_reduction(
        total_carbon_gco2=carbon_metrics['total_carbon_gco2'],
        baseline_carbon_gco2=None,  # ECMR is the baseline
        avg_carbon_intensity=carbon_metrics['avg_carbon_intensity'],
        avg_renewable_pct=carbon_metrics['avg_renewable_pct']
    )

    # M5: Green DC Utilization
    if green_dc_util:
        metrics.compute_m5_green_dc_utilization(
            green_dc_vms=green_dc_util['green_dc_vms'],
            brown_dc_vms=green_dc_util['brown_dc_vms']
        )

    metrics.raw_data = raw_data
    return metrics, raw_data


def extract_overall_statistics(text: str) -> Dict:
    """Extract overall statistics section"""
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


def extract_carbon_metrics(text: str) -> Dict:
    """Extract carbon and renewable metrics"""
    carbon = {}

    # Total carbon in kg CO2
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


def extract_datacenter_stats(text: str) -> Dict[str, Dict]:
    """
    Extract per-datacenter statistics including CPU/RAM utilization
    Returns: {datacenter_id: {stats_dict}}
    """
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

    # Split by datacenter entries (look for DC_XXXXX patterns)
    dc_entries = re.split(r'\n\s+(DC_\w+)\s+\(', dc_section)

    for i in range(1, len(dc_entries), 2):
        if i + 1 >= len(dc_entries):
            break

        dc_id = dc_entries[i]
        dc_content = dc_entries[i + 1]

        stats = {}

        # Extract VMs placed
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


def extract_vm_distribution(text: str) -> Dict:
    """Extract VM type distribution"""
    vm_dist = {'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0}

    # Find VM TYPE DISTRIBUTION section
    vm_section_match = re.search(
        r'VM TYPE DISTRIBUTION\s*-+\s*(.*?)(?=\n\s*DATACENTER SELECTION|\n\s*C-MORL|$)',
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


def extract_datacenter_selection(text: str) -> Dict:
    """Extract datacenter selection distribution"""
    dc_selection = {}

    # Find DATACENTER SELECTION DISTRIBUTION section
    dc_sel_match = re.search(
        r'DATACENTER SELECTION DISTRIBUTION\s*-+\s*(.*?)(?=\n\s*C-MORL|\n\s*M5:|$)',
        text,
        re.DOTALL
    )

    if not dc_sel_match:
        return dc_selection

    dc_sel_section = dc_sel_match.group(1)

    # Extract each datacenter
    dc_pattern = r'(DC_\w+)\s*:\s*(\d+)\s+\(([\d.]+)%\)'
    for match in re.finditer(dc_pattern, dc_sel_section):
        dc_id = match.group(1)
        vms = int(match.group(2))
        percentage = float(match.group(3))
        dc_selection[dc_id] = {'vms': vms, 'percentage': percentage}

    return dc_selection


def extract_green_dc_utilization(text: str) -> Dict:
    """
    Extract M5: Green Datacenter Utilization
    Looks for the M5 section that shows DG vs DB breakdown
    """
    green_util = {}

    # Find M5 section
    m5_match = re.search(
        r'M5:\s*GREEN DATACENTER UTILIZATION\s*-+\s*(.*?)(?=\n\s*PER-DATACENTER|\n\s*VM TYPE|$)',
        text,
        re.DOTALL | re.IGNORECASE
    )

    if not m5_match:
        # Fallback: try to extract from datacenter stats by inferring DC types
        return infer_green_dc_from_datacenter_stats(text)

    m5_section = m5_match.group(1)

    # Extract green and brown DC VMs
    green_match = re.search(r'Green Datacenter.*?VMs:\s+(\d+)', m5_section)
    brown_match = re.search(r'Brown Datacenter.*?VMs:\s+(\d+)', m5_section)

    if green_match and brown_match:
        green_util['green_dc_vms'] = int(green_match.group(1))
        green_util['brown_dc_vms'] = int(brown_match.group(1))
        green_util['total_vms'] = green_util['green_dc_vms'] + green_util['brown_dc_vms']
        green_util['green_utilization_pct'] = (
            green_util['green_dc_vms'] / max(green_util['total_vms'], 1) * 100
        )

    return green_util


def infer_green_dc_from_datacenter_stats(text: str) -> Dict:
    """
    Infer green vs brown DC usage from datacenter selection
    Assumption: Stockholm, Amsterdam are Green (DG), others are Brown (DB)
    This is a fallback if M5 section not found
    """
    dc_selection = extract_datacenter_selection(text)

    if not dc_selection:
        return {}

    # Define which DCs are green (this should match your datacenter configuration)
    # Based on renewable %, high renewable = green
    green_dcs = ['DC_STOCKHOLM', 'DC_AMSTERDAM']  # Typically high renewable

    green_vms = sum(dc_selection.get(dc, {}).get('vms', 0) for dc in green_dcs)
    total_vms = sum(data.get('vms', 0) for data in dc_selection.values())
    brown_vms = total_vms - green_vms

    return {
        'green_dc_vms': green_vms,
        'brown_dc_vms': brown_vms,
        'total_vms': total_vms,
        'green_utilization_pct': (green_vms / max(total_vms, 1) * 100)
    }


def compute_average_utilization(dc_stats: Dict, dc_selection: Dict) -> Tuple[float, float]:
    """
    Compute weighted average CPU and RAM utilization across all datacenters
    Weighted by number of VMs placed in each DC
    """
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


def compute_weighted_avg_latency(dc_stats: Dict, dc_selection: Dict) -> float:
    """
    Compute weighted average latency based on VMs placed in each DC
    Note: Latency should be extracted from placement decisions, this is approximate
    """
    if not dc_stats or not dc_selection:
        return 0.0

    total_vms = sum(data.get('vms', 0) for data in dc_selection.values())
    if total_vms == 0:
        return 0.0

    # Try to extract latency from datacenter stats
    weighted_latency = 0.0

    for dc_id, selection in dc_selection.items():
        vms = selection.get('vms', 0)
        if vms == 0:
            continue

        # Latency might be in the stats, or we estimate from location
        # For now, use a simple heuristic
        weight = vms / total_vms
        # Placeholder: extract actual latency if available in stats
        latency = 10.0  # Default latency
        weighted_latency += latency * weight

    return weighted_latency


def extract_runtime(text: str) -> float:
    """Extract actual runtime if available in output"""
    # Look for timing information in output
    runtime_match = re.search(r'Total runtime:\s+([\d.]+)\s+s', text, re.IGNORECASE)
    if runtime_match:
        return float(runtime_match.group(1))

    # Look for other timing patterns
    duration_match = re.search(r'Duration:\s+([\d.]+)\s+seconds', text, re.IGNORECASE)
    if duration_match:
        return float(duration_match.group(1))

    return None


if __name__ == "__main__":
    # Test the parser
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_ecmr_parser.py <ecmr_output.txt>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        output = f.read()

    metrics, raw_data = parse_ecmr_results(output)
    metrics.print_summary("ECMR ENHANCED PARSING TEST")

    print("\n" + "="*80)
    print("RAW DATA EXTRACTED:")
    print("="*80)
    import json
    print(json.dumps(raw_data, indent=2, default=str))
