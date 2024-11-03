import pymmcore_plus
# from pylab.widgets import (
#     MDA,
#     load_arduino_led,
#     stop_led,
# )
# import napari
#from qtpy.QtWidgets import QApplication
#from pylab.engine import AcquisitionEngine
#from pylab.config import Config
#from pylab.widgets import MainWidget

import numpy as np
import useq
import os
import glob
from pymmcore_plus.mda import MDAEngine
import time

DHYANA_CONFIG = r'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg'
THOR_CONFIG = r'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg'

pymmcore_plus.configure_logging(stderr_level=5, file_level="DEBUG")

mmcore_dhyana: pymmcore_plus.CMMCorePlus = pymmcore_plus.CMMCorePlus(mm_path=r'C:\Program Files\Micro-Manager-2.0')
mmcore_thor: pymmcore_plus.CMMCorePlus = pymmcore_plus.CMMCorePlus(mm_path=r'C:\Program Files\Micro-Manager-thor')
mmcore_dhyana.loadSystemConfiguration(DHYANA_CONFIG)
mmcore_thor.loadSystemConfiguration(THOR_CONFIG)

def load_thorcam_mmc_params(mmcore2=mmcore_thor):
    '''Load ThorCam MicroManager configuration:
    - loadSystemConfiguration from pylab.mdacore.THOR_CONFIG
    - setROI to 440, 305, 509, 509
    - setExposure to 20
    - use_hardware_sequencing to True
    '''
    
    print("Loading ThorCam MicroManager configuration...")
    mmcore2.setROI("ThorCam", 440, 305, 509, 509)
    mmcore2.setExposure(20)
    mmcore2.mda.engine.use_hardware_sequencing = True
    print("ThorCam MicroManager configuration loaded.")

def load_dhyana_mmc_params(mmcore1=mmcore_dhyana):
    '''Load Dhyana MicroManager configuration:
    - loadSystemConfiguration from pylab.mdacore.DHYANA_CONFIG
    - setProperty 'Arduino-Switch', 'Sequence', 'On'
    - setChannelGroup 'Channel'
    - setProperty 'Arduino-Shutter', 'OnOff', '1'
    - setProperty 'Dhyana', 'Output Trigger Port', '2'
    - setProperty 'Core', 'Shutter', 'Arduino-Shutter'
    - setProperty 'Dhyana', 'Gain', 'HDR'
    - setChannelGroup 'Channel'
    '''
    
    print("Loading Dhyana MicroManager configuration...")
    mmcore1.setProperty('Arduino-Switch', 'Sequence', 'On')
    mmcore1.setProperty('Arduino-Shutter', 'OnOff', '1')
    mmcore1.setProperty('Dhyana', 'Output Trigger Port', '2')
    mmcore1.setProperty('Core', 'Shutter', 'Arduino-Shutter')
    mmcore1.setProperty('Dhyana', 'Gain', 'HDR')
    mmcore1.setChannelGroup('Channel')
    mmcore1.mda.engine.use_hardware_sequencing = True
    print("Dhyana MicroManager configuration loaded.")

def load_napari_gui(dev = True):
    
    print("launching Dhyana interface...")
    viewer = napari.Viewer()
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    
    print("Launching Mesofield Interface with ThorCam...")
    mesofield = AcquisitionEngine(viewer, mmcore_dhyana, Config)
    pupil_widget = MDA(mmcore_thor, Config)
    viewer.window.add_dock_widget([mesofield, pupil_widget, load_arduino_led, stop_led], 
                                  area='right', name='Mesofield')

    if dev:
        mmcore_dhyana.loadSystemConfiguration()
        mmcore_thor.loadSystemConfiguration()
    else:
        load_dhyana_mmc_params(mmcore_dhyana)
        load_thorcam_mmc_params(mmcore_thor)
        
    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py
    napari.run()
    
def load_custom_gui():
    load_dhyana_mmc_params(mmcore_dhyana)
    load_thorcam_mmc_params(mmcore_thor)
    app = QApplication([])
    mesofield = MainWidget(mmcore_dhyana, mmcore_thor, Config)
    #pupil_cam = MDA(mmcore_thor, Config)
    mesofield.show()
    #pupil_cam.show()
    app.exec_()
 
 
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from pymmcore_plus.core._sequencing import SequencedEvent
    from pymmcore_plus.metadata.schema import FrameMetaV1
    from numpy.typing import NDArray
    from useq import MDAEvent
    PImagePayload = tuple[NDArray, MDAEvent, FrameMetaV1]
