from pymmcore_plus import CMMCorePlus
import numpy as np
import tifffile
import os
from datetime import datetime
import time

from qtpy.QtWidgets import (
    QCheckBox, 
    QPushButton, 
    QWidget, 
    QVBoxLayout, 
    QLineEdit, 
    QFormLayout
)
import nidaqmx
import napari
from napari import Viewer, run
from napari.qt import thread_worker
import collections
import threading
from tqdm import tqdm

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import napari




SAVE_DIR = r'C:/dev/sipefield/devOutput'
SAVE_NAME = r'Acquisition_test'
MM_DIR = r'C:/Program Files/Micro-Manager-2.0'
MM_CONFIG = r'C:/dev/devDhyanaCam.cfg'
NIDAQ_DEVICE = 'Dev2'
CHANNELS = ['port2/line0']
IO = 'input' # is the NIDAQ an INput or Output Device?

###THREADING
frame_queue = collections.deque()
stop_event = threading.Event()
############

print("loading Micro-Manager CORE instance...")
mmc = CMMCorePlus(mm_path=MM_DIR)
print("Micro-Manager CORE instance loaded. Initializing configuration file...")
mmc.loadSystemConfiguration(MM_CONFIG)

mmc.setProperty('Arduino-Switch', 'Sequence', 'On')
mmc.setProperty('Arduino-Shutter', 'OnOff', '0')
mmc.setProperty('Dhyana', 'Output Trigger Port', '2')
mmc.setProperty('Core', 'Shutter', 'Arduino-Shutter')

# Default parameters for file saving
save_dir = r'C:/dev/sipefield/devOutput'
protocol_id = "devTIFF"
subject_id = "001"
session_id = "01"
num_frames = 1000

class NIDAQ:
    '''
    Class to handle NI-DAQ operations for digital output. The class is used as a context manager to ensure proper initialization and cleanup of the NI-DAQ task. 
    The send_signal method is used to send a digital signal to the specified channels
    The trigger method is a convenience method to send a high signal followed by a low signal to the channels.
    
    Parameters:
    - device_name (str): Name of the NI-DAQ device (default: 'Dev2')
    - channels (list): List of channel names to use for digital output (default: ['port0/line0', 'port0/line1'])
    '''
    def __init__(self, device_name=NIDAQ_DEVICE, channels=CHANNELS, io=IO):
        self.device_name = device_name
        self.channels = channels if channels else ['port0/line0', 'port0/line1']
        self.task = None
        self._io = io 

    def __enter__(self):
        """During With context, generate input or output channels according to parameter 'io' """
        self.task = nidaqmx.Task()
        if self._io == "input": # Create input channel(s)
            for channel in self.channels:
                full_channel_name = f'{self.device_name}/{channel}'
                self.task.di_channels.add_di_chan(full_channel_name)
            return self
        else: # Create output channel(s)
            for channel in self.channels:
                full_channel_name = f'{self.device_name}/{channel}'
                self.task.do_channels.add_do_chan(full_channel_name)
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the task() on exit"""
        if self.task:
            self.task.close()

    def send_signal(self, signal_values):
        if not self.task:
            raise RuntimeError("Task not initialized. Use 'with NIDAQ(...) as nidaq:' context.")
        self.task.write(signal_values)
        print(f"Signal {'High' if all(signal_values) else 'Low'} on {self.device_name} for channels {self.channels}")

    def trigger(self, state):
        signal_values = [state] * len(self.channels)
        self.send_signal(signal_values)
        
    def pulse(self, duration=1):
        self.trigger(True)
        time.sleep(duration)
        self.trigger(False)

@mmc.events.devicePropertyChanged('Arduino-Switch', 'State').connect
class FrameSaver(threading.Thread):
    def __init__(self, frame_deque, stop_event, num_frames):
        super().__init__()
        self.frame_deque = frame_deque
        self.stop_event = stop_event
        self.filename = save_to_bids()
        self.num_frames = num_frames
        self.lock = threading.Lock()

    def run(self):
        try:
            with tifffile.TiffWriter(self.filename, bigtiff=True) as tiff:
                with tqdm(total=self.num_frames, desc='Saving Frames') as pbar:
                    while not self.stop_event.is_set() or len(self.frame_deque) > 0:
                        frame = None
                        with self.lock:
                            if len(self.frame_deque) > 0:
                                frame = self.frame_deque.popleft()

                        if frame is not None: 
                            try:
                                tiff.write(frame, datetime=True)
                                pbar.update(1)
                            except Exception as e:
                                print(f"Error while processing frame: {e}")

        except Exception as e:
            print(f"Error while opening TIFF file: {e}")
        finally:
            # Ensure progress bar is properly cleared
            pbar.close()
            self.frame_queue = collections.deque()

def save_to_bids(path=SAVE_DIR):
    """
    Make a BIDS formatted directory 
    
    Accesses global variables for protocol_id, subject_id, session_id
    
    Organizes the directory structure as follows:
    path/protocol_id-subject_id/ses-session_id/anat
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') # get current timestamp
    anat_dir = os.path.join(path, f"{protocol_id}-{subject_id}", f"ses-{session_id}", "anat")
    os.makedirs(anat_dir, exist_ok=True) # create the directory if it doesn't exist
    filename = os.path.join(anat_dir, f"sub-{subject_id}_ses-{session_id}_{timestamp}.tiff")
    return filename # returns the filename

