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


from magicgui import magic_factory, magicgui, widgets
from magicgui.tqdm import trange

from typing import TYPE_CHECKING
from itertools import cycle

if TYPE_CHECKING:
    import napari

from typing import Any, Dict
import json

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
    def __init__(self, frame_deque, stop_event, num_frames, file_dir):
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


def save_to_bids(save_dir: str, protocol_id: str, subject_id: str, session_id: str) -> str:
    """
    Create a directory path based on BIDS (Brain Imaging Data Structure) standards and return the path for a new TIFF file.
    
    Parameters:
    - save_dir (str): Base directory for saving the BIDS formatted data.
    - protocol_id (str): Identifier for the protocol.
    - subject_id (str): Identifier for the subject.
    - session_id (str): Identifier for the session.

    Returns:
    - str: The file path where the new TIFF file should be saved.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  # Get current timestamp
    anat_dir = os.path.join(save_dir, f"{protocol_id}-{subject_id}", f"ses-{session_id}", "anat")
    os.makedirs(anat_dir, exist_ok=True)  # Create the directory if it doesn't exist
    filename = os.path.join(anat_dir, f"sub-{subject_id}_ses-{session_id}_{timestamp}.tiff")
    print(f"File will be saved to: {filename}")
    return filename

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
        print("Sequence Stopped from LED Arudino Class")
        
    def _load_device(self, device):
        #mmc.setSerialPortCommand('COM12', '28', 'f')
        mmc.deviceBusy('Arduino-Switch')



class Parameters:
    def __init__(self, file_path=None):
        self.file_path = file_path
        self.params = {}
        if file_path:
            self.load_parameters()
        
    def load_parameters(self):
        import json
        
        if self.file_path:
            with open(self.file_path, 'r') as file:
                self.params = json.load(file)
                    
    def save_parameters(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.params, file)
            
    def set_global_parameters(self):
        for key, value in self.params.items():
            globals()[key] = value
    
    def __getitem__(self, key):
        return self.params[key]       

params = Parameters()

# Create a magicgui function to load the JSON file
@magicgui(call_button="Load JSON")
def load_json(file_path: str):
    params.file_path = file_path
    params.load_parameters()
    # Clear existing fields
    for widget in parameter_gui:
        parameter_gui.remove(widget)
    # Dynamically add fields to the GUI based on the loaded parameters
    for key, value in params.params.items():
        parameter_gui.append(key, value)

# Create a magicgui function for the parameters
@magicgui(call_button="Save Parameters")
def parameter_gui(**kwargs):
    for key, value in params.params.items():
        kwargs[key] = value
    return kwargs

# Function to start the MDA sequence
@magicgui(
    call_button="Start Acquisition",
    layout="vertical",
    num_frames={"widget_type": "SpinBox", "min": 0, "max": 100000, "step": 1},
    wait_for_trigger={"widget_type": "CheckBox"}
)
def acquisition_widget(
    wait_for_trigger: bool, 
    save_dir: str = save_dir, 
    num_frames: int = num_frames, 
    protocol_id: str = protocol_id, 
    subject_id: str = subject_id, 
    session_id: str = session_id):
    @Arduino(mmc)
    def start_acquisition(arduino):
        print("Acquisition started...")
        # Setup frame queue and threading
        filename = save_to_bids(save_dir, protocol_id, subject_id, session_id)
        frame_queue = collections.deque()
        stop_event = threading.Event()
        saving_thread = FrameSaver(frame_queue, stop_event, num_frames, file_dir=filename)
        saving_thread.start()

        # Acquisition logic goes here
        if wait_for_trigger:
            with NIDAQ() as nidaq:
                # Wait for an external trigger
                nidaq.wait_for_trigger()  # Assuming you define this method

        arduino.start_sequence()
        mmc.startContinuousSequenceAcquisition(0)
        for i in trange(num_frames):
            while mmc.getRemainingImageCount() == 0:
                time.sleep(0.1) 
            if mmc.getRemainingImageCount() > 0 or mmc.isSequenceRunning():
                frame_queue.append(mmc.popNextImageAndMD())

        mmc.stopSequenceAcquisition()
        arduino.stop_sequence()
        stop_event.set()
        saving_thread.join()
        print("Acquisition completed.")

    return start_acquisition()

def main():
    
    viewer = napari.Viewer()

    viewer.window.add_dock_widget([acquisition_widget], area='right')
    napari.run()
    load_json.show()


if __name__ == "__main__":
    main()
