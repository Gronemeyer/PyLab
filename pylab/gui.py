import napari.layers
import napari.layers.image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari

import pymmcore_plus
#from pymmcore_plus.mda.handlers import OMEZarrWriter, OMETiffWriter, ImageSequenceWriter
#from pymmcore_plus.mda import mda_listeners_connected
from magicgui import magicgui

from pylab.engine import AcquisitionEngine

DHYANA_CONFIG = r'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg'
THOR_CONFIG = r'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg'
    
@magicgui(call_button='Start LED', mmc={'bind': pymmcore_plus.CMMCorePlus.instance()})   
def load_arduino_led(mmc):
    """ Load Arduino-Switch device with a sequence pattern and start the sequence """
    
    mmc.getPropertyObject('Arduino-Switch', 'State').loadSequence(['4', '4', '2', '2'])
    mmc.getPropertyObject('Arduino-Switch', 'State').setValue(4) # seems essential to initiate serial communication
    mmc.getPropertyObject('Arduino-Switch', 'State').startSequence()

    print('Arduino loaded')

@magicgui(call_button='Stop LED', mmc={'bind': pymmcore_plus.CMMCorePlus.instance()})
def stop_led(mmc):
    """ Stop the Arduino-Switch LED sequence """
    
    mmc.getPropertyObject('Arduino-Switch', 'State').stopSequence()

def load_thorcam_mmc_params(mmcore2):
    print("Loading ThorCam MicroManager configuration...")
    mmcore2.loadSystemConfiguration(THOR_CONFIG)
    mmcore2.setROI("ThorCam", 440, 305, 509, 509)
    mmcore2.setExposure(20)
    mmcore2.mda.engine.use_hardware_sequencing = True
    print("ThorCam MicroManager configuration loaded.")

def load_dhyana_mmc_params(mmcore1):
    print("Loading Dhyana MicroManager configuration...")
    mmcore1.loadSystemConfiguration(DHYANA_CONFIG)
    mmcore1.setProperty('Arduino-Switch', 'Sequence', 'On')
    mmcore1.setProperty('Arduino-Shutter', 'OnOff', '1')
    mmcore1.setProperty('Dhyana', 'Output Trigger Port', '2')
    mmcore1.setProperty('Core', 'Shutter', 'Arduino-Shutter')
    mmcore1.setProperty('Dhyana', 'Gain', 'HDR')
    mmcore1.setChannelGroup('Channel')
    print("Dhyana MicroManager configuration loaded.")

def launch_mesofield(load_params=True, pupil=False):

    print("launching Dhyana interface...")

    viewer = napari.Viewer()
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    mmc = pymmcore_plus.CMMCorePlus.instance()

    if pupil:
        mmc_thor = pymmcore_plus.CMMCorePlus()
        load_thorcam_mmc_params(mmc_thor)
        print("Launching Mesofield Interface with ThorCam...")
        mesofield = AcquisitionEngine(viewer, mmc, mmc_thor)
        viewer.add_image(mmc_thor.snap(), name='pupil_cam')
    else:
        mesofield = AcquisitionEngine(viewer, mmc)

    viewer.window.add_dock_widget([mesofield, load_arduino_led, stop_led], 
                                  area='right', name='Mesofield')
    mmc.mda.engine.use_hardware_sequencing = True
    
    if load_params:
        load_dhyana_mmc_params(mmc)
        
    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py

    napari.run()

    
