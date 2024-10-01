"""Entry point for pylab."""

#from pylab.cli import main  # pragma: no cover
import click
from pycromanager import Core


'''
This is the client terminal command line interface

The client terminal commands are:
'''

@click.group()
def cli():
    """PyLabs Command Line Interface"""
    pass

@cli.command()
def record():
    """
    Record a widefield acquisition.S
    """
    from pycromanager import Acquisition, multi_d_acquisition_events
    from pylab import base

    print("Initializing Micro Manager Device configuration from config file..." + base.MM_CONFIG)
    # Initialize the core object for Micromanager API

    core = Core()
    core.close()
    core = Core()
    # Load the system configuration file
    core.load_system_configuration(base.MM_CONFIG)
    
    with Acquisition(directory=base.SAVE_DIR) as acq:
        events = multi_d_acquisition_events(num_time_points=10)
        acq.acquire(events)

    core.close()


@cli.command()
def record2():
    """
    Record a widefield acquisition.
    """
    from pycromanager import Acquisition, multi_d_acquisition_events, Core
    from pylab import base

    print("Initializing Micro Manager Device configuration from config file..." + base.MM_CONFIG)
    core = None
    try:
        core = Core()
        core.load_system_configuration(base.MM_CONFIG)
        
        with Acquisition(directory=base.SAVE_DIR) as acq:
            events = multi_d_acquisition_events(num_time_points=10)
            acq.acquire(events)
    finally:
        if core is not None:
            core.close()


### Utility commands for querying serial ports and USB IDs ###

@cli.command()
def get_devices():
    """Download USB IDs and list all serial ports."""
    from .utils import download_usb_ids, parse_usb_ids, list_serial_ports

    usb_ids_content = download_usb_ids()
    if usb_ids_content:
        usb_ids = parse_usb_ids(usb_ids_content)
        list_serial_ports(usb_ids)
    else:
        click.echo("Failed to download USB IDs.")

### NI-DAQ commands ###
from .utils import list_nidaq_devices, test_nidaq_connection, read_analog_input

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


