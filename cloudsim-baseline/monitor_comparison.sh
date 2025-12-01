#!/bin/bash
echo "Starting comparison monitor..."
echo ""

while true; do
    # Check if process is still running
    if ! ps -p 10857 > /dev/null 2>&1; then
        echo "$(date '+%H:%M:%S') - ✓ Comparison process completed!"
        break
    fi
    
    # Count policies
    STAGE1_POLICIES=$(ls capacity_aware_comparison_24h/cmorl/stage1/*.pt 2>/dev/null | wc -l | tr -d ' ')
    
    # Check stage 2
    if [ -d "capacity_aware_comparison_24h/cmorl/stage2" ]; then
        STAGE2_FILES=$(ls capacity_aware_comparison_24h/cmorl/stage2/*.pt 2>/dev/null | wc -l | tr -d ' ')
        echo "$(date '+%H:%M:%S') - Stage 1: $STAGE1_POLICIES/3 | Stage 2: $STAGE2_FILES policies"
    else
        echo "$(date '+%H:%M:%S') - Stage 1: $STAGE1_POLICIES/3 policies trained"
    fi
    
    # Check for final results
    if [ -f "capacity_aware_comparison_24h/comparison_report.txt" ]; then
        echo "$(date '+%H:%M:%S') - ✓ Final comparison report generated!"
        break
    fi
    
    sleep 120  # Check every 2 minutes
done

echo ""
echo "=================================================="
echo "COMPARISON COMPLETE!"
echo "=================================================="
ls -lh capacity_aware_comparison_24h/ | grep -E "\.txt|\.json|\.png"
