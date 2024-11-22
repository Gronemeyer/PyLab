"""Entry point for pylab."""

import os
# os.environ['NUMEXPR_MAX_THREADS'] = '4'
# os.environ['NUMEXPR_NUM_THREADS'] = '2'
# import numexpr as ne 

import click
from PyQt6.QtWidgets import QApplication
from pylab.maingui import MainWindow
from pylab.config import ExperimentConfig
from pylab.mmcore import MMConfigurator
'''
This is the client terminal command line interface

The client terminal commands are:

    launch: Launch the mesofield acquisition interface
        - dev: Set to True to launch in development mode with simulated MMCores
    test_mda: Test the mesofield acquisition interface

'''

PARAMETERS = {
    'mmc1_path': 'C:/Program Files/Micro-Manager-2.0gamma',
    'mmc2_path': 'C:/Program Files/Micro-Manager-thor',
    'mmc1_configuration_path': 'C:/Program Files/Micro-Manager-2.0/mm-sipefield.cfg',
    'mmc2_configuration_path': 'C:/Program Files/Micro-Manager-2.0/ThorCam.cfg',
    'memory_buffer_size': 10000,
    'dhyana_fps': 49,
    'thorcam_fps': 30,
    'encoder': {
        'type': 'dev',
        'port': 'COM4',
        'baudrate': '57600',
        'CPR': '2400',
        'diameter_cm': '0.1',
        'sample_interval_ms': '20'
    }
    }

@click.group()
def cli():
    """PyLabs Command Line Interface"""
    pass

@cli.command()
@click.option('--dev', default=False, help='launch in development mode with simulated MMCores.')
def launch(dev):
    """
    Launch mesofield acquisition interface 

    """
    print('Launching mesofield acquisition interface...')
    app = QApplication([])
    mmconfig = MMConfigurator(PARAMETERS, dev)
    config = ExperimentConfig(mmconfig)
    mmconfig.meso_engine.set_config(config)
    mesofield = MainWindow(config)
    mesofield.show()
    app.exec_()


@cli.command()
@click.option('--frames', default=100, help='Number of frames for the MDA test.')
def test_mda(frames):
    """
    Run a test of the mesofield Multi-Dimensional Acquisition (MDA) 
    """
    from pylab.mmcore import test_mda

@cli.command()
def run_mda():
    """Run the Multi-Dimensional Acquisition (MDA) without the GUI."""
    run_mda()


if __name__ == "__main__":  # pragma: no cover
    cli()




