package com.ecmr.baseline;

import py4j.GatewayServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.util.HashMap;

/**
 * Py4J Gateway for Java-Python communication
 * Allows Python scripts to interact with CloudSimPlus
 */
public class Py4JGateway {
    private static final Logger logger = LoggerFactory.getLogger(Py4JGateway.class);
    private GatewayServer gatewayServer;
    private ECMRSimulation simulation;
    
    public Py4JGateway() {
        this.simulation = new ECMRSimulation();
    }
    
    /**
     * Start the Py4J Gateway Server
     */
    public void startGateway() {
        try {
            gatewayServer = new GatewayServer(this);
            gatewayServer.start();
            logger.info("Py4J Gateway Server started on port 25333");
            logger.info("Python can now connect using: gateway = JavaGateway()");
        } catch (Exception e) {
            logger.error("Failed to start Py4J Gateway: {}", e.getMessage(), e);
            throw new RuntimeException("Gateway startup failed", e);
        }
    }
    
    /**
     * Stop the Gateway Server
     */
    public void stopGateway() {
        if (gatewayServer != null) {
            gatewayServer.shutdown();
            logger.info("Py4J Gateway Server stopped");
        }
    }
    
    /**
     * Initialize CloudSim simulation
     */
    public void initializeSimulation(Map<String, Object> config) {
        logger.info("Initializing CloudSim simulation with config: {}", config);
        simulation.initialize(config);
    }
    
    /**
     * Create a datacenter
     */
    public String createDatacenter(String id, int numServers, int cpuPerServer, 
                                    int ramPerServerMB, double powerIdleW, double powerMaxW) {
        logger.info("Creating datacenter: {}", id);
        return simulation.createDatacenter(id, numServers, cpuPerServer, 
                                          ramPerServerMB, powerIdleW, powerMaxW);
    }
    
    /**
     * Submit a VM request (CloudSim decides placement)
     */
    public boolean submitVM(int vmId, int cpus, int ramMB, int mips) {
        return simulation.submitVM(vmId, cpus, ramMB, mips);
    }

    /**
     * Submit a VM request to a specific datacenter (ECMR-controlled placement)
     */
    public boolean submitVMToDatacenter(int vmId, int cpus, int ramMB, int mips, String targetDatacenterId) {
        return simulation.submitVMToDatacenter(vmId, cpus, ramMB, mips, targetDatacenterId);
    }

    /**
     * Get simulation results
     */
    public Map<String, Object> getResults() {
        return simulation.getResults();
    }
    
    /**
     * Run the simulation
     */
    public void runSimulation() {
        logger.info("Starting CloudSim simulation...");
        simulation.run();
        logger.info("Simulation completed");
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
     * Main method to start gateway in standalone mode
     */
    public static void main(String[] args) {
        logger.info("=".repeat(80));
        logger.info("ECMR Baseline - Py4J Gateway Server");
        logger.info("=".repeat(80));
        
        Py4JGateway gateway = new Py4JGateway();
        gateway.startGateway();
        
        logger.info("\nGateway is running. Python scripts can now connect.");
        logger.info("Press Ctrl+C to stop the gateway.\n");
        
        // Keep the gateway running
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("\nShutting down gateway...");
            gateway.stopGateway();
        }));
        
        // Keep main thread alive
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            logger.error("Gateway interrupted", e);
        }
    }
}