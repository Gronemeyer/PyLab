from pymmcore_plus import CMMCorePlus

import useq
import logging

from pylab.engines import DevEngine, MesoEngine, PupilEngine

# Disable pymmcore-plus logger
package_logger = logging.getLogger('pymmcore-plus')

# Set the logging level to CRITICAL to suppress lower-level logs
package_logger.setLevel(logging.CRITICAL)


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
        
        self.meso_engine: MesoEngine = None
        self.pupil_engine: PupilEngine = None
        self.dev_engine: DevEngine = None

        self.mm1_path: str = parameters.get('mmc1_path', 'C:/Program Files/Micro-Manager-2.0gamma')
        self.mm2_path: str = parameters.get('mmc2_path', 'C:/Program Files/Micro-Manager-thor')

        self.mmc1_configuration_path: str = parameters.get('mmc1_configuration_path', None)
        self.mmc2_configuration_path: str = parameters.get('mmc2_configuration_path', None)

        self.dhyana_fps: int = parameters.get('dhyana_fps', 50)
        self.thorcam_fps: int = parameters.get('thorcam_fps', 34)
        self.memory_buffer_size: int = parameters.get('memory_buffer_size', 10000)
        
        self.encoder_params: dict = parameters.get('encoder', None)


    def load_cores(self):
        '''Load the MicroManager Cores from MM Application Path (str) and MM Configuration Path (str)'''

        if self.development_mode:
            self.mmcore1, self.mmcore2 = self.load_dev_cores()
        else:
            self.mmcore1 = CMMCorePlus(self.mm1_path)
            self.mmcore2 = CMMCorePlus(self.mm2_path)

            if self.mmc1_configuration_path:
                self.load_dhyana_mmc_params(self.mmcore1, self.mmc1_configuration_path)
            if self.mmc2_configuration_path:
                self.load_thorcam_mmc_params(self.mmcore2, self.mmc2_configuration_path)

            self.mmcore1.setCircularBufferMemoryFootprint(self.memory_buffer_size)
            self.mmcore2.setCircularBufferMemoryFootprint(self.memory_buffer_size)

            logging.info(
                f"Cores initialized with memory footprints: "
                f"{self.mmcore1.getCircularBufferMemoryFootprint()} MB and "
                f"{self.mmcore2.getCircularBufferMemoryFootprint()} MB"
            )

        self.register_engines()

        return self.mmcore1, self.mmcore2

    def register_engines(self) -> None:
        '''Register the Custom Pymmcore-Plus MDAEngines to the Cores.'''

        self.meso_engine = MesoEngine(self.mmcore1, use_hardware_sequencing=True)
        self.pupil_engine = PupilEngine(self.mmcore2, use_hardware_sequencing=True) 
        #self.dev_engine = DevEngine(self.mmcore1, use_hardware_sequencing=True)

        if not self.development_mode:
            self.mmcore1.register_mda_engine(self.meso_engine)
            logging.info(f"MMConfigurator: {self.meso_engine} registered to {self.mmcore1}")       
            self.mmcore2.register_mda_engine(self.pupil_engine)
            logging.info(f"MMConfigurator: {self.pupil_engine} registered to {self.mmcore2}")
        else:
            self.mmcore1.register_mda_engine(self.meso_engine)
            logging.info(f"MMConfigurator: {self.dev_engine} registered to {self.mmcore1}")
            self.mmcore2.register_mda_engine(self.pupil_engine)

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

    @staticmethod
    def load_thorcam_mmc_params(mmcore, config_path):
        """Load ThorCam MicroManager configuration."""
        print(f"Loading ThorCam MicroManager {mmcore} configuration {config_path}...")
        mmcore.loadSystemConfiguration(config_path)
        mmcore.setROI("ThorCam", 440, 305, 509, 509)
        mmcore.setExposure(20)
        mmcore.mda.engine.use_hardware_sequencing = True
        logging.info(f"{mmcore} ThorCam parameters loaded with configuration file {config_path}")

    @staticmethod
    def load_dhyana_mmc_params(mmcore, config_path):
        """Load Dhyana MicroManager configuration."""
        print(f"Loading Dhyana MicroManager {mmcore} configuration {config_path}...")
        mmcore.loadSystemConfiguration(config_path)
        mmcore.setProperty('Arduino-Switch', 'Sequence', 'On')
        mmcore.setProperty('Arduino-Shutter', 'OnOff', '1')
        mmcore.setProperty('Dhyana', 'Output Trigger Port', '2')
        mmcore.setProperty('Core', 'Shutter', 'Arduino-Shutter')
        #mmcore.setProperty('Dhyana', 'Gain', 'HDR')
        mmcore.setChannelGroup('Channel')
        mmcore.mda.engine.use_hardware_sequencing = True
        logging.info(f"{mmcore} Dhyana parameters loaded with configuration file {config_path}")
        
    @staticmethod
    def load_dev_cores():
        core1 = CMMCorePlus()
        core2 = CMMCorePlus()
        core1.loadSystemConfiguration()
        core2.loadSystemConfiguration()
        logging.info("Development Cores loaded")
        return core1, core2

