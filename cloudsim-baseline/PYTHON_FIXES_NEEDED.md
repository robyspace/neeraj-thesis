# Python Fixes for ecmr_cloudsim_complete.py

## Issues to Fix

### Issue 1: All VMs Processed in One Hour
**Current**: All 50 VMs processed in hour 0
**Needed**: Distribute across multiple hours

### Issue 2: No Detailed Datacenter Evaluation
**Current**: Only shows which DC was selected
**Needed**: Show all 5 DCs with scores, rejection reasons

### Issue 3: No Per-Hour Visibility
**Current**: Only final summary
**Needed**: Show placement decisions hour-by-hour

---

## Required Changes to `ecmr_cloudsim_complete.py`

### Change 1: Add VM-per-Hour Limit (Line ~820)

**Insert after line 820**:
```python
def run_complete_simulation(self, data_path, max_vms=100, vms_per_hour=10):
    """
    Run complete simulation with:
    - VM distribution across hours (NEW: vms_per_hour parameter)
    - ALL CSV data usage
    - Full ECMR algorithm
    - M1-M4 metrics
    """
```

**Modify VM processing loop (Line ~886)**:
```python
# CHANGED: Limit VMs per hour for temporal distribution
vms_this_hour = min(
    int(row['vm_arrivals']),
    vms_per_hour,  # NEW: Max 10 VMs per hour
    max_vms - vm_count
)
```

### Change 2: Track All DC Evaluations in schedule_vm() (Line ~418)

**Replace the schedule_vm() method starting at line 418**:

```python
def schedule_vm(self, vm: Dict, current_time: datetime) -> Tuple[Optional[str], bool, Dict]:
    """
    Enhanced ECMR scheduling with ALL datacenter evaluation tracking
    """
    self.metrics['total_vms'] += 1

    # NEW: Evaluate ALL datacenters and track details
    all_dc_evaluations = []

    dg_datacenters, db_datacenters = self.classify_datacenters()
    dg_datacenters = self.sort_dg_by_distance(dg_datacenters)

    # Evaluate ALL datacenters (both green and brown)
    for dc in list(dg_datacenters) + list(db_datacenters):
        distance_km = self.calculate_distance(dc)
        latency_ms = distance_km * 0.1

        evaluation = {
            'datacenter_id': dc.id,
            'datacenter_name': dc.name,
            'datacenter_type': dc.datacenter_type,
            'distance_km': round(distance_km, 2),
            'latency_ms': round(latency_ms, 2),
            'carbon_intensity': round(dc.carbon_intensity_gco2_kwh, 2),
            'renewable_pct': round(dc.renewable_pct, 1),
            'renewable_mw': round(dc.renewable_generation_mw, 1),
            'can_host': dc.can_host_vm(vm),
            'latency_ok': latency_ms <= self.latency_threshold_ms,
            'res_ok': None,
            'weighted_score': None,
            'selected': False,
            'rejection_reason': []
        }

        # Check RES for green DCs
        if dc.datacenter_type == 'DG':
            evaluation['res_ok'] = self.check_res_availability(dc, vm)
        else:
            evaluation['res_ok'] = True  # Brown DCs don't need RES

        # Determine if this DC is a candidate
        if not evaluation['can_host']:
            evaluation['rejection_reason'].append('insufficient_capacity')
        if not evaluation['latency_ok']:
            evaluation['rejection_reason'].append(f'latency>{self.latency_threshold_ms}ms')
        if not evaluation['res_ok']:
            evaluation['rejection_reason'].append('insufficient_RES')

        # Calculate score if all constraints pass
        if evaluation['can_host'] and evaluation['latency_ok'] and evaluation['res_ok']:
            evaluation['weighted_score'] = round(self.calculate_weighted_score(dc, vm), 4)
        else:
            evaluation['weighted_score'] = None

        all_dc_evaluations.append(evaluation)

    # Select best datacenter from candidates
    candidates = [e for e in all_dc_evaluations if e['weighted_score'] is not None]

    if candidates:
        # Sort by score (lower is better)
        candidates.sort(key=lambda x: x['weighted_score'])
        best = candidates[0]

        # Mark as selected
        for e in all_dc_evaluations:
            if e['datacenter_id'] == best['datacenter_id']:
                e['selected'] = True
                break

        # Allocate VM
        dc = self.datacenters[best['datacenter_id']]
        dc.allocate_vm(vm)

        self.metrics['placed_vms'] += 1
        self.metrics['total_response_time_ms'] += best['latency_ms']

        decision = {
            'vm_id': vm['vm_id'],
            'selected_datacenter': best['datacenter_id'],
            'datacenter_type': best['datacenter_type'],
            'all_dc_evaluations': all_dc_evaluations,  # NEW: Full evaluation
            'timestamp': current_time.isoformat(),
            'success': True
        }

        self.metrics['placement_decisions'].append(decision)
        return best['datacenter_id'], True, decision

    # No suitable DC found
    self.metrics['failed_vms'] += 1

    decision = {
        'vm_id': vm['vm_id'],
        'selected_datacenter': None,
        'all_dc_evaluations': all_dc_evaluations,  # NEW: Show why all rejected
        'timestamp': current_time.isoformat(),
        'success': False
    }

    self.metrics['placement_decisions'].append(decision)
    return None, False, decision
```

