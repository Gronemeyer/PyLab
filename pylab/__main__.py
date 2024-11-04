"""Entry point for pylab."""

#from pylab.cli import main  # pragma: no cover
import click
#from pylab.mdacore import *
from PyQt6.QtWidgets import QApplication
from pylab.engine import *
from pylab.gui import MainWindow, run_gui
from pylab.config import Config
from pylab.mdacore import load_dev_cores
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
        run_gui(mmcore_dhyana, mmcore_thor, Config)

@cli.command()
def dev():
    """
    Start the application.
    """
    app = QApplication([])
    core1, core2 = load_dev_cores()
    cfg = Config
    mesofield = MainWindow(core1, core2, cfg)
    mesofield.show()
    app.exec_()



### Utility commands for querying serial ports and USB IDs ###

@cli.command()
def get_devices():
    """Download USB IDs and list all serial ports."""
    from .utils.utils import download_usb_ids, parse_usb_ids, list_serial_ports

    usb_ids_content = download_usb_ids()
    if usb_ids_content:
        usb_ids = parse_usb_ids(usb_ids_content)
        list_serial_ports(usb_ids)
    else:
        click.echo("Failed to download USB IDs.")

### NI-DAQ commands ###
from .utils.utils import list_nidaq_devices, test_nidaq_connection, read_analog_input

@click.command()
def list_devices():
    """List all connected NI-DAQ devices."""
    devices = list_nidaq_devices()
    click.echo("\n".join(devices))

@click.command()
@click.option('--device_name', default='Dev2', help='Device name to test connection.')
def test_connection(device_name):
    """Test connection to a specified NI-DAQ device."""
    if test_nidaq_connection(device_name):
        click.echo(f"Successfully connected to {device_name}.")
    else:
        click.echo(f"Failed to connect to {device_name}.")

cli.add_command(list_devices)
cli.add_command(test_connection)


if __name__ == "__main__":  # pragma: no cover
    cli()




