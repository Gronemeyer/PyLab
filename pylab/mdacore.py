import pymmcore_plus

DHYANA_CONFIG = r'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg'
THOR_CONFIG = r'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg'

import logging

import pylab
import useq
from pylab.engine import MesoEngine, PupilEngine

# Disable pymmcore-plus logger
package_logger = logging.getLogger('pymmcore-plus')
# Set the logging level to CRITICAL to suppress lower-level logs
package_logger.setLevel(logging.CRITICAL)

def load_cores():
    mmcore_dhyana: pymmcore_plus.CMMCorePlus = pymmcore_plus.CMMCorePlus(mm_path=r'C:\Program Files\Micro-Manager-2.0')
    mmcore_thor: pymmcore_plus.CMMCorePlus = pymmcore_plus.CMMCorePlus(mm_path=r'C:\Program Files\Micro-Manager-thor')

    mmcore_dhyana.loadSystemConfiguration(DHYANA_CONFIG)

    mmcore_thor.loadSystemConfiguration(THOR_CONFIG)

    mmcore_dhyana.setCircularBufferMemoryFootprint(10000)
    mmcore_thor.setCircularBufferMemoryFootprint(10000)

    logging.info(f"Cores {mmcore_dhyana} and {mmcore_thor} initialized successfully with {mmcore_dhyana.getCircularBufferMemoryFootprint()} and {mmcore_thor.getCircularBufferMemoryFootprint()} memory footprint")   
    return mmcore_dhyana, mmcore_thor

def test_mda(frames: int = 20000):    
    from pymmcore_plus.mda.handlers import OMETiffWriter, ImageSequenceWriter
    from pylab.writer import CustomWriter
    mmcore_dhyana, mmcore_thor = load_cores()
    load_dhyana_mmc_params(mmcore_dhyana)
    load_thorcam_mmc_params(mmcore_thor)
    mmcore_dhyana.mda.set_engine(MesoEngine(mmcore_dhyana, use_hardware_sequencing=True)) 
    mmcore_thor.mda.set_engine(PupilEngine(mmcore_thor, use_hardware_sequencing=True))
    print('running MDA test...')
    mmcore_dhyana.run_mda(useq.MDASequence(time_plan={"interval": 0, "loops": frames}), output=CustomWriter(r'C:/dev/dh.ome.tif'))
    mmcore_thor.run_mda(useq.MDASequence(time_plan={"interval": 0, "loops": frames}), output=CustomWriter(r'C:/dev/thor.ome.tif'))
    print('threads launched')

def load_thorcam_mmc_params(mmcore):
    ''' Load ThorCam MicroManager configuration:
        - loadSystemConfiguration from pylab.mdacore.THOR_CONFIG
        - setROI to 440, 305, 509, 509
        - setExposure to 20
        - use_hardware_sequencing to True
    '''
    
    mmcore.setROI("ThorCam", 440, 305, 509, 509)
    mmcore.setExposure(20)
    mmcore.mda.engine.use_hardware_sequencing = True
    logging.info(f"{mmcore} ThorCam parameters loaded by {load_thorcam_mmc_params.__name__}")

def load_dhyana_mmc_params(mmcore):
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
    mmcore.setProperty('Arduino-Switch', 'Sequence', 'On')
    mmcore.setProperty('Arduino-Shutter', 'OnOff', '1')
    mmcore.setProperty('Dhyana', 'Output Trigger Port', '2')
    mmcore.setProperty('Core', 'Shutter', 'Arduino-Shutter')
    mmcore.setProperty('Dhyana', 'Gain', 'HDR')
    mmcore.setChannelGroup('Channel')
    mmcore.mda.engine.use_hardware_sequencing = True
    logging.info(f"{mmcore} Dhyana parameters loaded by {load_dhyana_mmc_params.__name__}")
    
def load_dev_cores() -> pymmcore_plus.CMMCorePlus:
    core1 = pymmcore_plus.CMMCorePlus()
    core2 = pymmcore_plus.CMMCorePlus()
    core1.loadSystemConfiguration()
    core2.loadSystemConfiguration()
    return core1, core2
    
if __name__ == '__main__':
    test_mda(100)