### Change 3: Add Hourly Summary Method (Insert after line ~600)

```python
def print_hourly_placement_summary(self, hour_idx: int):
    """Print placement summary for the last hour"""

    # Get recent decisions (last 10 for this hour)
    recent_decisions = self.metrics['placement_decisions'][-10:]
    if not recent_decisions:
        return

    print(f"\n  Hour {hour_idx} Placement Summary:")
    print(f"  {'-'*76}")

    # Count placements this hour
    dc_counts = defaultdict(int)
    for d in recent_decisions:
        if d.get('success'):
            dc_counts[d['selected_datacenter']] += 1

    # Show distribution
    if dc_counts:
        for dc_id in sorted(dc_counts.keys()):
            dc = self.datacenters[dc_id]
            count = dc_counts[dc_id]
            print(f"    {dc_id} [{dc.datacenter_type}]: {count} VMs | "
                  f"Renewable: {dc.renewable_pct:.1f}% | "
                  f"Carbon: {dc.carbon_intensity_gco2_kwh:.0f} gCO2/kWh")

    # Show one detailed example
    if recent_decisions and recent_decisions[0].get('all_dc_evaluations'):
        example = recent_decisions[0]
        print(f"\n    Sample Decision (VM {example['vm_id']}):")
        for eval in example['all_dc_evaluations']:
            status = "✓ SELECTED" if eval.get('selected') else (
                "✗ " + (', '.join(eval.get('rejection_reason', [])) if eval.get('rejection_reason') else "not best")
            )
            score_str = f"{eval['weighted_score']:.4f}" if eval['weighted_score'] is not None else "N/A    "
            print(f"      {eval['datacenter_id']:6} [{eval['datacenter_type']}]: "
                  f"Score={score_str} | Lat={eval['latency_ms']:5.1f}ms | "
                  f"C={eval['carbon_intensity']:3.0f}g | R={eval['renewable_pct']:4.1f}% | {status}")
```

### Change 4: Call Hourly Summary in Loop (Line ~924)

**Insert after line 924** (after `calculate_hourly_metrics()`):

```python
# Calculate hourly metrics
self.scheduler.calculate_hourly_metrics()
hours_processed += 1

# NEW: Print hourly summary every hour
if vms_this_hour > 0:
    self.scheduler.print_hourly_placement_summary(hours_processed)
```

### Change 5: Add Per-DC Statistics to Results (Line ~950+)

**Add new method in ECMRCloudSimComplete class**:

```python
def print_per_datacenter_statistics(self):
    """Print detailed per-datacenter statistics"""
    print("\nPER-DATACENTER PLACEMENT STATISTICS:")
    print("-"*80)

    for dc in self.datacenters:
        # Find all VMs placed in this DC
        vms_here = [d for d in self.scheduler.metrics['placement_decisions']
                    if d.get('selected_datacenter') == dc.id and d.get('success')]

        print(f"\n  {dc.id} - {dc.name} ({dc.country}):")

        if vms_here:
            # Calculate statistics when this DC was selected
            carbon_values = []
            renewable_values = []

            for decision in vms_here:
                for eval in decision.get('all_dc_evaluations', []):
                    if eval['datacenter_id'] == dc.id:
                        carbon_values.append(eval['carbon_intensity'])
                        renewable_values.append(eval['renewable_pct'])
                        break

            print(f"    VMs placed: {len(vms_here)}")
            if carbon_values:
                print(f"    Avg carbon when selected: {np.mean(carbon_values):.1f} gCO2/kWh")
                print(f"    Avg renewable when selected: {np.mean(renewable_values):.1f}%")
            print(f"    Final classification: {dc.datacenter_type}")
        else:
            print(f"    VMs placed: 0")
            print(f"    Reason: Not selected (check constraint violations)")
```

