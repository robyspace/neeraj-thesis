package org.example;

import org.cloudsimplus.brokers.DatacenterBroker;
import org.cloudsimplus.brokers.DatacenterBrokerSimple;
import org.cloudsimplus.builders.tables.CloudletsTableBuilder;
import org.cloudsimplus.cloudlets.Cloudlet;
import org.cloudsimplus.cloudlets.CloudletSimple;
import org.cloudsimplus.core.CloudSimPlus;
import org.cloudsimplus.datacenters.Datacenter;
import org.cloudsimplus.datacenters.DatacenterSimple;
import org.cloudsimplus.hosts.Host;
import org.cloudsimplus.hosts.HostSimple;
import org.cloudsimplus.resources.Pe;
import org.cloudsimplus.resources.PeSimple;
import org.cloudsimplus.utilizationmodels.UtilizationModelDynamic;
import org.cloudsimplus.utilizationmodels.UtilizationModelFull;
import org.cloudsimplus.vms.Vm;
import org.cloudsimplus.vms.VmSimple;

import java.util.ArrayList;
import java.util.List;

/**
 * Simple CloudSim Plus test to verify the setup is working correctly.
 * This example creates a single datacenter with one host, one VM, and one cloudlet.
 */
public class SimpleTest {
    
    private static final int HOSTS = 1;
    private static final int HOST_PES = 8;
    private static final int VMS = 1;
    private static final int VM_PES = 4;
    private static final int CLOUDLETS = 1;
    private static final int CLOUDLET_PES = 2;
    private static final int CLOUDLET_LENGTH = 10000;

    private CloudSimPlus simulation;
    private DatacenterBroker broker0;
    private List<Vm> vmList;
    private List<Cloudlet> cloudletList;
    private Datacenter datacenter0;

    public static void main(String[] args) {
        new SimpleTest();
    }

    private SimpleTest() {
        System.out.println("\n=== CloudSim Plus Simple Test ===\n");
        
        // Initialize CloudSim Plus
        simulation = new CloudSimPlus();

        // Create Datacenter
        datacenter0 = createDatacenter();
        System.out.println("✓ Created datacenter with " + HOSTS + " host(s)");

        // Create Broker
        broker0 = new DatacenterBrokerSimple(simulation);

        // Create VMs and Cloudlets
        vmList = createVms();
        cloudletList = createCloudlets();
        
        broker0.submitVmList(vmList);
        broker0.submitCloudletList(cloudletList);
        
        System.out.println("✓ Created " + VMS + " VM(s)");
        System.out.println("✓ Created " + CLOUDLETS + " cloudlet(s)");

        // Run simulation
        System.out.println("Starting simulation...\n");
        simulation.start();

        // Print results
        printResults();
    }

    /**
     * Creates a Datacenter with a list of hosts.
     */
    private Datacenter createDatacenter() {
        List<Host> hostList = new ArrayList<>(HOSTS);
        for (int i = 0; i < HOSTS; i++) {
            Host host = createHost();
            hostList.add(host);
        }

        return new DatacenterSimple(simulation, hostList);
    }

    /**
     * Creates a host with a list of PEs (Processing Elements/CPU cores).
     */
    private Host createHost() {
        List<Pe> peList = new ArrayList<>(HOST_PES);
        // List of Host's CPUs (Processing Elements, PEs)
        for (int i = 0; i < HOST_PES; i++) {
            peList.add(new PeSimple(1000)); // MIPS capacity
        }

        long ram = 2048; // in Megabytes
        long bw = 10000; // in Megabits/s
        long storage = 1000000; // in Megabytes

        return new HostSimple(ram, bw, storage, peList);
    }

    /**
     * Creates a list of VMs.
     */
    private List<Vm> createVms() {
        List<Vm> list = new ArrayList<>(VMS);
        for (int i = 0; i < VMS; i++) {
            Vm vm = new VmSimple(1000, VM_PES);
            vm.setRam(512).setBw(1000).setSize(10000);
            list.add(vm);
        }
        return list;
    }

    /**
     * Creates a list of Cloudlets.
     */
    private List<Cloudlet> createCloudlets() {
        List<Cloudlet> list = new ArrayList<>(CLOUDLETS);
        
        // UtilizationModel defining the Cloudlet uses full CPU
        UtilizationModelFull utilizationModel = new UtilizationModelFull();
        
        for (int i = 0; i < CLOUDLETS; i++) {
            Cloudlet cloudlet = new CloudletSimple(CLOUDLET_LENGTH, CLOUDLET_PES, utilizationModel);
            cloudlet.setSizes(1024);
            list.add(cloudlet);
        }
        return list;
    }

    /**
     * Prints simulation results.
     */
    private void printResults() {
        List<Cloudlet> finishedCloudlets = broker0.getCloudletFinishedList();
        
        System.out.println("=== Simulation Results ===\n");
        new CloudletsTableBuilder(finishedCloudlets).build();
        
        System.out.println("\n✓ Simulation completed successfully!");
    }
}