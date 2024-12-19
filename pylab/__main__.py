"""Entry point for pylab."""

import os
# os.environ['NUMEXPR_MAX_THREADS'] = '4'
# os.environ['NUMEXPR_NUM_THREADS'] = '2'
# import numexpr as ne 

import click
from PyQt6.QtWidgets import QApplication
from pylab.gui.maingui import MainWindow
from pylab.config import ExperimentConfig
from pylab.startup import Startup
'''
This is the client terminal command line interface

The client terminal commands are:

    launch: Launch the mesofield acquisition interface
        - dev: Set to True to launch in development mode with simulated MMCores
    test_mda: Test the mesofield acquisition interface

'''


@click.group()
def cli():
    """PyLabs Command Line Interface"""
    pass

@cli.command()
@click.option('--dev', default=False, help='launch in development mode with simulated MMCores.')
@click.option('--params', default='params.json', help='Path to the config JSON file.')
def launch(dev, params):
    """
    Launch mesofield acquisition interface 

    """
    print('Launching mesofield acquisition interface...')
    app = QApplication([])
    config_path = params
    config = ExperimentConfig(config_path, dev)
    config.hardware.initialize_cores(config)
    mesofield = MainWindow(config)
    mesofield.show()
    app.exec_()


@cli.command()
@click.option('--frames', default=100, help='Number of frames for the MDA test.')
def test_mda(frames):
    """
    Run a test of the mesofield Multi-Dimensional Acquisition (MDA) 
    """
    from pylab.startup import test_mda

@cli.command()
def run_mda():
    """Run the Multi-Dimensional Acquisition (MDA) without the GUI."""
    run_mda()


if __name__ == "__main__":  # pragma: no cover
    cli()




