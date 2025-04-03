def export(func):
    func._export = True
    func._export_name = func.__name__

    return func


def get_adapter_cls_from_hardware_object(ho):
    # This needs to be a direct import of Argus/DataPublisher otherwise the
    # is instance check below fails due to different "import paths" It
    # only works because mxcubecore adds mxcubecore.HardwareObjects to
    # sys path in __init__.py
    import Argus
    import DataPublisher
    from mxcubecore.HardwareObjects import (
        GenericDiffractometer,
        MiniDiff,
    )
    from mxcubecore.HardwareObjects.abstract import (
        AbstractActuator,
        AbstractBeam,
        AbstractDetector,
        AbstractEnergy,
        AbstractMachineInfo,
        AbstractMotor,
        AbstractNState,
        AbstractShutter,
    )

    from mxcubeweb.core.adapter.actuator_adapter import ActuatorAdapter
    from mxcubeweb.core.adapter.argus_adapter import ArgusAdapter
    from mxcubeweb.core.adapter.beam_adapter import BeamAdapter
    from mxcubeweb.core.adapter.data_publisher_adapter import DataPublisherAdapter
    from mxcubeweb.core.adapter.detector_adapter import DetectorAdapter
    from mxcubeweb.core.adapter.diffractometer_adapter import DiffractometerAdapter
    from mxcubeweb.core.adapter.energy_adapter import EnergyAdapter
    from mxcubeweb.core.adapter.machine_info_adapter import MachineInfoAdapter
    from mxcubeweb.core.adapter.motor_adapter import MotorAdapter
    from mxcubeweb.core.adapter.nstate_adapter import NStateAdapter

    adapter_mapping = {
        (AbstractNState.AbstractNState, AbstractShutter.AbstractShutter): NStateAdapter,
        (
            MiniDiff.MiniDiff,
            GenericDiffractometer.GenericDiffractometer,
        ): DiffractometerAdapter,
        (AbstractEnergy.AbstractEnergy,): EnergyAdapter,
        (AbstractDetector.AbstractDetector,): DetectorAdapter,
        (AbstractMachineInfo.AbstractMachineInfo,): MachineInfoAdapter,
        (AbstractBeam.AbstractBeam,): BeamAdapter,
        (DataPublisher.DataPublisher,): DataPublisherAdapter,
        (AbstractMotor.AbstractMotor,): MotorAdapter,
        (AbstractActuator.AbstractActuator,): ActuatorAdapter,
        (Argus.Argus,): ArgusAdapter,
    }

    return next(
        (
            adapter
            for classes, adapter in adapter_mapping.items()
            if isinstance(ho, classes)
        ),
        None,
    )