def load_sequence():
    value_sequence = ['4', '16', '4', '16', '4', '16', '4', '16', '4', '16', '4', '16']
    dev = 'Arduino-Switch'
    prop = 'State'
    mmc.loadDevice('Arduino-Switch', 'Arduino', dev)
    mmc.loadPropertySequence(dev, prop, value_sequence)

class Arduino():
    def __init__(self, mmc):
        self.switch = 'Arduino-Switch'
        self.shutter = 'Arduino-Shutter'
        self.switch_state = mmc.getPropertyObject(self.switch, 'State')
        self.shutter_state = mmc.getPropertyObject(self.shutter, 'OnOff')
        self.switch_state = mmc.getProperty(self.switch, self.switch_state)
        self.shutter_state = mmc.getProperty(self.shutter, self.shutter_state)
        self.state = mmc.getProperty(self.switch, self.switch_state)
        
    def switch_blue(self):
        mmc.setProperty(self.switch, self.switch_state, 4)
        
    def switch_violet(self):
        mmc.setProperty(self.switch, self.switch_state, 16)
        
    def shutter_open(self):
        self.shutter_state.setValue('1')
        
    def shutter_close(self):
        mmc.setProperty(self.shutter, self.shutter_state, 0)
        
    def load_device(self, device):
        if device == 'Arduino-Switch':
            mmc.loadDevice('Arduino-Switch')
        elif device == 'Arduino-Shutter':
            mmc.loadDevice('Arduino-Shutter')

# Function to start the MDA sequence
def start_acquisition(wait_for_trigger):
    
    load_sequence()
    dev = 'Arduino-Switch'
    prop = 'State'
    ###THREADING
    saving_thread = FrameSaver(frame_queue, stop_event, num_frames)
    ############

    if wait_for_trigger:
        with NIDAQ() as nidaq:
            if nidaq._io == "output": 
                # reset NIDAQ output trigger state
                with NIDAQ() as nidaq:
                    nidaq.trigger(False)
            else:
                print("Waiting for trigger...")

                while True:
                    try:
                        if nidaq.task.read(): 
                            break
                        elif not nidaq.task.read(): # While input signal is not True
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Error while waiting for trigger. Ensure NIDAQ tasks have been properly reset: {e}")
    
    saving_thread.start() # Start the thread to save the frames to disk

    print(time.ctime(time.time()), ' trigger received, starting acquisition')
    mmc.startPropertySequence(dev, prop)
    mmc.startContinuousSequenceAcquisition(0) 
    time.sleep(1)  # Allow some time for the camera to start capturing images

    start_time = time.time()  # Start time of the acquisition
    for i in range(num_frames):
        
        while mmc.getRemainingImageCount() == 0:
            time.sleep(0.1) 
            
        if mmc.getRemainingImageCount() > 0 or mmc.isSequenceRunning():
            frame_queue.append(mmc.popNextImage())

    mmc.stopSequenceAcquisition()
    mmc.stopPropertySequence(dev, prop)
    end_time = time.time()  # End time of the acquisition

    elapsed_time = end_time - start_time  # Total time taken for the acquisition
    framerate = num_frames / elapsed_time  # Calculate the average framerate

    ###THREADING
    stop_event.set()
    saving_thread.join()
    ############

    if wait_for_trigger:
        if nidaq._io == "output": 
        # reset NIDAQ output trigger state
            with NIDAQ() as nidaq:
                nidaq.trigger(False)
        
    print(f"started at ctime: {time.ctime(start_time)} with Average framerate: {framerate} frames per second") # TODO sort out possible 2 second process delay between trigger and acquisition
    
    # Load the final TIFF stack into the viewer
    # viewer.add_image(np.array(images), name='Final Acquisition') #2024-08-04 This line adds several minutes after saving