from itertools import product


class PupilEngine(MDAEngine):
    
    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-setup
        print('START: pupil custom setup_event')
        super().setup_event(event)  
        print('DONE: pupil custom setup_event')

        # do some custom post-setup

    def exec_event(self, event: useq.MDAEvent) -> object:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-execution
        print(f'START: pupil custom exec_event \n Event type: {type(event)}')
        result = super().exec_event(event)  
        print(f'DONE: pupil custom exec_event \n Event type: {type(event)}')

        # do some custom post-execution
        return result
    
    def exec_sequenced_event(self, event: 'SequencedEvent') -> Iterable['PImagePayload']:
        n_events = len(event.events)

        t0 = event.metadata.get("runner_t0") or time.perf_counter()
        event_t0_ms = (time.perf_counter() - t0) * 1000

        # Start sequence
        # Note that the overload of startSequenceAcquisition that takes a camera
        # label does NOT automatically initialize a circular buffer.  So if this call
        # is changed to accept the camera in the future, that should be kept in mind.
        self._mmc.startSequenceAcquisition(
            n_events,
            0,  # intervalMS  # TODO: add support for this
            True,  # stopOnOverflow
        )
        self.post_sequence_started(event)

        n_channels = self._mmc.getNumberOfCameraChannels()
        count = 0
        expected_images = n_events * n_channels
        print(f'pupil expected images: {expected_images}')
        iter_events = product(event.events, range(n_channels))
        # block until the sequence is done, popping images in the meantime
        while self._mmc.isSequenceRunning():
            if remaining := self._mmc.getRemainingImageCount():
                yield self._next_seqimg_payload(
                    *next(iter_events), remaining=remaining - 1, event_t0=event_t0_ms
                )
                count += 1
            else:
                time.sleep(0.001)
                if count == expected_images:
                    self._mmc.stopSequenceAcquisition()
                    print(f'stopped pupil MDA image overflow: {self._mmc}')
                    

        if self._mmc.isBufferOverflowed():  # pragma: no cover
            raise MemoryError("Buffer overflowed")

        while remaining := self._mmc.getRemainingImageCount():
            yield self._next_seqimg_payload(
                *next(iter_events), remaining=remaining - 1, event_t0=event_t0_ms
            )
            count += 1

    
    def teardown_sequence(self, sequence: useq.MDASequence) -> None:
        """Perform any teardown required after the sequence has been executed."""
        #core = super().mmcore
        #core.stopSequenceAcquisition
        print('DONE: pupil custom teardown')
        #mmcore_dhyana.stopSequenceAcquisition
        pass
    
class MesoEngine(MDAEngine):
    
    # def setup_sequence(self, sequence: useq.MDASequence):
    #     """Setup the hardware for the entire sequence."""
    #     # clear z_correction for new sequence
    #     print('START: meso setup_sequence')
    #     super().setup_sequence(sequence)

    #     return self.get_summary_metadata(mda_sequence=sequence)
    
    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-setup
        print('START: meso custom setup_event')
        super().setup_event(event)  
        print('DONE: meso custom setup_event')

        # do some custom post-setup

    def exec_event(self, event: useq.MDAEvent) -> object:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-execution
        print('START: meso custom exec_event')
        result = super().exec_event(event)  
        print('DONE: meso custom exec_event')

        # do some custom post-execution
        return result
    
    def teardown_sequence(self, sequence: useq.MDASequence) -> None:
        """Perform any teardown required after the sequence has been executed."""
        #core = super().mmcore
        #core.stopSequenceAcquisition
        print('DONE: meso custom teardown')
        #mmcore_thor.stopSequenceAcquisition
        pass
    
if __name__ == "__main__":
    load_dhyana_mmc_params(mmcore_dhyana)
    load_thorcam_mmc_params(mmcore_thor)
    mmcore_dhyana.mda.set_engine(MesoEngine(mmcore_dhyana, use_hardware_sequencing=True))
    mmcore_thor.mda.set_engine(PupilEngine(mmcore_thor, use_hardware_sequencing=True))
    mmcore_dhyana.run_mda(useq.MDASequence(time_plan={"interval": 0, "loops": 20000}))#, output=r'C:/dev/dh.ome.tif')
    mmcore_thor.run_mda(useq.MDASequence(time_plan={"interval": 0, "loops": 20000}))#, output=r'C:/dev/thor.ome.tif')
    