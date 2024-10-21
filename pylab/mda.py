from pathlib import Path
import numpy as np
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from useq import MDAEvent

from pymmcore_widgets import (
    MDAWidget,
    ChannelWidget,
    ExposureWidget,
    ImagePreview,
    LiveButton,
    SnapButton,
)

import qdarktheme
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

import useq
#from pylab.config import ExperimentConfig
       
    
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
    In this example, we've also connected callbacks to the CMMCorePlus object's `mda`
    events to print out the current state of the acquisition.
    """

    def __init__(self, core_object: CMMCorePlus) -> None:
        super().__init__()
        # get the CMMCore instance and load the default config
        self.mmc = core_object
        self.mmc.loadSystemConfiguration()

        # connect MDA acquisition events to local callbacks
        # in this example we're just printing the current state of the acquisition
        self.mmc.mda.events.frameReady.connect(self._on_frame)
        self.mmc.mda.events.sequenceFinished.connect(self._on_end)
        self.mmc.mda.events.sequencePauseToggled.connect(self._on_pause)

        # instantiate the MDAWidget, and a couple labels for feedback
        self.mda = MDAWidget(mmcore=self.mmc)
        # ----------------------------------Auto-set MDASequence and save_info----------------------------------#
        # If value is a dict, keys should be: 
        # - save_dir: str - Set the save directory.
        # - save_name: str - Set the save name.
        # - format: str - Set the combo box to the writer with this name.
        # - should_save: bool - Set the checked state of the checkbox.
        self.mda.setValue(useq.MDASequence(time_plan={"interval": 0, "loops": 1000}))
        self.mda.save_info.setValue({'save_dir': 'F:/', 'save_name': 'test', 'format': 'tiff-sequence', 'should_save': True})
        # -------------------------------------------------------------------------------------------------------#
        self.mda.valueChanged.connect(self._update_sequence)
        self.current_sequence = QLabel('... enter info and click "Run"')
        self.current_event = QLabel("... current event info will appear here")

        lbl_wdg = QGroupBox()
        lbl_layout = QVBoxLayout(lbl_wdg)
        lbl_layout.addWidget(QLabel(text="<h3>ACQUISITION SEQUENCE</h3>"))
        lbl_layout.addWidget(self.current_sequence)
        lbl_layout.addWidget(QLabel(text="<h3>ACQUISITION EVENT</h3>"))
        lbl_layout.addWidget(self.current_event)

        layout = QHBoxLayout(self)
        layout.addWidget(self.mda)
        layout.addWidget(lbl_wdg)

    def _update_sequence(self) -> None:
        """Called when the MDA sequence starts."""
        self.current_sequence.setText(self.mda.value().yaml(exclude_defaults=True))

    def _on_frame(self, image: np.ndarray, event: MDAEvent) -> None:
        """Called each time a frame is acquired."""
        self.current_event.setText(
            f"index: {event.index}\n"
            f"channel: {getattr(event.channel, 'config', 'None')}\n"
            f"exposure: {event.exposure}\n"
            f"pos_name: {event.pos_name}\n"
            f"xyz: ({event.x_pos}, {event.y_pos}, {event.z_pos})\n"
        )

    def _on_end(self) -> None:
        """Called when the MDA sequence ends."""
        self.current_event.setText("Finished!")

    def _on_pause(self, state: bool) -> None:
        """Called when the MDA is paused."""
        txt = "Paused..." if state else "Resumed!"
        self.current_event.setText(txt)


class ImageFrame(QWidget):
    """An example widget with a snap/live button and an image preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.preview = ImagePreview()
        self.snap_button = SnapButton()
        self.live_button = LiveButton()
        self.exposure = ExposureWidget()
        self.channel = ChannelWidget()
    
        self.setLayout(QVBoxLayout())

        buttons = QGroupBox()
        buttons.setLayout(QHBoxLayout())
        buttons.layout().addWidget(self.snap_button)
        buttons.layout().addWidget(self.live_button)

        ch_exp = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        ch_exp.setLayout(layout)

        ch = QGroupBox()
        ch.setTitle("Channel")
        ch.setLayout(QHBoxLayout())
        ch.layout().setContentsMargins(0, 0, 0, 0)
        ch.layout().addWidget(self.channel)
        layout.addWidget(ch)

        exp = QGroupBox()
        exp.setTitle("Exposure")
        exp.setLayout(QHBoxLayout())
        exp.layout().setContentsMargins(0, 0, 0, 0)
        exp.layout().addWidget(self.exposure)
        layout.addWidget(exp)

        self.layout().addWidget(self.preview)
        self.layout().addWidget(ch_exp)
        self.layout().addWidget(buttons)

class PupilRecorder(QMainWindow):
    def __init__(self, core_object: CMMCorePlus) -> None:
        super().__init__()
        self.mmc = core_object
        self.setWindowTitle("Pupil Record")
        #self.setWindowIcon()

        # Create a central widget and set its layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()  # Change to QVBoxLayout for two rows
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Create a widget for the top row and set its layout
        top_row_widget = QWidget()
        top_row_layout = QHBoxLayout()  # QHBoxLayout for two columns
        top_row_widget.setLayout(top_row_layout)

        # Create instances of MDA and ImageFrame
        mda_widget = MDA(core_object=self.mmc)
        image_frame_widget = ImageFrame()
        # Add the widgets to the top row layout
        top_row_layout.addWidget(image_frame_widget)  # Add image_frame_widget to the first column
        top_row_layout.addWidget(mda_widget)  # Add mda_widget to the second column

        # Add the top row widget to the main layout
        main_layout.addWidget(top_row_widget)

        # Create a Jupyter console widget
        self.console = RichJupyterWidget()
        self.console.setMinimumHeight(200)
        self.console.setVisible(False)  # Initially hidden

        # Set up the Jupyter kernel
        kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel_client = kernel_manager.client()
        self.console.kernel_manager = kernel_manager
        self.console.kernel_client = kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        # Add the console to the main layout
        main_layout.addWidget(self.console)

        # Add a menu action to toggle the console
        toggle_console_action = self.menuBar().addAction("Toggle Console")
        toggle_console_action.triggered.connect(self.toggle_console)

    def toggle_console(self):
        self.console.setVisible(not self.console.isVisible())

if __name__ == "__main__":
    app = QApplication([])
    mmc = CMMCorePlus()
    main_window = PupilRecorder(mmc)
    qdarktheme.setup_theme() #https://pyqtdarktheme.readthedocs.io/en/stable/how_to_use.html
    main_window.show()
    app.exec_()