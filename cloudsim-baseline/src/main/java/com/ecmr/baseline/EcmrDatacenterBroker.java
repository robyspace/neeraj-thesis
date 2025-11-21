package com.ecmr.baseline;

import org.cloudsimplus.brokers.DatacenterBrokerSimple;
import org.cloudsimplus.core.CloudSimPlus;
import org.cloudsimplus.datacenters.Datacenter;
import org.cloudsimplus.vms.Vm;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Comparator;
import java.util.Map;

/**
 * Custom DatacenterBroker that ENFORCES ECMR datacenter selection decisions
 * VMs are tagged with target datacenter ID in their description field
 * This broker uses a custom datacenter mapper to place VMs exactly where ECMR decided
 */
public class EcmrDatacenterBroker extends DatacenterBrokerSimple {
    private static final Logger logger = LoggerFactory.getLogger(EcmrDatacenterBroker.class);
    private Map<String, Datacenter> datacenterMap;

    public EcmrDatacenterBroker(CloudSimPlus simulation, Map<String, Datacenter> datacenterMap) {
        super(simulation);
        this.datacenterMap = datacenterMap;
        this.setSelectClosestDatacenter(false);

        // Set custom datacenter mapper to enforce ECMR decisions
        this.setDatacenterMapper(this::mapVmToEcmrSelectedDatacenter);

        logger.info("EcmrDatacenterBroker initialized with ECMR-enforced placement");
    }

    /**
     * Custom datacenter mapper that enforces ECMR's placement decisions
     * Reads the target datacenter ID from VM description and returns that datacenter
     *
     * @param datacenter The datacenter suggested by CloudSim (ignored)
     * @param vm The VM to be placed
     * @return The datacenter selected by ECMR algorithm
     */
    private Datacenter mapVmToEcmrSelectedDatacenter(Datacenter datacenter, Vm vm) {
        String ecmrTargetId = vm.getDescription();

        if (ecmrTargetId == null || ecmrTargetId.isEmpty()) {
            logger.warn("VM {} has no ECMR target datacenter, using CloudSim default", vm.getId());
            return datacenter;
        }

        Datacenter ecmrTarget = datacenterMap.get(ecmrTargetId);

        if (ecmrTarget == null) {
            logger.error("ECMR target datacenter {} not found for VM {}, using CloudSim default",
                        ecmrTargetId, vm.getId());
            return datacenter;
        }

        logger.debug("VM {} mapped to ECMR-selected datacenter: {} (overriding CloudSim suggestion: {})",
                    vm.getId(), ecmrTargetId, datacenter.getId());

        return ecmrTarget;
    }

    /**
     * Track ECMR decisions when VMs are submitted
     */
    @Override
    public EcmrDatacenterBroker submitVm(Vm vm) {
        String ecmrTarget = vm.getDescription();
        if (ecmrTarget != null && !ecmrTarget.isEmpty()) {
            logger.info("VM {} submitted with ECMR target datacenter: {}", vm.getId(), ecmrTarget);
        }
        super.submitVm(vm);
        return this;
    }
}
