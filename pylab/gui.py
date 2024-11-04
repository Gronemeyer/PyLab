import datetime
from itertools import count
from pathlib import Path
import numpy as np
import pandas as pd

from qtpy.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout,
)

from pymmcore_plus import CMMCorePlus
from useq import MDAEvent

# Necessary modules for the IPython console
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

from pylab.widgets import MDA, ConfigController
from pylab.config import ExperimentConfig

class MainWindow(QMainWindow):
    def __init__(self, core_object1: CMMCorePlus, core_object2: CMMCorePlus, cfg: ExperimentConfig):
        super().__init__()
        self.setWindowTitle("Main Widget with Two MDA Widgets")
        self._meso_counter = count()
        self._pupil_counter = count()
        self._dhyana_metadata: dict[str, dict] = {}
        self._thor_metadata: dict[str, dict] = {}

        # Create a central widget and set it as the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set layout for the central widget
        main_layout = QHBoxLayout(central_widget)
        mda_layout = QVBoxLayout()
        
        # Create two instances of MDA widget
        self.dhyana_gui = MDA(core_object1, cfg)
        self.thor_gui = MDA(core_object2, cfg)
        self.config = ConfigController(core_object1, cfg)
        
        # Add MDA widgets to the layout
        mda_layout.addWidget(self.dhyana_gui)
        mda_layout.addWidget(self.thor_gui)
        main_layout.addLayout(mda_layout)
        main_layout.addWidget(self.config)
        
        self.init_console()
        toggle_console_action = self.menuBar().addAction("Toggle Console")
        toggle_console_action.triggered.connect(self.toggle_console)
        
        self.dhyana_gui.mmc.mda.events.sequenceStarted.connect(self._dhyana_mda_start)
        self.thor_gui.mmc.mda.events.sequenceStarted.connect(self._thor_mda_start)
        self.dhyana_gui.mmc.mda.events.frameReady.connect(self._dhyana_save_frame_metadata)
        self.thor_gui.mmc.mda.events.frameReady.connect(self._thor_save_frame_metadata)
        #self.dhyana_gui.mmc.mda.events.sequenceFinished.connect(self.save_meso_metadata)
        #self.thor_gui.mmc.mda.events.sequenceFinished.connect(self.save_pupil_metadata)

    def _dhyana_mda_start(self) -> None:
        """Called when the MDA sequence starts for Dhyana camera."""
        self._meso_counter = count() # reset iterative counter
        self._dhyana_metadata = {} # reset frame metadata storage
        
    def _thor_mda_start(self) -> None:
        """Called when the MDA sequence starts for Dhyana camera."""
        self._pupil_counter = count() # reset iterative counter
        self._dhyana_metadata = {} # reset frame metadata storage

    def _dhyana_save_frame_metadata(self, image: np.ndarray, event: MDAEvent, frame_metadata: dict) -> None:
        """Called each time a frame is acquired."""
        frame_index = next(self._meso_counter)
        self._dhyana_metadata[frame_index] = frame_metadata
        
    def _thor_save_frame_metadata(self, image: np.ndarray, event: MDAEvent, frame_metadata: dict) -> None:
        """Called each time a frame is acquired."""
        frame_index = next(self._pupil_counter)
        self._thor_metadata[frame_index] = frame_metadata

    def save_meso_metadata(self) -> None:
        """Called when the MDA sequence ends for Dhyana camera."""
        save_dir = Path('C:/dev/PyLab/tests')  # Make sure you use forward slashes or raw strings for Windows paths
        save_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

        # Construct the filename
        time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f'{time_str}_dhyana_frame_metadata.json'

        # Save metadata to the json file
        df = pd.DataFrame(self._dhyana_metadata)  # Transpose so that the rows are by time index
        df = df.drop(index=['mda_event'])
        df.to_json(save_dir / filename)

    def save_pupil_metadata(self) -> None:
        """Called when the MDA sequence ends for Thor camera."""
        save_dir = Path('C:/dev/PyLab/tests')  # Ensure consistency in save location
        save_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

        # Construct the filename
        time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f'{time_str}_thor_frame_metadata.json'

        # Save metadata to the json file
        df = pd.DataFrame(self._thor_metadata)
        df = df.drop(index=['mda_event']) # mda_event is type: MappingProxy, cannot be serialized to json
        df.to_json(save_dir / filename)
        
    def _on_pause(self, state: bool) -> None:
        """Called when the MDA is paused."""

        
    def toggle_console(self):
        """Show or hide the IPython console."""
        if self.console_widget and self.console_widget.isVisible():
            self.console_widget.hide()
        else:
            if not self.console_widget:
                self.init_console()
            else:
                self.console_widget.show()
                
    def init_console(self):
        """Initialize the IPython console and embed it into the application."""
        # Create an in-process kernel
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.kernel.gui = 'qt'

        # Create a kernel client and start channels
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        # Create the console widget
        self.console_widget = RichJupyterWidget()
        self.console_widget.kernel_manager = self.kernel_manager
        self.console_widget.kernel_client = self.kernel_client

        # Expose variables to the console's namespace
        self.kernel.shell.push({
            'wdgt1': self.dhyana_gui,
            'wdgt2': self.thor_gui,
            'self': self

            # Optional, so you can use 'self' directly in the console
        })

def run_gui(core1: CMMCorePlus, core2: CMMCorePlus, cfg: ExperimentConfig):
    """Run the main GUI."""
