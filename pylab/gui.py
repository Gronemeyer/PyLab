import datetime
from itertools import count
from pathlib import Path
import numpy as np
import pandas as pd

from pymmcore_plus import CMMCorePlus
from useq import MDAEvent

# Necessary modules for the IPython console
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

from qtpy.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout,
)

from pylab.widgets import MDA, ConfigController
from pylab.config import ExperimentConfig


class MainWindow(QMainWindow):
    def __init__(self, core_object1: CMMCorePlus, core_object2: CMMCorePlus, cfg: ExperimentConfig):
        super().__init__()
        self.setWindowTitle("Main Widget with Two MDA Widgets")
        self.config: ExperimentConfig = cfg

        # Create a central widget and set it as the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set layout for the central widget
        main_layout = QHBoxLayout(central_widget)
        mda_layout = QVBoxLayout()
        
        # Create two instances of MDA widget
        self.dhyana_gui = MDA(core_object1, cfg)
        self.thor_gui = MDA(core_object2, cfg)
        self.cfg_gui = ConfigController(core_object1, core_object2, cfg)
        
        # Add MDA widgets to the layout
        mda_layout.addWidget(self.dhyana_gui)
        mda_layout.addWidget(self.thor_gui)
        main_layout.addLayout(mda_layout)
        main_layout.addWidget(self.cfg_gui)
        
        self.init_console()
        toggle_console_action = self.menuBar().addAction("Toggle Console")
        toggle_console_action.triggered.connect(self.toggle_console)

        self.cfg_gui.configUpdated.connect(self._update_config)
        self.cfg_gui.recordStarted.connect(self.record)
        
    def record(self):
        self.dhyana_gui.mda.run_mda()
        self.thor_gui.mda.run_mda()   
         
    def _update_config(self, config):
        self.config: ExperimentConfig = config
        self._refresh_mda_gui()
        self._refresh_save_gui()
        
    def _refresh_mda_gui(self):
        self.dhyana_gui.mda.setValue(self.config.meso_sequence)
        self.thor_gui.mda.setValue(self.config.pupil_sequence)
        
    def _refresh_save_gui(self):
        self.dhyana_gui.mda.save_info.setValue({'save_dir': str(self.config.bids_dir),  'save_name': str(self.config.meso_file_path), 'format': 'ome-tiff', 'should_save': True})
        self.thor_gui.mda.save_info.setValue({'save_dir': str(self.config.bids_dir), 'save_name': str(self.config.pupil_file_path), 'format': 'ome-tiff', 'should_save': True})
        
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


