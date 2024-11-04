import pymmcore_plus
from pymmcore_plus import CMMCorePlus
import os
import subprocess #for PsychoPy Subprocess
from magicgui import magicgui

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTableWidget,
    QHeaderView,
    QFileDialog,
    QTableWidgetItem
)

from pymmcore_widgets import (
    MDAWidget,
    ExposureWidget,
    ImagePreview,
    LiveButton,
    SnapButton,
)

from pylab.config import ExperimentConfig

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
class ConfigController(QWidget):
    """AcquisitionEngine object for the napari-mesofield plugin.
    This class is a subclass of the QWidget class.
    The object connects to the Micro-Manager Core object instance and the napari viewer object.

    _update_config: updates the experiment configuration from a new JSON file

    run_sequence: runs the MDA sequence with the configuration parameters

    launch_psychopy: launches the PsychoPy experiment as a subprocess with ExperimentConfig parameters
    """
    def __init__(self, mmc: pymmcore_plus.CMMCorePlus, cfg):
        super().__init__()
        self._mmc = mmc
        self.config: ExperimentConfig = cfg

        # Create main layout
        self.layout = QVBoxLayout(self)

        configUpdated = pyqtSignal(object)

        # ==================================== GUI Widgets ===================================== #

        # 1. Selecting a save directory
        self.directory_label = QLabel('Select Save Directory:')
        self.directory_line_edit = QLineEdit()
        self.directory_line_edit.setReadOnly(True)
        self.directory_button = QPushButton('Browse')

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.directory_label)
        dir_layout.addWidget(self.directory_line_edit)
        dir_layout.addWidget(self.directory_button)

        self.layout.addLayout(dir_layout)

        # 2. Dropdown Widget for JSON configuration files
        self.json_dropdown_label = QLabel('Select JSON Config:')
        self.json_dropdown = QComboBox()

        json_layout = QHBoxLayout()
        json_layout.addWidget(self.json_dropdown_label)
        json_layout.addWidget(self.json_dropdown)

        self.layout.addLayout(json_layout)

        # 3. Table widget to display the configuration parameters loaded from the JSON
        self.layout.addWidget(QLabel('Experiment Config:'))
        self.config_table = QTableWidget()
        self.config_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.config_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.config_table)

        # 4. Record button to start the MDA sequence
        self.record_button = QPushButton('Record')
        self.layout.addWidget(self.record_button)

        # ------------------------------------------------------------------------------------- #

        # ============ Callback connections between widget values and functions ================ #

        self.directory_button.clicked.connect(self._select_directory)
        self.json_dropdown.currentIndexChanged.connect(self._update_config)
        self.config_table.cellChanged.connect(self._on_table_edit)
        self.record_button.clicked.connect(self.record)

        # ------------------------------------------------------------------------------------- #

        # Initialize the config table
        self._refresh_config_table()

    # ============================== Private Class Methods ============================================ #

    def _select_directory(self):
        """Open a dialog to select a directory and update the GUI accordingly."""
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if directory:
            self.directory_line_edit.setText(directory)
            self._get_json_file_choices(directory)

    def _get_json_file_choices(self, path):
        """Return a list of JSON files in the current directory."""
        import glob
        self.config.save_dir = path
        try:
            json_files = glob.glob(os.path.join(path, "*.json"))
            self.json_dropdown.clear()
            self.json_dropdown.addItems(json_files)
        except Exception as e:
            print(f"Error getting JSON files from directory: {path}\n{e}")

    def _update_config(self, index):
        """Update the experiment configuration from a new JSON file."""
        json_path_input = self.json_dropdown.currentText()

        if json_path_input and os.path.isfile(json_path_input):
            try:
                self.config.load_parameters(json_path_input)
                # Refresh the GUI table
                self._refresh_config_table()
            except Exception as e:
                print(f"Trouble updating ExperimentConfig from AcquisitionEngine:\n{json_path_input}\nConfiguration not updated.")
                print(e)

    def _on_table_edit(self, row, column):
        """Update the configuration parameters when the table is edited."""
        try:
            if self.config_table.item(row, 0) and self.config_table.item(row, 1):
                key = self.config_table.item(row, 0).text()
                value = self.config_table.item(row, 1).text()
                self.config.update_parameter(key, value)
        except Exception as e:
            print(f"Error updating config from table: check AcquisitionEngine._on_table_edit()\n{e}")

    def _refresh_config_table(self):
        """Refresh the configuration table to reflect current parameters."""
        df = self.config.dataframe
        self.config_table.blockSignals(True)  # Prevent signals while updating the table
        self.config_table.clear()
        self.config_table.setRowCount(len(df))
        self.config_table.setColumnCount(len(df.columns))
        self.config_table.setHorizontalHeaderLabels(df.columns.tolist())

        for i, row in df.iterrows():
            for j, (col_name, value) in enumerate(row.items()):
                item = QTableWidgetItem(str(value))
                self.config_table.setItem(i, j, item)

        self.config_table.blockSignals(False)  # Re-enable signals

    # ----------------------------------------------------------------------------------------------- #

    # ============================== Public Class Methods ============================================ #

    def record(self):
        """Run the MDA sequence with the global Config object parameters loaded from JSON."""

        # Wait for spacebar press if start_on_trigger is True
        wait_for_trigger = self.config.start_on_trigger
        if wait_for_trigger:
            print("Press spacebar to start recording...")
            # self.launch_psychopy()
            # Note: Implement key press detection suitable for PyQt5
            # For example, using QEventLoop or custom dialog

        # Run the MDA sequence
        self._mmc.run_mda(
            self.config.meso_sequence,
            output=self.config.meso_data_path
        )

    def launch_psychopy(self):
        """Launches a PsychoPy experiment as a subprocess with the current ExperimentConfig parameters."""
        # Build the command arguments
        args = [
            "C:\\Program Files\\PsychoPy\\python.exe",
            "F:\\jgronemeyer\\Gratings_vis_0.6.py",
            f'{self.config.protocol}',
            f'{self.config.subject}',
            f'{self.config.session}',
            f'{self.config.save_dir}',
            f'{self.config.num_trials}'
        ]

        subprocess.Popen(args, start_new_session=True)
    
    def save_config(self):
        """ Save the current configuration to a JSON file """
        self.config.save_parameters()

    #-----------------------------------------------------------------------------------------------#
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
