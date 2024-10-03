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

def start_thorcam():
    print("Starting ThorCam interface...")
    mmc_thor = pymmcore_plus.CMMCorePlus()
    mmc_thor.loadSystemConfiguration(THOR_CONFIG)
    mmc_thor.setROI("ThorCam", 440, 305, 509, 509)
    mmc_thor.setExposure(20)
    mmc_thor.mda.engine.use_hardware_sequencing = True
    pupil_viewer = napari.view_image(mmc_thor.snap(), name='pupil_viewer')
    pupilcam = AcquisitionEngine(pupil_viewer, mmc_thor)
    pupil_viewer.window.add_dock_widget([pupilcam], area='right')
    #viewer.window.add_dock_widget([record_from_buffer, start_sequence])
    #pupil_cam = AcquisitionEngine(viewer, pupil_mmc, PUPIL_JSON)
    #pupil_viewer.window.add_plugin_dock_widget('napari-micromanager')
    #pupil_viewer.window.add_dock_widget([pupil_cam], area='right')
    
    print("ThorCam interface launched.")
    pupil_viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py

def load_dhyana_mmc_params(mmc):
    mmc.loadSystemConfiguration(DHYANA_CONFIG)
    mmc.setProperty('Arduino-Switch', 'Sequence', 'On')
    mmc.setProperty('Arduino-Shutter', 'OnOff', '1')
    mmc.setProperty('Dhyana', 'Output Trigger Port', '2')
    mmc.setProperty('Core', 'Shutter', 'Arduino-Shutter')
    mmc.setProperty('Dhyana', 'Gain', 'HDR')
    mmc.setChannelGroup('Channel')

def start_dhyana(load_params=True, pupil=False):

    print("launching Dhyana interface...")

    viewer = napari.Viewer()
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    mmc = pymmcore_plus.CMMCorePlus.instance()
    print("Starting ThorCam interface...")

    if pupil:
        mmc_thor = pymmcore_plus.CMMCorePlus()
        mmc_thor.loadSystemConfiguration(THOR_CONFIG)
        mmc_thor.setROI("ThorCam", 440, 305, 509, 509)
        mmc_thor.setExposure(20)
        mmc_thor.mda.engine.use_hardware_sequencing = True
        mesofield = AcquisitionEngine(viewer, mmc, mmc_thor)
    else:
        mesofield = AcquisitionEngine(viewer, mmc)

    viewer.window.add_dock_widget([mesofield, load_arduino_led, stop_led], 
                                  area='right', name='Mesofield')
    mmc.mda.engine.use_hardware_sequencing = True
    
    if load_params:
        load_dhyana_mmc_params(mmc)
        print("Dhyana parameters loaded.")
        
    print("Dhyana interface launched.")
    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py
    
    if pupil:
        start_thorcam()
  
    napari.run()
# Launch Napari with the custom widget
# if __name__ == "__main__":
#     print("Starting Sipefield Napari Acquisition Interface...")
#     start_dhyana(load_params=False, pupil=False)
    
