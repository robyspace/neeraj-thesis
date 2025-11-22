package com.ecmr.baseline;

import org.cloudsimplus.hosts.Host;
import org.cloudsimplus.power.PowerMeasurement;
import org.cloudsimplus.power.models.PowerModelHost;

/**
 * Custom power model using the detailed power consumption profiles from Miao2024.pdf Table 4
 * Implements NON-LINEAR power consumption based on SpecPower benchmark results
 *
 * CRITICAL: This does NOT use simple linear interpolation like PowerModelHostSimple.
 * Instead, it uses the actual 11-point power consumption curves from SpecPower benchmarks.
 *
 * Example (Huawei RH2285 V2 at 50% load):
 * - Linear model: 146.0W (idle + 0.5 × (max - idle))
 * - Our model: 114.0W (interpolated from Table 4)
 * - Difference: 22% error with linear model!
 */
public class ServerPowerModel implements PowerModelHost {
    private ServerType serverType;
    private Host host;

    public ServerPowerModel(ServerType serverType) {
        this.serverType = serverType;
    }

    /**
     * Get power consumption for a given utilization fraction
     * Uses non-linear interpolation between 11 measured points from Table 4
     */
    @Override
    public double getPower(double utilizationFraction) throws IllegalArgumentException {
        // Use the 11-point lookup table with interpolation
        return serverType.getPowerAtLoad(utilizationFraction);
    }

    /**
     * Get current power consumption based on host's actual utilization
     * This is called by CloudSim during simulation
     */
    @Override
    public double getPower() throws IllegalArgumentException {
        if (host == null) {
            return serverType.getIdlePower();
        }

        // Calculate actual CPU utilization across all PEs
        double totalMips = host.getTotalMipsCapacity();
        double allocatedMips = host.getTotalAllocatedMips();

        double utilization = totalMips > 0 ? (allocatedMips / totalMips) : 0.0;

        return getPower(utilization);
    }

    @Override
    public Host getHost() {
        return host;
    }

    @Override
    public PowerModelHost setHost(Host host) {
        this.host = host;
        return this;
    }

    // Startup/Shutdown methods - not used in this model
    @Override
    public PowerModelHost setStartupPower(double power) {
        return this;
    }

    @Override
    public PowerModelHost setShutDownPower(double power) {
        return this;
    }

    @Override
    public double getStartupPower() {
        return 0;
    }

    @Override
    public double getShutDownPower() {
        return 0;
    }

    @Override
    public double getTotalStartupPower() {
        return 0;
    }

    @Override
    public double getTotalShutDownPower() {
        return 0;
    }

    @Override
    public double getTotalStartupTime() {
        return 0;
    }

    @Override
    public double getTotalShutDownTime() {
        return 0;
    }

    @Override
    public int getTotalStartups() {
        return 0;
    }

    // Required by PowerModelHost interface
    public void addShutDownTotals() {
        // Not used in this model - no shutdown tracking
    }

    public void addStartupTotals() {
        // Not used in this model - no startup tracking
    }

    @Override
    public PowerMeasurement getPowerMeasurement() {
        double staticPower = serverType.getIdlePower();
        double currentPower = getPower();
        double dynamicPower = currentPower - staticPower;
        return new PowerMeasurement(staticPower, dynamicPower);
    }

    @Override
    public String toString() {
        return String.format("ServerPowerModel[%s, Idle=%.1fW, Max=%.1fW, Current=%.1fW]",
                serverType.getModelName(),
                serverType.getIdlePower(),
                serverType.getMaxPower(),
                getPower());
    }
}
