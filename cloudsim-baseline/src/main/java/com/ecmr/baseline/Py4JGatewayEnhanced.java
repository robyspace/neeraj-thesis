package com.ecmr.baseline;

import py4j.GatewayServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.HashMap;

/**
 * Enhanced Py4J Gateway supporting heterogeneous server infrastructure
 * Exposes ECMRSimulationEnhanced to Python via Py4J
 */
public class Py4JGatewayEnhanced {
    private static final Logger logger = LoggerFactory.getLogger(Py4JGatewayEnhanced.class);
    private GatewayServer gatewayServer;
    private ECMRSimulationEnhanced simulation;

    public Py4JGatewayEnhanced() {
        this.simulation = new ECMRSimulationEnhanced();
    }

    /**
     * Start the Py4J Gateway Server
     */
    public void startGateway() {
        try {
            gatewayServer = new GatewayServer(this);
            gatewayServer.start();
            logger.info("Enhanced Py4J Gateway Server started on port 25333");
            logger.info("Python can connect using: gateway = JavaGateway()");
        } catch (Exception e) {
            logger.error("Failed to start Gateway: {}", e.getMessage(), e);
            throw new RuntimeException("Gateway startup failed", e);
        }
    }

    /**
     * Stop the Gateway Server
     */
    public void stopGateway() {
        if (gatewayServer != null) {
            gatewayServer.shutdown();
            logger.info("Gateway Server stopped");
        }
    }

    /**
     * Initialize CloudSim simulation
     */
    public void initializeSimulation(Map<String, Object> config) {
        logger.info("Initializing simulation with config: {}", config);
        simulation.initialize(config);
    }

    /**
     * Initialize CloudSim simulation (no config needed)
     */
    public void initializeSimulation() {
        logger.info("Initializing simulation");
        simulation.initialize();
    }

    /**
     * Create heterogeneous datacenter (RECOMMENDED)
     * @param id Datacenter ID (e.g., "DC_ITALY")
     * @param serversPerType Number of servers of each type (typically 40)
     * @param pue Power Usage Effectiveness
     */
    public String createHeterogeneousDatacenter(String id, int serversPerType, double pue) {
        logger.info("Creating heterogeneous datacenter: {} ({} servers/type, PUE: {})",
                    id, serversPerType, pue);
        return simulation.createHeterogeneousDatacenter(id, serversPerType, pue);
    }

    /**
     * Create datacenter with simple config (backward compatibility)
     */
    public String createDatacenter(String id, int numServers, int cpuPerServer,
                                   int ramPerServerMB, double powerIdleW, double powerMaxW) {
        return simulation.createDatacenter(id, numServers, cpuPerServer,
                                          ramPerServerMB, powerIdleW, powerMaxW);
    }

    /**
     * Submit VM using predefined VM type (RECOMMENDED)
     * @param vmId VM identifier
     * @param vmType VM type: "small", "medium", "large", or "xlarge"
     * @param targetDatacenterId Target datacenter (e.g., "DC_ITALY")
     */
    public boolean submitVMByType(int vmId, String vmType, String targetDatacenterId) {
        try {
            VMType type = VMType.fromString(vmType);
            return simulation.submitVMByType(vmId, type, targetDatacenterId);
        } catch (IllegalArgumentException e) {
            logger.error("Invalid VM type: {}", vmType, e);
            return false;
        }
    }

    /**
     * Submit VM with custom specifications
     */
    public boolean submitVMToDatacenter(int vmId, int cpus, int ramMB, int mips,
                                       String targetDatacenterId) {
        return simulation.submitVMToDatacenter(vmId, cpus, ramMB, mips, targetDatacenterId);
    }

    /**
     * Submit VM without datacenter specification (CloudSim auto-placement)
     */
    public boolean submitVM(int vmId, int cpus, int ramMB, int mips) {
        return simulation.submitVM(vmId, cpus, ramMB, mips);
    }

    /**
     * Run the simulation
     */
    public void runSimulation() {
        logger.info("Running CloudSim simulation...");
        simulation.run();
        logger.info("Simulation completed");
    }

    /**
     * Get simulation results (includes PUE-adjusted energy)
     */
    public Map<String, Object> getResults() {
        return simulation.getResults();
    }

    /**
     * Get datacenter statistics
     */
    public Map<String, Object> getDatacenterStats(String datacenterId) {
        return simulation.getDatacenterStats(datacenterId);
    }

    /**
     * Get VM placement decisions
     */
    public List<Map<String, Object>> getPlacementDecisions() {
        return simulation.getPlacementDecisions();
    }

    /**
     * Main method to start gateway
     */
    public static void main(String[] args) {
        logger.info("=".repeat(80));
        logger.info("ECMR Enhanced - Py4J Gateway Server");
        logger.info("Server Models: Huawei RH2285 V2, RH2288H V3, Lenovo SR655 V3");
        logger.info("VM Types: small, medium, large, xlarge");
        logger.info("=".repeat(80));

        Py4JGatewayEnhanced gateway = new Py4JGatewayEnhanced();
        gateway.startGateway();

        logger.info("\nGateway running. Python can now connect.");
        logger.info("Press Ctrl+C to stop.\n");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("\nShutting down gateway...");
            gateway.stopGateway();
        }));

        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            logger.error("Gateway interrupted", e);
        }
    }
}
