"""Entry point for pylab."""



#from pylab.cli import main  # pragma: no cover
import os
os.environ['NUMEXPR_MAX_THREADS'] = '4'
os.environ['NUMEXPR_NUM_THREADS'] = '2'
import numexpr as ne 

import click
#from pylab.mdacore import *
from PyQt6.QtWidgets import QApplication
from pylab.engine import *
from pylab.gui import MainWindow
from pylab.config import Config
from pylab.mdacore import load_dev_cores, load_dhyana_mmc_params, load_thorcam_mmc_params, load_cores
'''
This is the client terminal command line interface

The client terminal commands are:
'''

@click.group()
def cli():
    """PyLabs Command Line Interface"""
    pass

@cli.command()
@click.option('--dev', is_flag=True, help='Run in development mode.')
def launch(dev):
    """
    Launch napari with mesofield acquisition interface widgets
    """
    if dev:
        load_dhyana_mmc_params(mmcore_dhyana)
        load_thorcam_mmc_params(mmcore_thor)
        mmcore_dhyana.mda.set_engine(MesoEngine(mmcore_dhyana, use_hardware_sequencing=True))
        mmcore_thor.mda.set_engine(PupilEngine(mmcore_thor, use_hardware_sequencing=True))
        mmcore_dhyana.run_mda(useq.MDASequence(time_plan={"interval": 0, "loops": 20000}))#, output=r'C:/dev/dh.ome.tif')
        mmcore_thor.run_mda(useq.MDASequence(time_plan={"interval": 0, "loops": 20000}))#, output=r'C:/dev/thor.ome.tif')
    else:
            app = QApplication([])
            mmcore_dhyana, mmcore_thor = load_cores()
            load_dhyana_mmc_params(mmcore_dhyana)
            load_thorcam_mmc_params(mmcore_thor)
            engine1 = MesoEngine(mmcore_dhyana, True)
            engine2 = PupilEngine(mmcore_thor, True)
            mmcore_dhyana.register_mda_engine(engine1)
            mmcore_thor.register_mda_engine(engine2)
            cfg = Config
            mesofield = MainWindow(mmcore_dhyana, mmcore_thor, cfg)
            mesofield.show()
            app.exec_()

@cli.command()
def dev():
    """
    Start the application.
    """
    app = QApplication([])
    core1, core2 = load_dev_cores()
    engine1 = MesoEngine(core1, True)
    engine2 = PupilEngine(core2, False)
    core1.register_mda_engine(engine1)
    core2.register_mda_engine(engine2)
    cfg = Config
    mesofield = MainWindow(core1, core2, cfg)
    mesofield.show()
    app.exec_()

@cli.command()
@click.option('--frames', default=100, help='Number of frames for the MDA test.')
def test_mda(frames):
    """
    Start the application.
    """
    from pylab.mdacore import test_mda
    test_mda(frames)
    print('done')


if __name__ == "__main__":  # pragma: no cover
    cli()




