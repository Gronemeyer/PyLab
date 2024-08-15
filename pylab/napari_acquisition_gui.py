from pymmcore_plus import CMMCorePlus
import pymmcore_plus
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
from itertools import cycle

if TYPE_CHECKING:
    import napari


pymmcore_plus.configure_logging(file_level="DEBUG", stderr_level="DEBUG")

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
mmc.setProperty('Dhyana', 'Gain', 'HDR')

# Default parameters for file saving
save_dir = r'C:/dev/sipefield/devOutput'
protocol_id = "devTIFF"
subject_id = "001"
session_id = "01"
num_frames = 1000
pattern = ['6', '4', '16', '16']


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
            with tifffile.TiffWriter(self.filename, bigtiff=True, ome=True) as tiff:
                with tqdm(total=self.num_frames, desc='Saving Frames') as pbar:
                    while not self.stop_event.is_set() or len(self.frame_deque) > 0:
                        frame = None
                        with self.lock:
                            if len(self.frame_deque) > 0:
                                frame, meta = self.frame_deque.popleft()

                        if frame is not None: 
                            try:
                                tiff.write(frame, datetime=True, software="Micro-Manager", metadata=meta)
                                pbar.update(1)
                            except Exception as e:
                                print(f"Error while processing frame: {e}")

        except Exception as e:
            print(f"Error while opening TIFF file: {e}")
        finally:
            self.frame_queue = collections.deque()

# class LiveViewer(threading.Thread):
#     def __init__(self, frame_deque, stop_event):
#         super().__init__()
#         self.frame_deque = frame_deque
#         self.stop_event = stop_event

#     def update layer(self, frame):
#         napari.current_viewer.layer(frame, name='Final Acquisition')

#     @thread_worker(connect={"yielded": lambda x: napari.current_viewer.(x, name='Final Acquisition')})
#     def run(self):
#         try:
#             while not self.stop_event.is_set() or len(self.frame_deque) > 0:
#                 frame = None
#                 with self.lock:
#                     if len(self.frame_deque) > 0:
#                         yield self.frame_deque.pop()
#                 if frame is not None:
#         except Exception as e:
#             print(f"Error while displaying live acquisition: {e}")
#         finally:
#             self.frame_deque = collections.deque()

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

class Arduino():
    def __init__(self, mmc):
        self.mmc = mmc
        self._device = 'Arduino-Switch'
        self.pattern = ['4', '4', '16', '16']
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            self.load_sequence(self.pattern)
            self._load_device(self._device)
            result = func(self, *args, **kwargs)
            return result
        return wrapper
    
    def switch_blue(self):
        mmc.getPropertyObject(self._device, 'State').setValue(4)
        
    def switch_violet(self):
        mmc.getPropertyObject(self._device, 'State').setValue(16)
        
    def load_sequence(self, sequence):
        self.pattern = sequence # Load the sequence pattern
        self._load_device(self._device) # Load the Arduino-Switch device    
        mmc.getPropertyObject(self._device, 'State').loadSequence(self.pattern)
            
    def start_sequence(self):
        mmc.getPropertyObject(self._device, 'State').startSequence()
    
    def stop_sequence(self):
        mmc.getPropertyObject(self._device, 'State').stopSequence()
        
    def _load_device(self, device):
        mmc.deviceBusy('Arduino-Switch')

# Function to start the MDA sequence
@Arduino(mmc)
def start_acquisition(arduino, mmc, wait_for_trigger, pattern=pattern):

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
    
    print(time.ctime(time.time()), ' trigger received, starting acquisition')
    arduino.start_sequence()
    saving_thread.start() # Start the thread to save the frames to disk
    mmc.startContinuousSequenceAcquisition(0) # Start the camera stream to internal image buffer of MMC
    time.sleep(1)  # Allow some time for the camera to start capturing images to fill the buffer

    start_time = time.time()  # Python arbitrary start time of the acquisition
    for i in range(num_frames):
        
        while mmc.getRemainingImageCount() == 0:
            time.sleep(0.1) 
            
        if mmc.getRemainingImageCount() > 0 or mmc.isSequenceRunning():
            frame_queue.append(mmc.popNextImageAndMD(slice=i))

    mmc.stopSequenceAcquisition()
    arduino.stop_sequence()

    end_time = time.time()  # End time of the acquisition

    elapsed_time = end_time - start_time  # Total python arbitrary time taken for the acquisition
    framerate = num_frames / elapsed_time  # Calculate the average arbitrary framerate

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
    return

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
        start_acquisition(mmc, self._trigger_mode)
        

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

    viewer.window.add_plugin_dock_widget('napari-micromanager')
    viewer.window.add_dock_widget(MyWidget(viewer), area='bottom')
    napari.run()
    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py

# Launch Napari with the custom widget
if __name__ == "__main__":
    print("Starting Sipefield Napari Acquisition Interface...")
    start_napari()
