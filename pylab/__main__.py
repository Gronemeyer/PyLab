"""Entry point for pylab."""

#from pylab.cli import main  # pragma: no cover
import click
from pycromanager import Core
from pylab.utils import utils
from pylab import gui


'''
This is the client terminal command line interface

The client terminal commands are:
'''

@click.group()
def cli():
    """PyLabs Command Line Interface"""
    pass

@cli.command()
@click.option('--pupil', default='False', help='Load SNAP with pupil camera.')
def launch(pupil):
    """
    Launch napari with mesofield acquisition interface widgets
    """
    print("Starting Sipefield Napari Acquisition Platform...")
    gui.launch_mesofield()
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




