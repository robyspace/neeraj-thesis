#!/bin/bash

# Thesis Files Preparation Script
# This script copies all necessary files to a single folder for Claude Projects upload

THESIS_DIR="thesis_materials_for_claude"

echo "=================================================="
echo "Preparing Thesis Files for Claude Web Interface"
echo "=================================================="
echo ""

# Create main directory
mkdir -p "$THESIS_DIR"

# Create subdirectories
echo "Creating folder structure..."
mkdir -p "$THESIS_DIR/01_literature"
mkdir -p "$THESIS_DIR/02_code/python"
mkdir -p "$THESIS_DIR/02_code/java"
mkdir -p "$THESIS_DIR/02_code/documentation"
mkdir -p "$THESIS_DIR/03_data"
mkdir -p "$THESIS_DIR/04_results"
mkdir -p "$THESIS_DIR/05_analysis"
mkdir -p "$THESIS_DIR/06_figures"

echo "✓ Folder structure created"
echo ""

# 1. Literature (manual - user needs to copy their PDF)
echo "📚 LITERATURE:"
echo "   ⚠️  Please manually copy your literature review PDF to:"
echo "      $THESIS_DIR/01_literature/"
echo ""

# 2. Code - Python
echo "💻 Copying Python code..."
cp ecmr_heterogeneous_integration.py "$THESIS_DIR/02_code/python/" 2>/dev/null && echo "   ✓ ecmr_heterogeneous_integration.py"
cp train_cmorl.py "$THESIS_DIR/02_code/python/" 2>/dev/null && echo "   ✓ train_cmorl.py"
cp cmorl_agent.py "$THESIS_DIR/02_code/python/" 2>/dev/null && echo "   ✓ cmorl_agent.py"
cp cmorl_environment.py "$THESIS_DIR/02_code/python/" 2>/dev/null && echo "   ✓ cmorl_environment.py"
echo ""

# 2. Code - Java
echo "☕ Copying Java code..."
cp src/main/java/Main.java "$THESIS_DIR/02_code/java/" 2>/dev/null && echo "   ✓ Main.java"
cp src/main/java/GatewayServer.java "$THESIS_DIR/02_code/java/" 2>/dev/null && echo "   ✓ GatewayServer.java"
echo ""

# 2. Code - Documentation
echo "📖 Copying documentation..."
cp CODE_REFERENCE.md "$THESIS_DIR/02_code/documentation/" 2>/dev/null && echo "   ✓ CODE_REFERENCE.md"
cp DOCUMENTATION_INDEX.md "$THESIS_DIR/02_code/documentation/" 2>/dev/null && echo "   ✓ DOCUMENTATION_INDEX.md"
cp RUNNING_TESTING_GUIDE.md "$THESIS_DIR/02_code/documentation/" 2>/dev/null && echo "   ✓ RUNNING_TESTING_GUIDE.md"
cp TEST_SCENARIOS.md "$THESIS_DIR/02_code/documentation/" 2>/dev/null && echo "   ✓ TEST_SCENARIOS.md"
cp THESIS_PREPARATION_CHECKLIST.md "$THESIS_DIR/02_code/documentation/" 2>/dev/null && echo "   ✓ THESIS_PREPARATION_CHECKLIST.md"
echo ""

# 3. Data
echo "📊 Copying dataset..."
if [ -f "output/synchronized_dataset_2024.csv" ]; then
    # Copy only first 1000 lines to keep file size manageable
    head -1000 output/synchronized_dataset_2024.csv > "$THESIS_DIR/03_data/synchronized_dataset_2024_sample.csv"
    echo "   ✓ synchronized_dataset_2024_sample.csv (first 1000 lines)"
else
    echo "   ⚠️  Dataset not found: output/synchronized_dataset_2024.csv"
fi
echo ""

# 4. Results - Main comparison
echo "📈 Copying results..."
cp capacity_aware_comparison_24h/comparison_report.md "$THESIS_DIR/04_results/" 2>/dev/null && echo "   ✓ comparison_report.md"
cp capacity_aware_comparison_24h/ecmr/metrics.json "$THESIS_DIR/04_results/ecmr_metrics.json" 2>/dev/null && echo "   ✓ ecmr_metrics.json"
cp capacity_aware_comparison_24h/cmorl/solution_1_metrics.json "$THESIS_DIR/04_results/cmorl_solution_1_metrics.json" 2>/dev/null && echo "   ✓ cmorl_solution_1_metrics.json"
cp capacity_aware_comparison_24h/cmorl/solution_2_metrics.json "$THESIS_DIR/04_results/cmorl_solution_2_metrics.json" 2>/dev/null && echo "   ✓ cmorl_solution_2_metrics.json"
cp capacity_aware_comparison_24h/cmorl/final_results.json "$THESIS_DIR/04_results/cmorl_final_results.json" 2>/dev/null && echo "   ✓ cmorl_final_results.json"

