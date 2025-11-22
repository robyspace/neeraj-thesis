package com.ecmr.baseline;

/**
 * VM instance types from Miao2024.pdf Table 5
 * Defines the four heterogeneous VM configurations
 */
public enum VMType {
    /**
     * Small VM instance
     * 1 core, 2 GB RAM, 250 GB storage
     * Clock: 0.5 GHz, Bandwidth: 0.8 Gbps
     */
    SMALL(
        "small",
        1,              // CPU cores
        2 * 1024,       // 2 GB RAM in MB
        250 * 1024,     // 250 GB storage in MB
        500,            // 0.5 GHz = 500 MIPS per core
        800             // 0.8 Gbps bandwidth in Mbps
    ),

    /**
     * Medium VM instance
     * 2 cores, 4 GB RAM, 500 GB storage
     * Clock: 1.0 GHz, Bandwidth: 1.5 Gbps
     */
    MEDIUM(
        "medium",
        2,              // CPU cores
        4 * 1024,       // 4 GB RAM in MB
        500 * 1024,     // 500 GB storage in MB
        1000,           // 1.0 GHz = 1000 MIPS per core
        1500            // 1.5 Gbps bandwidth in Mbps
    ),

    /**
     * Large VM instance
     * 4 cores, 8 GB RAM, 750 GB storage
     * Clock: 1.5 GHz, Bandwidth: 2 Gbps
     */
    LARGE(
        "large",
        4,              // CPU cores
        8 * 1024,       // 8 GB RAM in MB
        750 * 1024,     // 750 GB storage in MB
        1500,           // 1.5 GHz = 1500 MIPS per core
        2000            // 2 Gbps bandwidth in Mbps
    ),

    /**
     * Extra-large VM instance
     * 8 cores, 16 GB RAM, 1000 GB storage
     * Clock: 2.0 GHz, Bandwidth: 3 Gbps
     */
    XLARGE(
        "xlarge",
        8,              // CPU cores
        16 * 1024,      // 16 GB RAM in MB
        1000 * 1024,    // 1000 GB (1 TB) storage in MB
        2000,           // 2.0 GHz = 2000 MIPS per core
        3000            // 3 Gbps bandwidth in Mbps
    );

    private final String name;
    private final int numCores;
    private final long ramMB;
    private final long storageMB;
    private final long mipsPerCore;
    private final long bandwidthMbps;

    VMType(String name, int numCores, long ramMB, long storageMB,
           long mipsPerCore, long bandwidthMbps) {
        this.name = name;
        this.numCores = numCores;
        this.ramMB = ramMB;
        this.storageMB = storageMB;
        this.mipsPerCore = mipsPerCore;
        this.bandwidthMbps = bandwidthMbps;
    }

    public String getName() { return name; }
    public int getNumCores() { return numCores; }
    public long getRamMB() { return ramMB; }
    public long getStorageMB() { return storageMB; }
    public long getMipsPerCore() { return mipsPerCore; }
    public long getTotalMips() { return numCores * mipsPerCore; }
    public long getBandwidthMbps() { return bandwidthMbps; }

    @Override
    public String toString() {
        return String.format("%s [%d cores @ %d MIPS, %d MB RAM, %d MB storage, %d Mbps BW]",
                name, numCores, mipsPerCore, ramMB, storageMB, bandwidthMbps);
    }

    /**
     * Get VM type by name (for Python integration)
     */
    public static VMType fromString(String name) {
        for (VMType type : VMType.values()) {
            if (type.getName().equalsIgnoreCase(name)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown VM type: " + name);
    }
}
