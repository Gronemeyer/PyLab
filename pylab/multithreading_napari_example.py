"""
Multithreading two-way
======================

.. tags:: interactivity
"""
import time
from pymmcore_plus import CMMCorePlus
import numpy as np
import tifffile
import os
from datetime import datetime
import time

import numpy as np
from qtpy.QtWidgets import (
    QGridLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)
import collections
import threading
from tqdm import tqdm
import napari
from napari.qt.threading import thread_worker

###     PARAMETERS

SAVE_DIR = r'C:/dev/sipefield/devOutput'
SAVE_NAME = r'Acquisition_test'
MM_DIR = r'C:/Program Files/Micro-Manager-2.0'
MM_CONFIG = r'C:/dev/devDhyanaCam.cfg'
NIDAQ_DEVICE = 'Dev2'
CHANNELS = ['port2/line0']
IO = 'input' # is the NIDAQ an INput or Output Device?

###     THREADING

frame_queue = collections.deque()
stop_event = threading.Event()

###     MICRO-MANAGER

print("loading Micro-Manager CORE instance...")
mmc = CMMCorePlus()
print("Micro-Manager CORE instance loaded. Initializing configuration file...")
mmc.loadSystemConfiguration(MM_CONFIG)

###     Micro-Manager Configuration

mmc.setProperty('Arduino-Switch', 'Sequence', 'On')
mmc.setProperty('Arduino-Shutter', 'OnOff', '0')
mmc.setProperty('Dhyana', 'Output Trigger Port', '2')
mmc.setProperty('Core', 'Shutter', 'Arduino-Shutter')
mmc.mda.engine.use_hardware_sequencing = True

#### Default parameters for file saving

save_dir = r'C:/dev/sipefield/devOutput'
protocol_id = "devTIFF"
subject_id = "001"
session_id = "01"
num_frames = 1000

class FrameSaver(threading.Thread):
    def __init__(self, frame_deque, stop_event, filename, num_frames):
        super().__init__()
        self.frame_deque = frame_deque
        self.stop_event = stop_event
        self.filename = filename
        self.num_frames = num_frames
        self.lock = threading.Lock()

    def run(self):
        try:
            with tifffile.TiffWriter(self.filename, bigtiff=True) as tiff:
                while not self.stop_event.is_set() or len(self.frame_deque) > 0:
                    frame = None
                    with self.lock:
                        if len(self.frame_deque) > 0:
                            frame = self.frame_deque.popleft()

                    if frame is not None: 
                        try:
                            tiff.write(frame, datetime=True)
                        except Exception as e:
                            print(f"Error while processing frame: {e}")

        except Exception as e:
            print(f"Error while opening TIFF file: {e}")
        finally:
            # Ensure progress bar is properly cleared
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

class Acquisition:
    def __init__(self, mmc, num_frames):
        self.mmc = mmc
        self.num_frames = num_frames

    def start(self):
        self.mmc.startContinuousSequenceAcquisition(0)

    def stop(self):
        self.mmc.stopContinuousSequenceAcquisition()

    def get_frame(self):
        return self.mmc.popNextImage()

    def get_remaining(self):
        return self.mmc.getRemainingImageCount()

    def is_running(self):
        return self.mmc.isSequenceRunning()

    def is_finished(self):
        return self.mmc.getRemainingImageCount() == 0

    def __iter__(self):
        for _ in range(self.num_frames):
            while self.get_remaining() == 0:
                time.sleep(0.1)
            yield self.get_frame()

    def __len__(self):
        return self.num_frames


def acquire(acq):
    acq.start()
    for frame in acq:
        yield frame
    acq.stop()