# Training log (first 500 lines and last 500 lines to keep manageable)
if [ -f "capacity_aware_comparison_24h/cmorl/training_log.txt" ]; then
    echo "   ⓘ  Extracting training log summary (first 500 + last 500 lines)..."
    (head -500 capacity_aware_comparison_24h/cmorl/training_log.txt; echo ""; echo "... [middle section omitted for brevity] ..."; echo ""; tail -500 capacity_aware_comparison_24h/cmorl/training_log.txt) > "$THESIS_DIR/04_results/cmorl_training_log_summary.txt"
    echo "   ✓ cmorl_training_log_summary.txt"
fi
echo ""

# 5. Analysis
echo "🔬 Copying analysis..."
cp capacity_aware_comparison_24h/METRIC_COMPARISON_ANALYSIS.md "$THESIS_DIR/05_analysis/" 2>/dev/null && echo "   ✓ METRIC_COMPARISON_ANALYSIS.md"
echo ""

# 6. Figures
echo "🖼️  Checking for figures..."
FIGURE_COUNT=$(find capacity_aware_comparison_24h -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
if [ "$FIGURE_COUNT" -gt 0 ]; then
    cp capacity_aware_comparison_24h/*.png "$THESIS_DIR/06_figures/" 2>/dev/null
    echo "   ✓ Copied $FIGURE_COUNT PNG figures"
else
    echo "   ⚠️  No PNG figures found"
    echo "   ℹ️  You can generate figures from JSON data in Claude web interface"
fi
echo ""

# Create README for the thesis materials folder
cat > "$THESIS_DIR/README.md" << 'EOF'
# MSc Thesis Materials for Claude Projects

## Contents

This folder contains all materials needed for writing the thesis report in Claude web interface.

### 01_literature/
- Your literature review PDF (copy manually)

### 02_code/
- **python/**: Main algorithm implementations (ECMR, C-MORL, environment, agent)
- **java/**: CloudSim backend (Main.java, GatewayServer.java)
- **documentation/**: Code reference, testing guides, thesis checklist

### 03_data/
- Sample dataset (first 1000 lines of carbon intensity data)

### 04_results/
- Comparison report (markdown)
- ECMR metrics (JSON)
- C-MORL solution metrics (2 solutions, JSON)
- Training log summary (first + last 500 lines)
- Final Pareto front results

### 05_analysis/
- Detailed metric comparison analysis (M1-M5)
- Key insights and realizations
- Strengths/weaknesses comparison

### 06_figures/
- PNG visualizations (if generated)
- Generate additional figures in Claude using JSON data

## Upload Instructions

1. Go to claude.ai and create a new Project
2. Name it: "MSc Thesis - Carbon-Aware Cloud Scheduling"
3. Upload ALL files from this folder
4. Start with the initial prompt from THESIS_PREPARATION_CHECKLIST.md

## Key Numbers for Reference

- **Total VMs:** 240
- **Simulation:** 24 hours × 10 VMs/hour
- **Datacenters:** 5 European locations (120 VMs capacity each)
- **Total Energy:** ~26.69 kWh (both algorithms)
- **Total Carbon:** ~1958 gCO2 (both algorithms)
- **ECMR Runtime:** 0.42s
- **C-MORL Runtime:** 327.9s (5.5 min)
- **Pareto Front:** 2 solutions
- **State Space:** 137 dimensions
- **Neural Network:** 137→256→256→5

## Writing Tips

1. Reference files explicitly: "Based on cmorl_solution_1_metrics.json..."
2. Verify all numbers against source JSON files
3. Request section-by-section writing (don't write entire thesis at once)
4. Ask Claude to generate figures from JSON data
5. Maintain academic tone and technical precision

Good luck with your thesis!
EOF

echo "   ✓ README.md created"
echo ""

# Summary
echo "=================================================="
echo "PREPARATION COMPLETE!"
echo "=================================================="
echo ""
echo "Thesis materials prepared in: $THESIS_DIR/"
echo ""
echo "Next steps:"
echo "1. Copy your literature review PDF to $THESIS_DIR/01_literature/"
echo "2. Review the contents of $THESIS_DIR/"
echo "3. Upload all files to Claude Projects at claude.ai"
echo "4. Follow instructions in THESIS_PREPARATION_CHECKLIST.md"
echo ""
echo "Files prepared:"
du -sh "$THESIS_DIR"
echo ""
echo "Folder contents:"
find "$THESIS_DIR" -type f | sed 's|'$THESIS_DIR'/||' | sort
echo ""
echo "✅ Ready for Claude web interface!"
