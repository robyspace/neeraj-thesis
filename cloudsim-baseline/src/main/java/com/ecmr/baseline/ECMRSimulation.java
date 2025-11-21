package com.ecmr.baseline;

import org.cloudsimplus.core.CloudSimPlus;
import org.cloudsimplus.datacenters.Datacenter;
import org.cloudsimplus.datacenters.DatacenterSimple;
import org.cloudsimplus.hosts.Host;
import org.cloudsimplus.hosts.HostSimple;
import org.cloudsimplus.resources.Pe;
import org.cloudsimplus.resources.PeSimple;
import org.cloudsimplus.vms.Vm;
import org.cloudsimplus.vms.VmSimple;
import org.cloudsimplus.cloudlets.Cloudlet;
import org.cloudsimplus.cloudlets.CloudletSimple;
import org.cloudsimplus.brokers.DatacenterBroker;
import org.cloudsimplus.brokers.DatacenterBrokerSimple;
import org.cloudsimplus.utilizationmodels.UtilizationModelFull;
import org.cloudsimplus.utilizationmodels.UtilizationModelDynamic;
import org.cloudsimplus.power.models.PowerModelHostSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Main CloudSimPlus simulation for ECMR baseline
 * Implements the datacenter infrastructure and VM scheduling
 */
public class ECMRSimulation {
    private static final Logger logger = LoggerFactory.getLogger(ECMRSimulation.class);

    private CloudSimPlus simulation;
    private DatacenterBroker broker;
    private List<Datacenter> datacenters;
    private List<Vm> vmList;
    private Map<String, Datacenter> datacenterMap;
    private Map<Integer, Map<String, Object>> placementDecisions;

    // ECMR-specific: Track which broker/DC each VM was assigned to
    private Map<Integer, String> vmDatacenterAssignments;

    public ECMRSimulation() {
        this.datacenters = new ArrayList<>();
        this.vmList = new ArrayList<>();
        this.datacenterMap = new HashMap<>();
        this.placementDecisions = new HashMap<>();
        this.vmDatacenterAssignments = new HashMap<>();
    }

    /**
     * Initialize the CloudSim simulation
     */
    public void initialize(Map<String, Object> config) {
        logger.info("Initializing CloudSim Plus simulation");

        // Create CloudSim instance
        simulation = new CloudSimPlus();

        // Create custom ECMR broker that respects ECMR's datacenter decisions
        broker = new EcmrDatacenterBroker(simulation, datacenterMap);
        broker.setSelectClosestDatacenter(false); // ECMR handles placement

        logger.info("CloudSim initialized with ECMR-aware broker");
    }

    /**
     * Create a datacenter with specified configuration
     */
    public String createDatacenter(String id, int numServers, int cpuPerServer,
                                   int ramPerServerMB, double powerIdleW, double powerMaxW) {
        logger.info("Creating datacenter: {} with {} servers", id, numServers);

        List<Host> hostList = new ArrayList<>();
        for (int i = 0; i < numServers; i++) {
            Host host = createHost(cpuPerServer, ramPerServerMB, powerIdleW, powerMaxW);
            hostList.add(host);
        }

        // Create datacenter
        Datacenter dc = new DatacenterSimple(simulation, hostList);
        dc.setSchedulingInterval(1); // Schedule every simulation second

        datacenters.add(dc);
        datacenterMap.put(id, dc);

        logger.info("Datacenter {} created with ID: {}", id, dc.getId());
        return id;
    }

    /**
     * Create a host (physical server)
     */
    private Host createHost(int cpus, int ramMB, double powerIdleW, double powerMaxW) {
        List<Pe> peList = new ArrayList<>();

        // Create processing elements (CPU cores)
        for (int i = 0; i < cpus; i++) {
            peList.add(new PeSimple(1000)); // 1000 MIPS per core
        }

        long ram = ramMB; // MB
        long storage = 1000000; // 1 TB in MB
        long bw = 10000; // 10 Gbps in Mbps

        Host host = new HostSimple(ram, bw, storage, peList);

        // Set power model (linear between idle and max power)
        host.setPowerModel(new PowerModelHostSimple(powerMaxW, powerIdleW));

        return host;
    }