# Custom widget class for Napari
class MyWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.layout = QVBoxLayout(self)
        self._trigger_mode = False
        
        # ==== Form layout for parameters ==== #
        self.form_layout = QFormLayout()
        
        # ==== Input fields for parameters ==== #
        self.save_dir_input = QLineEdit(save_dir)
        self.protocol_id_input = QLineEdit(protocol_id)
        self.subject_id_input = QLineEdit(subject_id)
        self.session_id_input = QLineEdit(session_id)
        self.num_frames_input = QLineEdit(str(num_frames))
        
        # === Labels for input fields === #
        self.form_layout.addRow('Save Directory:', self.save_dir_input)
        self.form_layout.addRow('Protocol ID:', self.protocol_id_input)
        self.form_layout.addRow('Subject ID:', self.subject_id_input)
        self.form_layout.addRow('Session ID:', self.session_id_input)
        self.form_layout.addRow('Number of Frames:', self.num_frames_input)
        self.layout.addLayout(self.form_layout) # Add the form layout to the main layout
        
        # === Checkbox for trigger mode === #
        self.checkbox = QCheckBox("Wait for Trigger")
        self.checkbox.setCheckState(False)
        self.checkbox.stateChanged.connect(self.set_trigger_mode)
        self.layout.addWidget(self.checkbox)
        
        # === Start Acquisition button === #
        self.button = QPushButton("Start Acquisition")
        self.button.clicked.connect(self.start_acquisition_with_params)
        self.layout.addWidget(self.button)

        # === Test Trigger button === #
        self.button = QPushButton("Test NiDAQ Trigger")
        self.button.clicked.connect(self.test_trigger)
        self.layout.addWidget(self.button) 
        
    def start_acquisition_with_params(self):
        global save_dir, protocol_id, subject_id, session_id, num_frames
        save_dir = self.save_dir_input.text()
        protocol_id = self.protocol_id_input.text()
        subject_id = self.subject_id_input.text()
        session_id = self.session_id_input.text()
        num_frames = int(self.num_frames_input.text())
        start_acquisition(self._trigger_mode)
        

    def test_trigger(self):
        with NIDAQ() as nidaq:
            nidaq.pulse()
            
    def set_trigger_mode(self, checked): # TODO have this change the acquisition trigger method
        if checked:
            self._trigger_mode = True
        else:
            self._trigger_mode = False

def update_fps(fps):
    """Update fps."""
    viewer = napari.current_viewer()
    viewer.text_overlay.text = f'{fps:1.1f} FPS'
    
# Function to start Napari with the custom widget
def start_napari():
    
    print("launching interface...")
    viewer = Viewer()
    viewer.text_overlay.visible = True
    viewer.window._qt_viewer.canvas.measure_fps(callback=update_fps)
    mmc.mda.engine.use_hardware_sequencing = True

    # Activate live view
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    viewer.window.add_dock_widget(MyWidget(viewer), area='bottom')
    run()
    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py

# Launch Napari with the custom widget
if __name__ == "__main__":
    print("Starting Sipefield Napari Acquisition Interface...")
    start_napari()