### Change 6: Update main() to Use New Parameters (Line ~1050)

```python
def main():
    parser = argparse.ArgumentParser(description='ECMR-CloudSim Complete Integration')
    parser.add_argument('--data', required=True, help='Synchronized dataset CSV')
    parser.add_argument('--max-vms', type=int, default=100, help='Max VMs to simulate')
    parser.add_argument('--vms-per-hour', type=int, default=10, help='Max VMs per hour')  # NEW
    parser.add_argument('--output', default='ecmr_cloudsim_complete_results.json',
                       help='Output JSON file')

    args = parser.parse_args()

    try:
        integration = ECMRCloudSimComplete()
        integration.initialize()
        integration.create_datacenters_with_ecmr()

        # Run with vms-per-hour limit
        placements = integration.run_complete_simulation(
            args.data,
            args.max_vms,
            args.vms_per_hour  # NEW parameter
        )

        results = integration.get_complete_results()

        # NEW: Add per-DC statistics
        integration.print_per_datacenter_statistics()

        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n✓ Results saved to: {args.output}")
        print("✓ ECMR-CloudSim complete integration finished successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0
```

---

## Expected Output After Fixes

```
Hour 1 Placement Summary:
  DC_SE [DG]: 4 VMs | Renewable: 67.3% | Carbon: 24 gCO2/kWh
  DC_DE [DG]: 6 VMs | Renewable: 79.2% | Carbon: 145 gCO2/kWh

  Sample Decision (VM 0):
    DC_IT  [DB]: Score=0.4563 | Lat= 47.8ms | C=232g | R=43.1% | ✗ high_carbon, not best
    DC_SE  [DG]: Score=0.2145 | Lat= 65.4ms | C= 24g | R=67.3% | ✗ not best
    DC_ES  [DG]: Score=0.3894 | Lat= 88.2ms | C= 77g | R=51.1% | ✗ not best
    DC_FR  [DB]: Score=0.3341 | Lat= 23.5ms | C= 16g | R=32.9% | ✗ not best
    DC_DE  [DG]: Score=0.1987 | Lat= 47.8ms | C=144g | R=79.4% | ✓ SELECTED

Hour 2 Placement Summary:
  DC_FR [DB]: 3 VMs | Renewable: 32.1% | Carbon: 15 gCO2/kWh
  DC_SE [DG]: 7 VMs | Renewable: 68.9% | Carbon: 22 gCO2/kWh

---

Total VMs processed: 100
Total hours simulated: 10

PER-DATACENTER PLACEMENT STATISTICS:

  DC_IT - Milan Datacenter (italy):
    VMs placed: 8
    Avg carbon when selected: 245.3 gCO2/kWh
    Avg renewable when selected: 41.2%

  DC_SE - Stockholm Datacenter (sweden):
    VMs placed: 42  ← Most selected (low carbon!)
    Avg carbon when selected: 25.1 gCO2/kWh
    Avg renewable when selected: 67.8%

  DC_ES - Madrid Datacenter (spain):
    VMs placed: 15
    Avg carbon when selected: 78.4 gCO2/kWh
    Avg renewable when selected: 52.3%

  DC_FR - Paris Datacenter (france):
    VMs placed: 18
    Avg carbon when selected: 15.8 gCO2/kWh
    Avg renewable when selected: 33.1%

  DC_DE - Frankfurt Datacenter (germany):
    VMs placed: 17
    Avg carbon when selected: 142.3 gCO2/kWh
    Avg renewable when selected: 79.6%
```

---

## How to Apply Changes

1. **Restart Gateway** (in Terminal 1):
```bash
# Kill old gateway
pkill -f Py4JGateway

# Start new gateway with updated JAR
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGateway
```

2. **Apply Python changes** to `ecmr_cloudsim_complete.py`:
- Follow the 6 changes above
- OR create a new file `ecmr_cloudsim_complete_v2.py` with all fixes

3. **Test** (in Terminal 2):
```bash
python3 src/main/python/ecmr_cloudsim_complete.py \
  --data output/synchronized_dataset_2024.csv \
  --max-vms 100 \
  --vms-per-hour 10
```

---

## Success Criteria

After applying fixes, you should see:

✅ VMs distributed across ~10 hours (not just 1 hour)
✅ All 5 datacenters receive some VMs
✅ Both DG and DB datacenters used
✅ Hourly summaries showing different DC selections per hour
✅ Detailed per-VM decisions showing all 5 DCs evaluated
✅ Per-datacenter statistics at the end
✅ CloudSim VM count closer to ECMR count
