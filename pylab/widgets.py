from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import napari

import pymmcore_plus
from magicgui import magicgui

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

        # connect MDA acquisition events to local callbacks
        # in this example we're just printing the current state of the acquisition
        self.mmc.mda.events.frameReady.connect(self._on_frame)
        self.mmc.mda.events.sequenceFinished.connect(self._on_end)
        self.mmc.mda.events.sequencePauseToggled.connect(self._on_pause)

        # instantiate the MDAWidget, and a couple labels for feedback
        self.mda = MDAWidget(mmcore=self.mmc)
        # ----------------------------------Auto-set MDASequence and save_info----------------------------------#
        self.mda.setValue(useq.MDASequence(time_plan={"interval": 0, "loops": 1000}))
        self.mda.save_info.setValue({'save_dir': self.config.save_dir, 'save_name': self.config.filename, 'format': 'tiff-sequence', 'should_save': True})
        # -------------------------------------------------------------------------------------------------------#
        self.mda.valueChanged.connect(self._update_sequence)
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


    def _update_sequence(self) -> None:
        """Called when the MDA sequence starts."""

    def _on_frame(self, image: np.ndarray, event: MDAEvent) -> None:
        """Called each time a frame is acquired."""
        # self.current_event.setText(
        #     f"index: {event.index}\n"
        #     f"channel: {getattr(event.channel, 'config', 'None')}\n"
        #     f"exposure: {event.exposure}\n"
        # )

    def _on_end(self) -> None:
        """Called when the MDA sequence ends."""

    def _on_pause(self, state: bool) -> None:
        """Called when the MDA is paused."""

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



    
