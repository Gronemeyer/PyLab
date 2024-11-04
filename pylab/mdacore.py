import pymmcore_plus

DHYANA_CONFIG = r'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg'
THOR_CONFIG = r'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg'

pymmcore_plus.configure_logging(stderr_level=5, file_level="DEBUG")

def load_cores():
    mmcore_dhyana: pymmcore_plus.CMMCorePlus = pymmcore_plus.CMMCorePlus(mm_path=r'C:\Program Files\Micro-Manager-2.0')
    mmcore_thor: pymmcore_plus.CMMCorePlus = pymmcore_plus.CMMCorePlus(mm_path=r'C:\Program Files\Micro-Manager-thor')
    mmcore_dhyana.loadSystemConfiguration(DHYANA_CONFIG)
    mmcore_thor.loadSystemConfiguration(THOR_CONFIG)

def load_thorcam_mmc_params(mmcore):
    ''' Load ThorCam MicroManager configuration:
        - loadSystemConfiguration from pylab.mdacore.THOR_CONFIG
        - setROI to 440, 305, 509, 509
        - setExposure to 20
        - use_hardware_sequencing to True
    '''
    
    print("Loading ThorCam MicroManager configuration...")
    mmcore.setROI("ThorCam", 440, 305, 509, 509)
    mmcore.setExposure(20)
    mmcore.mda.engine.use_hardware_sequencing = True
    print("ThorCam MicroManager configuration loaded.")

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
    
def load_dev_cores() -> pymmcore_plus.CMMCorePlus:
    core1 = pymmcore_plus.CMMCorePlus()
    core2 = pymmcore_plus.CMMCorePlus()
    core1.loadSystemConfiguration()
    core2.loadSystemConfiguration()
    return core1, core2
    

    