def start_acquisition(wait_for_trigger=False):
    

    value_sequence = ['4', '16']
    dev = 'Arduino-Switch'
    prop = 'State'
    mmc.loadPropertySequence(dev, prop, value_sequence)
    
    ###THREADING
    output_filename = save_to_bids()
    saving_thread = FrameSaver(frame_queue, stop_event, output_filename, num_frames)
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
    mmc.startContinuousSequenceAcquisition(0) and mmc.startPropertySequence(dev, prop)
    time.sleep(1)  # Allow some time for the camera to start capturing images

    start_time = time.time()  # Start time of the acquisition
    for i in range(num_frames):
        while mmc.getRemainingImageCount() == 0:
            time.sleep(0.1) 
            
        if mmc.getRemainingImageCount() > 0 or mmc.isSequenceRunning():
            frame_queue.append(mmc.popNextImage())


    mmc.stopSequenceAcquisition()
    end_time = time.time()  # End time of the acquisition

    elapsed_time = end_time - start_time  # Total time taken for the acquisition
    framerate = num_frames / elapsed_time  # Calculate the average framerate
    
    ##THREADING
    stop_event.set()
    saving_thread.join()
    ###########

    if wait_for_trigger:
        if nidaq._io == "output": 
        # reset NIDAQ output trigger state
            with NIDAQ() as nidaq:
                nidaq.trigger(False)
        
    print(f"started at ctime: {time.ctime(start_time)} with Average framerate: {framerate} frames per second") # TODO sort out possible 2 second process delay between trigger and acquisition
    return 'done'



class Controller(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QGridLayout()
        self.setLayout(layout)
        self.status = QLabel('Click "Start"', self)
        self.play_btn = QPushButton('Start', self)
        self.abort_btn = QPushButton('Abort!', self)
        self.reset_btn = QPushButton('Reset', self)
        self.progress_bar = QProgressBar()

        layout.addWidget(self.play_btn, 0, 0)
        layout.addWidget(self.reset_btn, 0, 1)
        layout.addWidget(self.abort_btn, 0, 2)
        layout.addWidget(self.status, 0, 3)
        layout.setColumnStretch(3, 1)
        layout.addWidget(self.progress_bar, 1, 0, 1, 4)


def create_connected_widget():
    """Builds a widget that can control a function in another thread."""
    w = Controller()

    # the decorated function now returns a GeneratorWorker object, and the
    # Qthread in which it's running.
    # (optionally pass start=False to prevent immediate running)
    acq = Acquisition(mmc, num_frames)
    worker = acquire(acq)

    w.play_btn.clicked.connect(worker.start)

    # it provides signals like {started, yielded, returned, errored, finished}
    worker.returned.connect(lambda x: w.status.setText(f'worker returned {x}'))
    worker.errored.connect(lambda x: w.status.setText(f'worker errored {x}'))
    worker.started.connect(lambda: w.status.setText('worker started...'))
    worker.aborted.connect(lambda: w.status.setText('worker aborted'))

    # send values into the function (like generator.send) using worker.send
    # abort thread with worker.abort()
    w.abort_btn.clicked.connect(lambda: worker.quit())

    def on_reset_button_pressed():
        # we want to avoid sending into a unstarted worker
        if worker.is_running:
            worker.send(0)

    def on_yield(x):
        # Receive events and update widget progress
        napari.current_viewer().add_image(x)
        #w.progress_bar.setValue(100 * x // num_frames)
        w.status.setText(f'worker yielded {x}')

    def on_start():
        def handle_pause():
            worker.toggle_pause()
            w.play_btn.setText('Pause' if worker.is_paused else 'Continue')

        w.play_btn.clicked.disconnect(worker.start)
        w.play_btn.setText('Pause')
        w.play_btn.clicked.connect(handle_pause)

    def on_finish():
        w.play_btn.setDisabled(True)
        w.reset_btn.setDisabled(True)
        w.abort_btn.setDisabled(True)
        w.play_btn.setText('Done')

    w.reset_btn.clicked.connect(on_reset_button_pressed)
    worker.yielded.connect(on_yield)
    worker.started.connect(on_start)
    worker.finished.connect(on_finish)
    return w

def update_fps(fps):
    """Update fps."""
    viewer = napari.current_viewer()
    viewer.text_overlay.text = f'{fps:1.1f} FPS'
    
if __name__ == '__main__':
    print("Starting Sipefield Napari Acquisition Interface...")

    viewer = napari.Viewer()

    
    w = create_connected_widget()
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    viewer.window.add_dock_widget(w, area="bottom", name="Controller")
    viewer.text_overlay.visible = True
    viewer.window._qt_viewer.canvas.measure_fps(callback=update_fps)

    viewer.update_console(locals()) # https://github.com/napari/napari/blob/main/examples/update_console.py

    napari.run()