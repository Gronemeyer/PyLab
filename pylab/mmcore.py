<<<<<<< HEAD
import pymmcore_plus

import logging
=======
from pymmcore_plus import CMMCorePlus
>>>>>>> 7cc5bd730068db5f5d36d9144f98e318f617e1b6

import useq
import logging

<<<<<<< HEAD
=======
from pylab.engines import DevEngine, MesoEngine, PupilEngine

>>>>>>> 7cc5bd730068db5f5d36d9144f98e318f617e1b6
# Disable pymmcore-plus logger
package_logger = logging.getLogger('pymmcore-plus')

# Set the logging level to CRITICAL to suppress lower-level logs
package_logger.setLevel(logging.CRITICAL)

<<<<<<< HEAD
DHYANA_CONFIG = r'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg'
THOR_CONFIG = r'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg'

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
    #from pymmcore_plus.mda.handlers import OMETiffWriter, ImageSequenceWriter
    from pylab.engines import MesoEngine, PupilEngine
    from pylab.io import CustomWriter
    
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
    
# if __name__ == '__main__':
#     test_mda(100)
=======

class MMConfigurator:
    '''MicroManager configuration class.
    
    This class is responsible for loading the MicroManager cores and engines.
    It also provides methods to test the MDA functionality. NOTE: This class
    does not intialize the MicroManager cores until the `load_cores()` method is called.

    `load_cores()` will initialize the MicroManager cores (with parameters if `dev=False`)
    and call the `register_engines()` method to register the engines to the cores. 

    Parameters
    ----------
    parameters : dict
        Dictionary from JSON containing the configuration parameters.
    dev : bool, optional
        Development mode flag, by default False.

    Attributes
    ----------
    development_mode : bool
        Development mode flag.
    mmcore1 : CMMCorePlus
        MicroManager core 1.
    mmcore2 : CMMCorePlus
        MicroManager core 2.
    mm1_path : str
        MicroManager 1 path.
    mm2_path : str
        MicroManager 2 path.
    dhyana_fps : int
        Dhyana camera frames per second.
    thorcam_fps : int
        Thorcam camera frames per second.
    mmc1_configuration_path : str
        MicroManager 1 configuration path.
    mmc2_configuration_path : str
        MicroManager 2 configuration path.
    memory_buffer_size : int
        Memory buffer size.
    
    Methods
    -------
    load_cores()
        Load the MicroManager cores.
    register_engines()
        Register the engines to the cores.
    test_mda(frames: int = 20000)
        Test the MDA functionality.
    load_thorcam_mmc_params(mmcore)
        Load ThorCam MicroManager configuration.
    load_dhyana_mmc_params(mmcore)
        Load Dhyana MicroManager configuration.
    load_dev_cores()
        Load development cores.
    
    '''

    def __init__(self, parameters: dict, dev: bool = False):
        self.development_mode: bool = dev

        self.mmcore1: CMMCorePlus = None
        self.mmcore2: CMMCorePlus = None

        self.mm1_path: str = parameters.get('mmc1_path', 'C:/Program Files/Micro-Manager-2.0gamma')
        self.mm2_path: str = parameters.get('mmc2_path', 'C:/Program Files/Micro-Manager-thor')

        self.mmc1_configuration_path: str = parameters.get('mmc1_configuration_path', None)
        self.mmc2_configuration_path: str = parameters.get('mmc2_configuration_path', None)

        self.dhyana_fps: int = parameters.get('dhyana_fps', 50)
        self.thorcam_fps: int = parameters.get('thorcam_fps', 34)
        self.memory_buffer_size: int = parameters.get('memory_buffer_size', 10000)

    def load_cores(self):
        '''Load the MicroManager Cores from MM Application Path (str) and MM Configuration Path (str)'''

        if self.development_mode:
            self.mmcore1, self.mmcore2 = self.load_dev_cores()
        else:
            self.mmcore1 = CMMCorePlus(self.mm1_path)
            self.mmcore2 = CMMCorePlus(self.mm2_path)

            if self.mmc1_configuration_path:
                self.mmcore1.loadSystemConfiguration(self.mmc1_configuration_path)
            if self.mmc2_configuration_path:
                self.mmcore2.loadSystemConfiguration(self.mmc2_configuration_path)

            self.mmcore1.setCircularBufferMemoryFootprint(self.memory_buffer_size)
            self.mmcore2.setCircularBufferMemoryFootprint(self.memory_buffer_size)

            logging.info(
                f"Cores initialized with memory footprints: "
                f"{self.mmcore1.getCircularBufferMemoryFootprint()} MB and "
                f"{self.mmcore2.getCircularBufferMemoryFootprint()} MB"
            )

        self.register_engines()

        return self.mmcore1, self.mmcore2

    def register_engines(self):
        '''Register the Custom Pymmcore-Plus MDAEngines to the Cores.'''

        if self.development_mode:
            self.mmcore1.register_mda_engine(DevEngine(self.mmcore1, use_hardware_sequencing=True))
            self.mmcore2.register_mda_engine(DevEngine(self.mmcore2, use_hardware_sequencing=True))
            logging.info("Development Engines registered to cores")

        else:
            self.mmcore1.register_mda_engine(MesoEngine(self.mmcore1, use_hardware_sequencing=True))
            self.mmcore2.register_mda_engine(PupilEngine(self.mmcore2, use_hardware_sequencing=True))
            logging.info("Engines registered to cores")

    def test_mda(self, frames: int = 20000):    
        from pylab.engines import MesoEngine, PupilEngine
        from pylab.io import CustomWriter

        self.load_cores()
        
        self.load_dhyana_mmc_params(self.mmcore1)
        self.load_thorcam_mmc_params(self.mmcore2)
        
        self.mmcore1.mda.set_engine(MesoEngine(self.mmcore1, use_hardware_sequencing=True)) 
        self.mmcore2.mda.set_engine(PupilEngine(self.mmcore2, use_hardware_sequencing=True))
        
        print('Running MDA test...')
        self.mmcore1.run_mda(
            useq.MDASequence(time_plan={"interval": 0, "loops": frames}),
            output=CustomWriter(r'C:/dev/dh.ome.tif')
        )
        self.mmcore2.run_mda(
            useq.MDASequence(time_plan={"interval": 0, "loops": frames}),
            output=CustomWriter(r'C:/dev/thor.ome.tif')
        )
        print('Threads launched')

    def load_thorcam_mmc_params(self, mmcore):
        """Load ThorCam MicroManager configuration."""
        mmcore.setROI("ThorCam", 440, 305, 509, 509)
        mmcore.setExposure(20)
        mmcore.mda.engine.use_hardware_sequencing = True
        logging.info(f"{mmcore} ThorCam parameters loaded by {self.load_thorcam_mmc_params.__name__}")

    def load_dhyana_mmc_params(self, mmcore):
        """Load Dhyana MicroManager configuration."""
        print("Loading Dhyana MicroManager configuration...")
        mmcore.setProperty('Arduino-Switch', 'Sequence', 'On')
        mmcore.setProperty('Arduino-Shutter', 'OnOff', '1')
        mmcore.setProperty('Dhyana', 'Output Trigger Port', '2')
        mmcore.setProperty('Core', 'Shutter', 'Arduino-Shutter')
        mmcore.setProperty('Dhyana', 'Gain', 'HDR')
        mmcore.setChannelGroup('Channel')
        mmcore.mda.engine.use_hardware_sequencing = True
        logging.info(f"{mmcore} Dhyana parameters loaded by {self.load_dhyana_mmc_params.__name__}")
        
    @staticmethod
    def load_dev_cores():
        core1 = CMMCorePlus()
        core2 = CMMCorePlus()
        core1.loadSystemConfiguration()
        core2.loadSystemConfiguration()
        logging.info("Development Cores loaded")
        return core1, core2

>>>>>>> 7cc5bd730068db5f5d36d9144f98e318f617e1b6
