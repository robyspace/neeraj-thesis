# Demo Quick Reference Card
## Print this and keep it visible during presentation!

---

## 🚀 Quick Start Commands

### Start Gateway (Background Terminal)
```bash
cd /Users/robyspace/Documents/GitHub/neeraj-thesis/cloudsim-baseline
java -cp target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar \
  com.ecmr.baseline.Py4JGatewayEnhanced &
```

### Run ECMR Demo
```bash
python3 ecmr_heterogeneous_integration.py
```

### Show C-MORL Results
```bash
ls -lh capacity_aware_comparison_24h/cmorl/stage1/
cat capacity_aware_comparison_24h/comparison_report.md
```

### Show Figures
```bash
open capacity_aware_comparison_24h/figures/
```

---

## 📊 Key Numbers to Remember

| Metric | ECMR | C-MORL |
|--------|------|--------|
| **Total Carbon** | 1958.1 gCO2 | 1958.2 gCO2 |
| **Total Energy** | 26.69 kWh | 26.69 kWh |
| **Runtime** | 0.42s | 327.9s |
| **Latency** | 0ms | 8-15ms |
| **Amsterdam** | 91/120 (76%) | 120/120 (100%) ✓ |
| **Pareto Solutions** | 1 | 2 ✓ |

---

## 💡 Key Messages

### Main Contribution:
> "Enhanced C-MORL with 5 capacity dimensions, enabling it to learn optimal datacenter utilization - 100% vs ECMR's 76%"

### Why Same Carbon?:
> "Both leverage Amsterdam (0 gCO2) effectively. Value is in HOW: C-MORL fills it completely, ECMR doesn't."

### Why 50% Fallback is Good:
> "120 VMs in Amsterdam (capacity), 120 overflow to Stockholm. That's 120/240 = 50%. Optimal!"

### When to Use Each:
- **ECMR:** Speed-critical, one-time, simple
- **C-MORL:** Recurring, multi-objective, capacity-critical

---

## 🎯 Presentation Flow (15 min)

| Time | Section | Key Point |
|------|---------|-----------|
| 0-2 | Intro | Problem: Cloud carbon emissions |
| 2-5 | Overview | 3 components: CloudSim, ECMR, C-MORL |
| 5-7 | ECMR Demo | Fast but misses optimization (91/120) |
| 7-10 | C-MORL | Learned 100% capacity utilization |
| 10-15 | Results | Same carbon, better capacity, Pareto |
| 15-18 | Contributions | 5 capacity dims, optimal learning |

---

## ❓ Top 3 Expected Questions

**Q: Why same carbon?**
A: Both use Amsterdam well. Difference is capacity optimization.

**Q: Why 50% fallback?**
A: 120/240 overflow from Amsterdam is optimal, proves learning.

**Q: Production ready?**
A: Train offline (5.5 min), deploy policy, fast inference.

---

## 🆘 Emergency Backup

If demo fails:
```bash
cat capacity_aware_comparison_24h/comparison_report.md
open capacity_aware_comparison_24h/figures/
tail -50 capacity_aware_comparison_24h/cmorl/training_log.txt
```

Say: "I ran this yesterday. Let me walk you through the results..."

---

## ✅ Pre-Demo Checklist

- [ ] Gateway running (check with `ps aux | grep java`)
- [ ] Terminal font size 16-18pt
- [ ] Notifications OFF
- [ ] comparison_report.md open
- [ ] Figures folder open
- [ ] This card printed and visible

---

**You've got this! 🎓**