    /**
     * Submit a VM request (CloudSim decides placement)
     */
    public boolean submitVM(int vmId, int cpus, int ramMB, int mips) {
        logger.debug("Submitting VM {}: {} CPUs, {} MB RAM", vmId, cpus, ramMB);

        Vm vm = new VmSimple(vmId, mips, cpus)
                .setRam(ramMB)
                .setBw(1000)
                .setSize(10000);

        vmList.add(vm);

        // Create a cloudlet (workload) for this VM with reasonable resource utilization
        Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
                .setFileSize(1024)
                .setOutputSize(1024)
                .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))  // 50% CPU
                .setUtilizationModelRam(new UtilizationModelDynamic(0.3))  // 30% RAM
                .setUtilizationModelBw(new UtilizationModelDynamic(0.2));  // 20% BW

        broker.submitVm(vm);
        broker.submitCloudlet(cloudlet);

        return true;
    }

    /**
     * Submit a VM request to a specific datacenter (ECMR-controlled placement)
     *
     * @param vmId VM identifier
     * @param cpus Number of CPUs
     * @param ramMB RAM in MB
     * @param mips MIPS per CPU
     * @param targetDatacenterId Target datacenter ID (e.g., "DC_IT")
     * @return true if VM was successfully submitted
     */
    public boolean submitVMToDatacenter(int vmId, int cpus, int ramMB, int mips, String targetDatacenterId) {
        logger.debug("Submitting VM {} to datacenter {}: {} CPUs, {} MB RAM",
                    vmId, targetDatacenterId, cpus, ramMB);

        // Get the target datacenter
        Datacenter targetDc = datacenterMap.get(targetDatacenterId);
        if (targetDc == null) {
            logger.warn("Datacenter {} not found, VM {} submission failed", targetDatacenterId, vmId);
            return false;
        }

        Vm vm = new VmSimple(vmId, mips, cpus)
                .setRam(ramMB)
                .setBw(1000)
                .setSize(10000);

        vmList.add(vm);

        // Create a cloudlet (workload) for this VM with reasonable resource utilization
        Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
                .setFileSize(1024)
                .setOutputSize(1024)
                .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))  // 50% CPU
                .setUtilizationModelRam(new UtilizationModelDynamic(0.3))  // 30% RAM
                .setUtilizationModelBw(new UtilizationModelDynamic(0.2));  // 20% BW

        // ECMR-CONTROLLED PLACEMENT: Tag VM with target datacenter
        // Tag the VM with the ECMR-selected datacenter ID
        vm.setDescription(targetDatacenterId);

        // Submit VM and cloudlet to broker
        // Note: CloudSim broker will do automatic placement
        // We track ECMR's decision separately for comparison
        broker.submitVm(vm);
        broker.submitCloudlet(cloudlet);

        // Track ECMR's assignment for comparison with CloudSim's actual placement
        vmDatacenterAssignments.put(vmId, targetDatacenterId);

        logger.debug("VM {} tagged for datacenter {} by ECMR (CloudSim will place automatically)",
                    vmId, targetDatacenterId);
        return true;
    }

    /**
     * Run the simulation
     */
    public void run() {
        logger.info("Starting CloudSim simulation with {} datacenters and {} VMs",
                datacenters.size(), vmList.size());

        double startTime = System.currentTimeMillis();
        simulation.start();
        double endTime = System.currentTimeMillis();

        logger.info("Simulation completed in {} ms", (endTime - startTime));

        // Collect results
        collectResults();
    }

    /**
     * Collect simulation results
     */
    private void collectResults() {
        List<Cloudlet> finishedCloudlets = broker.getCloudletFinishedList();
        logger.info("Collecting results from {} finished cloudlets", finishedCloudlets.size());

        for (Cloudlet cloudlet : finishedCloudlets) {
            Vm vm = cloudlet.getVm();
            Host host = vm.getHost();
            Datacenter dc = host.getDatacenter();

            Map<String, Object> decision = new HashMap<>();
            decision.put("vmId", vm.getId());
            decision.put("datacenterId", dc.getId());
            decision.put("hostId", host.getId());
            decision.put("executionTime", cloudlet.getTotalExecutionTime()); // FIXED: Line 168
            decision.put("finishTime", cloudlet.getFinishTime());
            decision.put("status", cloudlet.getStatus().name());

            placementDecisions.put((int) vm.getId(), decision);
        }
    }

    /**
     * Get simulation results
     */
    public Map<String, Object> getResults() {
        Map<String, Object> results = new HashMap<>();

        // Calculate metrics
        double totalEnergy = 0;
        int successfulVMs = 0;
        int failedVMs = 0;
        double totalExecutionTime = 0;

        for (Datacenter dc : datacenters) {
            for (Host host : dc.getHostList()) {
                // FIXED: Line 190 - Calculate energy manually
                double power = host.getPowerModel().getPower();
                double energyWattSec = power * simulation.clock();
                totalEnergy += energyWattSec;
            }
        }

        List<Cloudlet> finishedList = broker.getCloudletFinishedList();
        successfulVMs = finishedList.size();
        failedVMs = vmList.size() - successfulVMs;

        for (Cloudlet cloudlet : finishedList) {
            totalExecutionTime += cloudlet.getTotalExecutionTime(); // FIXED: Line 199
        }

        double avgExecutionTime = successfulVMs > 0 ?
                totalExecutionTime / successfulVMs : 0;

        results.put("totalEnergy", totalEnergy);
        results.put("successfulVMs", successfulVMs);
        results.put("failedVMs", failedVMs);
        results.put("avgExecutionTime", avgExecutionTime);
        results.put("totalVMs", vmList.size());
        results.put("failureRate", failedVMs * 100.0 / vmList.size());

        logger.info("Results collected: {} successful VMs, {} failed VMs, {} kWh energy",
                successfulVMs, failedVMs, totalEnergy / 3600000); // Convert to kWh

        return results;
    }

    /**
     * Get datacenter statistics
     */
    public Map<String, Object> getDatacenterStats(String datacenterId) {
        Datacenter dc = datacenterMap.get(datacenterId);
        if (dc == null) {
            logger.warn("Datacenter {} not found", datacenterId);
            return new HashMap<>();
        }

        Map<String, Object> stats = new HashMap<>();
        double totalEnergy = 0;
        int totalCpus = 0;
        int usedCpus = 0;
        long totalRam = 0;
        long usedRam = 0;
        int activeVMs = 0; // Add this variable

        for (Host host : dc.getHostList()) {
            // Calculate energy manually
            double power = host.getPowerModel().getPower();
            double energyWattSec = power * simulation.clock();
            totalEnergy += energyWattSec;

            totalCpus += host.getPesNumber();
            usedCpus += host.getBusyPesNumber();
            totalRam += host.getRam().getCapacity();
            usedRam += host.getRam().getAllocatedResource();

            // FIXED: Line 252 - Count VMs from each host
            activeVMs += host.getVmList().size();
        }

        stats.put("datacenterId", dc.getId());
        stats.put("totalEnergy", totalEnergy / 3600000); // kWh
        stats.put("numHosts", dc.getHostList().size());
        stats.put("cpuUtilization", totalCpus > 0 ? (usedCpus * 100.0 / totalCpus) : 0);
        stats.put("ramUtilization", totalRam > 0 ? (usedRam * 100.0 / totalRam) : 0);
        stats.put("activeVMs", activeVMs);

        return stats;
    }

    /**
     * Get all placement decisions
     */
    public List<Map<String, Object>> getPlacementDecisions() {
        return new ArrayList<>(placementDecisions.values());
    }

    /**
     * Main method for standalone execution
     */
    public static void main(String[] args) {
        logger.info("=".repeat(80));
        logger.info("ECMR Baseline - CloudSimPlus Simulation");
        logger.info("=".repeat(80));

        // Example usage
        ECMRSimulation sim = new ECMRSimulation();
        sim.initialize(new HashMap<>());

        // Create 3 datacenters
        sim.createDatacenter("DC1", 10, 32, 128 * 1024, 200, 400);
        sim.createDatacenter("DC2", 10, 32, 128 * 1024, 200, 400);
        sim.createDatacenter("DC3", 10, 32, 128 * 1024, 200, 400);

        // Submit some VMs
        for (int i = 0; i < 50; i++) {
            sim.submitVM(i, 4, 8192, 4000);
        }

        // Run simulation
        sim.run();

        // Get results
        Map<String, Object> results = sim.getResults();
        logger.info("Simulation Results: {}", results);
        logger.info("=".repeat(80));
    }
}
