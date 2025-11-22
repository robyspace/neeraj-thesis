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
import org.cloudsimplus.utilizationmodels.UtilizationModelDynamic;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Enhanced CloudSimPlus simulation implementing the EXACT infrastructure from Miao2024.pdf
 *
 * Key Features:
 * - 3 heterogeneous server types (Huawei RH2285 V2, RH2288H V3, Lenovo SR655 V3)
 * - Detailed power consumption profiles from Table 4 (11-point curves)
 * - 4 VM instance types (small, medium, large, xlarge)
 * - Heterogeneous datacenter configuration (40 servers of each type per DC)
 * - PUE-based total energy calculation
 */
public class ECMRSimulationEnhanced {
    private static final Logger logger = LoggerFactory.getLogger(ECMRSimulationEnhanced.class);

    private CloudSimPlus simulation;
    private DatacenterBroker broker;
    private List<Datacenter> datacenters;
    private List<Vm> vmList;
    private Map<String, Datacenter> datacenterMap;
    private Map<Integer, Map<String, Object>> placementDecisions;
    private Map<Integer, String> vmDatacenterAssignments;

    // PUE (Power Usage Effectiveness) per datacenter
    private Map<String, Double> datacenterPUE;

    // Real-time utilization tracking (samples collected during simulation)
    private Map<String, List<Double>> datacenterCpuUtilization;
    private Map<String, List<Double>> datacenterRamUtilization;
    private static final double MONITORING_INTERVAL = 3600.0; // Sample every hour (3600 seconds)

    // Default PUE value (can be overridden per datacenter)
    private static final double DEFAULT_PUE = 1.2;

    public ECMRSimulationEnhanced() {
        this.datacenters = new ArrayList<>();
        this.vmList = new ArrayList<>();
        this.datacenterMap = new HashMap<>();
        this.placementDecisions = new HashMap<>();
        this.vmDatacenterAssignments = new HashMap<>();
        this.datacenterPUE = new HashMap<>();
        this.datacenterCpuUtilization = new HashMap<>();
        this.datacenterRamUtilization = new HashMap<>();
    }

    /**
     * Initialize the CloudSim simulation
     */
    public void initialize(Map<String, Object> config) {
        logger.info("Initializing Enhanced CloudSim Plus simulation");

        // Clear previous simulation state to prevent memory leaks
        datacenters.clear();
        vmList.clear();
        datacenterMap.clear();
        placementDecisions.clear();
        vmDatacenterAssignments.clear();
        datacenterPUE.clear();
        datacenterCpuUtilization.clear();
        datacenterRamUtilization.clear();

        simulation = new CloudSimPlus();
        broker = new EcmrDatacenterBroker(simulation, datacenterMap);
        broker.setSelectClosestDatacenter(false);

        logger.info("Enhanced CloudSim initialized with heterogeneous server infrastructure");
    }

    /**
     * Initialize the CloudSim simulation (no config needed)
     */
    public void initialize() {
        initialize(new HashMap<>());
    }

    /**
     * Create a datacenter with HETEROGENEOUS servers matching Miao2024.pdf
     *
     * @param id Datacenter ID (e.g., "DC_ITALY")
     * @param serversPerType Number of servers of each type (typically 40)
     * @param pue Power Usage Effectiveness for this datacenter
     * @return Datacenter ID
     */
    public String createHeterogeneousDatacenter(String id, int serversPerType, double pue) {
        logger.info("Creating heterogeneous datacenter: {} with {} servers per type (PUE: {})",
                    id, serversPerType, pue);

        List<Host> hostList = new ArrayList<>();

        // Create servers of each type (40 of each = 120 total per DC)
        for (ServerType type : ServerType.values()) {
            for (int i = 0; i < serversPerType; i++) {
                Host host = createHost(type);
                hostList.add(host);
            }
            logger.debug("Added {} servers of type {}", serversPerType, type.getModelName());
        }

        // Create datacenter
        Datacenter dc = new DatacenterSimple(simulation, hostList);
        dc.setSchedulingInterval(1.0); // Schedule every simulation second

        datacenters.add(dc);
        datacenterMap.put(id, dc);
        datacenterPUE.put(id, pue);

        // Initialize utilization tracking lists
        datacenterCpuUtilization.put(id, new ArrayList<>());
        datacenterRamUtilization.put(id, new ArrayList<>());

        logger.info("Datacenter {} created with {} heterogeneous hosts (PUE: {})",
                    id, hostList.size(), pue);
        return id;
    }

