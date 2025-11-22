package com.ecmr.baseline;

/**
 * Server specifications from Miao2024.pdf Table 3
 * Represents the three heterogeneous server types used in the datacenter
 */
public enum ServerType {
    /**
     * Huawei RH2285 V2
     * CPU: Intel Xeon E5-2470, 2*8 cores = 16 cores
     * RAM: 24 GB
     * Clock: 2.3 GHz
     * Bandwidth: 25 Gbps
     */
    HUAWEI_RH2285_V2(
        "Huawei RH2285 V2",
        16,                    // Total cores (2 CPUs × 8 cores)
        24 * 1024,             // 24 GB RAM in MB
        2300,                  // 2.3 GHz = 2300 MIPS per core
        25000,                 // 25 Gbps bandwidth in Mbps
        1024 * 1024,           // 1 TB storage in MB (1024 * 1024 = 1,048,576 MB)
        new double[] {51, 72.5, 81.9, 92, 101, 114, 133, 154, 178, 218, 241} // Power profile from Table 4
    ),

    /**
     * Huawei RH2288H V3
     * CPU: Intel Xeon E5-2698 V4, 2*20 cores = 40 cores
     * RAM: 64 GB
     * Clock: 3.6 GHz
     * Bandwidth: 25 Gbps
     */
    HUAWEI_RH2288H_V3(
        "Huawei RH2288H V3",
        40,                    // Total cores (2 CPUs × 20 cores)
        64 * 1024,             // 64 GB RAM in MB
        3600,                  // 3.6 GHz = 3600 MIPS per core
        25000,                 // 25 Gbps bandwidth in Mbps
        1024 * 1024,           // 1 TB storage in MB (1024 * 1024 = 1,048,576 MB)
        new double[] {43.5, 83.7, 101, 117, 131, 145, 164, 187, 228, 277, 329} // Power profile from Table 4
    ),

    /**
     * Lenovo SR655 V3
     * CPU: AMD EPYC 9654, 1*96 cores = 96 cores
     * RAM: 192 GB
     * Clock: 2.4 GHz
     * Bandwidth: 25 Gbps
     */
    LENOVO_SR655_V3(
        "Lenovo SR655 V3",
        96,                    // Total cores (1 CPU × 96 cores)
        192 * 1024,            // 192 GB RAM in MB
        2400,                  // 2.4 GHz = 2400 MIPS per core
        25000,                 // 25 Gbps bandwidth in Mbps
        1024 * 1024,           // 1 TB storage in MB (1024 * 1024 = 1,048,576 MB)
        new double[] {63.2, 124, 145, 166, 186, 206, 227, 244, 280, 308, 351} // Power profile from Table 4
    );

    private final String modelName;
    private final int numCores;
    private final long ramMB;
    private final long mipsPerCore;
    private final long bandwidthMbps;
    private final long storageMB;

    /**
     * Power consumption at different load levels (0%, 10%, 20%, ..., 100%)
     * From Miao2024.pdf Table 4 - SpecPower benchmark results
     */
    private final double[] powerConsumptionWatts; // 11 values for 0%, 10%, 20%, ..., 100%

    ServerType(String modelName, int numCores, long ramMB, long mipsPerCore,
               long bandwidthMbps, long storageMB, double[] powerConsumptionWatts) {
        this.modelName = modelName;
        this.numCores = numCores;
        this.ramMB = ramMB;
        this.mipsPerCore = mipsPerCore;
        this.bandwidthMbps = bandwidthMbps;
        this.storageMB = storageMB;
        this.powerConsumptionWatts = powerConsumptionWatts;
    }

    public String getModelName() { return modelName; }
    public int getNumCores() { return numCores; }
    public long getRamMB() { return ramMB; }
    public long getMipsPerCore() { return mipsPerCore; }
    public long getBandwidthMbps() { return bandwidthMbps; }
    public long getStorageMB() { return storageMB; }

    /**
     * Get power consumption at specific load percentage
     * Uses linear interpolation between the 11 measured points
     *
     * @param loadPercentage CPU load (0.0 to 1.0)
     * @return Power consumption in Watts
     */
    public double getPowerAtLoad(double loadPercentage) {
        // Clamp to valid range
        loadPercentage = Math.max(0.0, Math.min(1.0, loadPercentage));

        // Convert to index (0.0 -> 0, 0.1 -> 1, ..., 1.0 -> 10)
        double index = loadPercentage * 10.0;
        int lowerIndex = (int) Math.floor(index);
        int upperIndex = (int) Math.ceil(index);

        // Handle edge case
        if (upperIndex >= powerConsumptionWatts.length) {
            return powerConsumptionWatts[powerConsumptionWatts.length - 1];
        }

        // Linear interpolation between two points
        if (lowerIndex == upperIndex) {
            return powerConsumptionWatts[lowerIndex];
        }

        double fraction = index - lowerIndex;
        double lowerPower = powerConsumptionWatts[lowerIndex];
        double upperPower = powerConsumptionWatts[upperIndex];

        return lowerPower + fraction * (upperPower - lowerPower);
    }

    /**
     * Get idle power (0% load)
     */
    public double getIdlePower() {
        return powerConsumptionWatts[0];
    }

    /**
     * Get maximum power (100% load)
     */
    public double getMaxPower() {
        return powerConsumptionWatts[powerConsumptionWatts.length - 1];
    }

    @Override
    public String toString() {
        return String.format("%s [%d cores @ %d MIPS, %d MB RAM, Idle: %.1fW, Max: %.1fW]",
                modelName, numCores, mipsPerCore, ramMB, getIdlePower(), getMaxPower());
    }
}
