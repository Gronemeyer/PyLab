import pymmcore_plus
from pylab.widgets import (
    MDA,
    load_arduino_led,
    stop_led,
)
from pylab.engine import AcquisitionEngine
import napari
from pylab.config import Config

DHYANA_CONFIG = r'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg'
THOR_CONFIG = r'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg'

mmcore_dhyana = pymmcore_plus.CMMCorePlus.instance()
mmcore_thor = pymmcore_plus.CMMCorePlus()

def load_thorcam_mmc_params(mmcore2=mmcore_thor):
    '''Load ThorCam MicroManager configuration:
    - loadSystemConfiguration from pylab.mdacore.THOR_CONFIG
    - setROI to 440, 305, 509, 509
    - setExposure to 20
    - use_hardware_sequencing to True
    '''
    
    print("Loading ThorCam MicroManager configuration...")
    mmcore2.loadSystemConfiguration(THOR_CONFIG)
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
    mmcore1.loadSystemConfiguration(DHYANA_CONFIG)
    mmcore1.setProperty('Arduino-Switch', 'Sequence', 'On')
    mmcore1.setProperty('Arduino-Shutter', 'OnOff', '1')
    mmcore1.setProperty('Dhyana', 'Output Trigger Port', '2')
    mmcore1.setProperty('Core', 'Shutter', 'Arduino-Shutter')
    mmcore1.setProperty('Dhyana', 'Gain', 'HDR')
    mmcore1.setChannelGroup('Channel')
    print("Dhyana MicroManager configuration loaded.")

def load_napari_gui():
    print("launching Dhyana interface...")

    viewer = napari.Viewer()
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    print("Launching Mesofield Interface with ThorCam...")
    mesofield = AcquisitionEngine(viewer, mmcore_dhyana, Config)
    pupil_widget = MDA(mmcore_thor, Config)

    viewer.window.add_dock_widget([mesofield, pupil_widget, load_arduino_led, stop_led], 
                                  area='right', name='Mesofield')

    dev = True
    if dev:
        mmcore_dhyana.loadSystemConfiguration()
        mmcore_thor.loadSystemConfiguration()
    else:
        load_dhyana_mmc_params(mmcore_dhyana)
        load_thorcam_mmc_params(mmcore_thor)
        
    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py

    napari.run()