    /**
     * Create a datacenter with simple configuration (for backward compatibility)
     */
    public String createDatacenter(String id, int numServers, int cpuPerServer,
                                   int ramPerServerMB, double powerIdleW, double powerMaxW) {
        // Use default heterogeneous configuration
        return createHeterogeneousDatacenter(id, 40, DEFAULT_PUE);
    }

    /**
     * Create a host based on ServerType specifications
     */
    private Host createHost(ServerType serverType) {
        List<Pe> peList = new ArrayList<>();

        // Create processing elements with MIPS from server specs
        for (int i = 0; i < serverType.getNumCores(); i++) {
            peList.add(new PeSimple(serverType.getMipsPerCore()));
        }

        // Create host with specifications from ServerType
        Host host = new HostSimple(
            serverType.getRamMB(),
            serverType.getBandwidthMbps(),
            serverType.getStorageMB(),
            peList
        );

        // Set custom power model using the detailed power consumption profile
        host.setPowerModel(new ServerPowerModel(serverType));

        host.setId(host.getId()); // Ensure ID is set
        logger.trace("Created host: {}", serverType);

        return host;
    }

    /**
     * Submit a VM using predefined VM type
     */
    public boolean submitVMByType(int vmId, VMType vmType, String targetDatacenterId) {
        logger.debug("Submitting VM {} (type: {}) to datacenter {}",
                    vmId, vmType.getName(), targetDatacenterId);

        // Verify datacenter exists
        Datacenter targetDc = datacenterMap.get(targetDatacenterId);
        if (targetDc == null) {
            logger.warn("Datacenter {} not found", targetDatacenterId);
            return false;
        }

        // Create VM with specifications from VMType
        // VmSimple expects: (id, mipsPerCore, numberOfCores)
        Vm vm = new VmSimple(vmId, vmType.getMipsPerCore(), vmType.getNumCores())
                .setRam(vmType.getRamMB())
                .setBw(vmType.getBandwidthMbps())
                .setSize(vmType.getStorageMB());

        // Tag VM with target datacenter for ECMR enforcement
        vm.setDescription(targetDatacenterId);

        vmList.add(vm);

        // Create cloudlet with realistic utilization
        Cloudlet cloudlet = new CloudletSimple(vmId, 10000 * vmType.getNumCores(), vmType.getNumCores())
                .setFileSize(1024)
                .setOutputSize(1024)
                .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))   // 50% CPU
                .setUtilizationModelRam(new UtilizationModelDynamic(0.3))   // 30% RAM
                .setUtilizationModelBw(new UtilizationModelDynamic(0.2));   // 20% BW

        broker.submitVm(vm);
        broker.submitCloudlet(cloudlet);

        vmDatacenterAssignments.put(vmId, targetDatacenterId);

        return true;
    }

    /**
     * Submit a VM with custom specifications (for backward compatibility)
     */
    public boolean submitVMToDatacenter(int vmId, int cpus, int ramMB, int mips, String targetDatacenterId) {
        logger.debug("Submitting custom VM {} to datacenter {}: {} CPUs, {} MB RAM, {} MIPS",
                    vmId, targetDatacenterId, cpus, ramMB, mips);

        Datacenter targetDc = datacenterMap.get(targetDatacenterId);
        if (targetDc == null) {
            logger.warn("Datacenter {} not found", targetDatacenterId);
            return false;
        }

        Vm vm = new VmSimple(vmId, mips, cpus)
                .setRam(ramMB)
                .setBw(1000)
                .setSize(10000);

        vm.setDescription(targetDatacenterId);
        vmList.add(vm);

        Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
                .setFileSize(1024)
                .setOutputSize(1024)
                .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))
                .setUtilizationModelRam(new UtilizationModelDynamic(0.3))
                .setUtilizationModelBw(new UtilizationModelDynamic(0.2));

        broker.submitVm(vm);
        broker.submitCloudlet(cloudlet);

        vmDatacenterAssignments.put(vmId, targetDatacenterId);

        return true;
    }

    /**
     * Submit VM without datacenter specification (CloudSim auto-placement)
     */
    public boolean submitVM(int vmId, int cpus, int ramMB, int mips) {
        Vm vm = new VmSimple(vmId, mips, cpus)
                .setRam(ramMB)
                .setBw(1000)
                .setSize(10000);

        vmList.add(vm);

        Cloudlet cloudlet = new CloudletSimple(vmId, 10000, cpus)
                .setFileSize(1024)
                .setOutputSize(1024)
                .setUtilizationModelCpu(new UtilizationModelDynamic(0.5))
                .setUtilizationModelRam(new UtilizationModelDynamic(0.3))
                .setUtilizationModelBw(new UtilizationModelDynamic(0.2));

        broker.submitVm(vm);
        broker.submitCloudlet(cloudlet);

        return true;
    }

    /**
     * Run the simulation
     */
    public void run() {
        logger.info("Starting CloudSim simulation with {} datacenters and {} VMs",
                datacenters.size(), vmList.size());

        // Setup real-time utilization monitoring
        setupUtilizationMonitoring();

        double startTime = System.currentTimeMillis();
        simulation.start();
        double endTime = System.currentTimeMillis();

        logger.info("Simulation completed in {} ms", (endTime - startTime));

        collectResults();
    }

    /**
     * Setup real-time utilization monitoring during simulation
     * Samples CPU and RAM utilization at regular intervals
     */
    private void setupUtilizationMonitoring() {
        simulation.addOnClockTickListener(eventInfo -> {
            double clock = eventInfo.getTime();

            // Sample every MONITORING_INTERVAL seconds
            if (clock % MONITORING_INTERVAL < 1.0) {
                for (Map.Entry<String, Datacenter> entry : datacenterMap.entrySet()) {
                    String dcId = entry.getKey();
                    Datacenter dc = entry.getValue();

                    int totalCpus = 0;
                    int usedCpus = 0;
                    long totalRam = 0;
                    long usedRam = 0;

                    for (Host host : dc.getHostList()) {
                        totalCpus += host.getPesNumber();
                        usedCpus += host.getBusyPesNumber();
                        totalRam += host.getRam().getCapacity();
                        usedRam += host.getRam().getAllocatedResource();
                    }

                    // Calculate utilization percentages
                    double cpuUtil = totalCpus > 0 ? (usedCpus * 100.0 / totalCpus) : 0;
                    double ramUtil = totalRam > 0 ? (usedRam * 100.0 / totalRam) : 0;

                    // Store samples
                    datacenterCpuUtilization.get(dcId).add(cpuUtil);
                    datacenterRamUtilization.get(dcId).add(ramUtil);

                    logger.debug("Utilization sample at {}s - {}: CPU={:.2f}%, RAM={:.2f}%",
                            clock, dcId, cpuUtil, ramUtil);
                }
            }
        });

        logger.info("Real-time utilization monitoring enabled (sampling every {} seconds)",
                MONITORING_INTERVAL);
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
            decision.put("vmId", (int) vm.getId());
            decision.put("datacenterId", (int) dc.getId());
            decision.put("hostId", (int) host.getId());
            decision.put("executionTime", cloudlet.getTotalExecutionTime());
            decision.put("finishTime", cloudlet.getFinishTime());
            decision.put("status", cloudlet.getStatus().name());

            // Get server type info from host
            String serverType = getServerTypeFromHost(host);
            decision.put("serverType", serverType);

            placementDecisions.put(Integer.valueOf((int) vm.getId()), decision);
        }
    }

    /**
     * Identify server type from host specifications
     */
    private String getServerTypeFromHost(Host host) {
        int cores = (int) host.getPesNumber();
        if (cores == 16) return ServerType.HUAWEI_RH2285_V2.getModelName();
        if (cores == 40) return ServerType.HUAWEI_RH2288H_V3.getModelName();
        if (cores == 96) return ServerType.LENOVO_SR655_V3.getModelName();
        return "Unknown";
    }

    /**
     * Get simulation results with PUE-adjusted energy
     */
    public Map<String, Object> getResults() {
        Map<String, Object> results = new HashMap<>();

        double totalITEnergy = 0;
        double totalDatacenterEnergy = 0;
        int successfulVMs = 0;
        int failedVMs = 0;
        double totalExecutionTime = 0;

        // Calculate energy for each datacenter
        for (Map.Entry<String, Datacenter> entry : datacenterMap.entrySet()) {
            String dcId = entry.getKey();
            Datacenter dc = entry.getValue();
            double pue = datacenterPUE.getOrDefault(dcId, DEFAULT_PUE);

            double dcITEnergy = 0;
            for (Host host : dc.getHostList()) {
                double power = host.getPowerModel().getPower();
                double energyWattSec = power * simulation.clock();
                dcITEnergy += energyWattSec;
            }

            totalITEnergy += dcITEnergy;
            totalDatacenterEnergy += dcITEnergy * pue;
        }

        List<Cloudlet> finishedList = broker.getCloudletFinishedList();
        successfulVMs = finishedList.size();
        failedVMs = vmList.size() - successfulVMs;

        for (Cloudlet cloudlet : finishedList) {
            totalExecutionTime += cloudlet.getTotalExecutionTime();
        }

        double avgExecutionTime = successfulVMs > 0 ? totalExecutionTime / successfulVMs : 0;

        results.put("totalITEnergy", totalITEnergy);
        results.put("totalDatacenterEnergy", totalDatacenterEnergy);
        results.put("totalEnergyKWh", totalDatacenterEnergy / 3600000); // Convert to kWh
        results.put("totalITEnergyKWh", totalITEnergy / 3600000);
        results.put("averagePUE", totalDatacenterEnergy / totalITEnergy);
        results.put("successfulVMs", successfulVMs);
        results.put("failedVMs", failedVMs);
        results.put("avgExecutionTime", avgExecutionTime);
        results.put("totalVMs", vmList.size());
        results.put("failureRate", failedVMs * 100.0 / vmList.size());

        logger.info("Results: {} successful VMs, {} failed VMs, {:.2f} kWh total energy (PUE-adjusted)",
                successfulVMs, failedVMs, totalDatacenterEnergy / 3600000);

        return results;
    }

    /**
     * Get datacenter statistics with PUE-adjusted energy
     */
    public Map<String, Object> getDatacenterStats(String datacenterId) {
        Datacenter dc = datacenterMap.get(datacenterId);
        if (dc == null) {
            logger.warn("Datacenter {} not found", datacenterId);
            return new HashMap<>();
        }

        Map<String, Object> stats = new HashMap<>();
        double pue = datacenterPUE.getOrDefault(datacenterId, DEFAULT_PUE);

        double itEnergy = 0;
        int totalCpus = 0;
        int usedCpus = 0;
        long totalRam = 0;
        long usedRam = 0;
        int activeVMs = 0;

        // Count servers by type
        int huaweiRH2285 = 0, huaweiRH2288 = 0, lenovoSR655 = 0;

        for (Host host : dc.getHostList()) {
            double power = host.getPowerModel().getPower();
            double energyWattSec = power * simulation.clock();
            itEnergy += energyWattSec;

            totalCpus += host.getPesNumber();
            totalRam += host.getRam().getCapacity();
            activeVMs += host.getVmList().size();

            // Count server types
            int cores = (int) host.getPesNumber();
            if (cores == 16) huaweiRH2285++;
            else if (cores == 40) huaweiRH2288++;
            else if (cores == 96) lenovoSR655++;
        }

        double totalEnergy = itEnergy * pue;

        // Calculate average utilization from samples collected during simulation
        double avgCpuUtil = calculateAverageUtilization(datacenterCpuUtilization.get(datacenterId));
        double avgRamUtil = calculateAverageUtilization(datacenterRamUtilization.get(datacenterId));

        stats.put("datacenterId", (int) dc.getId());
        stats.put("itEnergyKWh", itEnergy / 3600000);
        stats.put("totalEnergyKWh", totalEnergy / 3600000);
        stats.put("pue", pue);
        stats.put("numHosts", dc.getHostList().size());
        stats.put("huaweiRH2285Count", huaweiRH2285);
        stats.put("huaweiRH2288Count", huaweiRH2288);
        stats.put("lenovoSR655Count", lenovoSR655);
        stats.put("cpuUtilization", avgCpuUtil);
        stats.put("ramUtilization", avgRamUtil);
        stats.put("activeVMs", activeVMs);
        stats.put("cpuUtilizationSamples", datacenterCpuUtilization.get(datacenterId).size());
        stats.put("ramUtilizationSamples", datacenterRamUtilization.get(datacenterId).size());

        return stats;
    }

    /**
     * Calculate average utilization from collected samples
     */
    private double calculateAverageUtilization(List<Double> samples) {
        if (samples == null || samples.isEmpty()) {
            return 0.0;
        }

        double sum = 0.0;
        for (Double sample : samples) {
            sum += sample;
        }

        return sum / samples.size();
    }

    /**
     * Get all placement decisions
     */
    public List<Map<String, Object>> getPlacementDecisions() {
        return new ArrayList<>(placementDecisions.values());
    }

    /**
     * Main method for standalone testing
     */
    public static void main(String[] args) {
        logger.info("=".repeat(80));
        logger.info("ECMR Enhanced - CloudSimPlus Simulation with Heterogeneous Servers");
        logger.info("=".repeat(80));

        ECMRSimulationEnhanced sim = new ECMRSimulationEnhanced();
        sim.initialize(new HashMap<>());

        // Create datacenters with heterogeneous servers (40 of each type = 120 total)
        sim.createHeterogeneousDatacenter("DC_ITALY", 40, 1.2);
        sim.createHeterogeneousDatacenter("DC_SWEDEN", 40, 1.15);
        sim.createHeterogeneousDatacenter("DC_FRANCE", 40, 1.2);

        logger.info("\nSubmitting VMs of different types...\n");

        // Submit VMs of different types
        sim.submitVMByType(0, VMType.SMALL, "DC_ITALY");
        sim.submitVMByType(1, VMType.MEDIUM, "DC_SWEDEN");
        sim.submitVMByType(2, VMType.LARGE, "DC_FRANCE");
        sim.submitVMByType(3, VMType.XLARGE, "DC_ITALY");
        sim.submitVMByType(4, VMType.MEDIUM, "DC_SWEDEN");

        // Run simulation
        sim.run();

        // Print results
        Map<String, Object> results = sim.getResults();
        logger.info("\n" + "=".repeat(80));
        logger.info("SIMULATION RESULTS:");
        logger.info("=".repeat(80));
        results.forEach((key, value) -> logger.info("{}: {}", key, value));

        // Print per-datacenter stats
        logger.info("\n" + "=".repeat(80));
        logger.info("DATACENTER STATISTICS:");
        logger.info("=".repeat(80));
        for (String dcId : Arrays.asList("DC_ITALY", "DC_SWEDEN", "DC_FRANCE")) {
            Map<String, Object> stats = sim.getDatacenterStats(dcId);
            logger.info("\n{}: {}", dcId, stats);
        }

        logger.info("\n" + "=".repeat(80));
    }
}
