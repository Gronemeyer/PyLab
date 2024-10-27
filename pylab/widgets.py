from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari

import pymmcore_plus
from magicgui import magicgui
from itertools import count

from pathlib import Path
import numpy as np
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from useq import MDAEvent

from pymmcore_widgets import (
    MDAWidget,
    ExposureWidget,
    ImagePreview,
    LiveButton,
    SnapButton,
)

import useq

from pylab.config import ExperimentConfig
from pylab.engine import AcquisitionEngine

# Import necessary modules for the IPython console
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from qtpy.QtWidgets import QMainWindow
import pandas as pd
import datetime

import json
class MDA(QWidget):
    """An example of using the MDAWidget to create and acquire a useq.MDASequence.

    The `MDAWidget` provides a GUI to construct a `useq.MDASequence` object.
    This object describes a full multi-dimensional acquisition;
    In this example, we set the `MDAWidget` parameter `include_run_button` to `True`,
    meaning that a `run` button is added to the GUI. When pressed, a `useq.MDASequence`
    is first built depending on the GUI values and is then passed to the
    `CMMCorePlus.run_mda` to actually execute the acquisition.
    For details of the corresponding schema and methods, see
    https://github.com/pymmcore-plus/useq-schema and
    https://github.com/pymmcore-plus/pymmcore-plus.

    """

    def __init__(self, core_object: CMMCorePlus, cfg) -> None:
        super().__init__()
        # get the CMMCore instance and load the default config
        self.mmc = core_object
        self.config: ExperimentConfig = cfg

        # instantiate the MDAWidget
        self.mda = MDAWidget(mmcore=self.mmc)
        # ----------------------------------Auto-set MDASequence and save_info----------------------------------#
        self.mda.setValue(self.config.pupil_sequence)
        self.mda.save_info.setValue({'save_dir': self.config.save_dir, 'save_name': self.config.filename, 'format': 'tiff-sequence', 'should_save': True})
        # -------------------------------------------------------------------------------------------------------#
        self.setLayout(QHBoxLayout())

        self.preview = ImagePreview(mmcore=self.mmc,parent=self.mda)
        self.snap_button = SnapButton(mmcore=self.mmc)
        self.live_button = LiveButton(mmcore=self.mmc)
        self.exposure = ExposureWidget(mmcore=self.mmc)

        live_viewer = QGroupBox()
        live_viewer.setLayout(QVBoxLayout())
        buttons = QGroupBox()
        buttons.setLayout(QHBoxLayout())
        buttons.layout().addWidget(self.snap_button)
        buttons.layout().addWidget(self.live_button)
        live_viewer.layout().addWidget(buttons)
        live_viewer.layout().addWidget(self.preview)

        self.layout().addWidget(self.mda)
        self.layout().addWidget(live_viewer)


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

class MainWidget(QMainWindow):
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
        self.config = AcquisitionEngine(core_object1, cfg)
        
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
        self.dhyana_gui.mmc.mda.events.sequenceFinished.connect(self.save_meso_metadata)
        self.thor_gui.mmc.mda.events.sequenceFinished.connect(self.save_pupil_metadata)

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

        
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
    
#     # Assuming core_object1, core_object2, cfg1, and cfg2 are defined elsewhere
#     core_object1 = CMMCorePlus.instance()
#     core_object2 = CMMCorePlus.instance()
#     cfg1 = ExperimentConfig()
#     cfg2 = ExperimentConfig()
    
#     window = MainWindow(core_object1, core_object2, cfg1, cfg2)
#     window.show()
    
#     sys.exit(app.exec_())
