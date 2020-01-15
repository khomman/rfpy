import os
import click

from obspy import UTCDateTime

from rfpy import app, db
from rfpy.data import get_stations, get_events, get_data
from rfpy.models import Stations, ReceiverFunctions, Filters
from rfpy.util import read_station_file, read_rftn_file, read_rftn_directory


@click.group()
def cli():
    pass


@cli.command('db_init')
def db_init():
    """ Create database """
    db.create_all()


@cli.command('download_stations')
@click.option('-f', '--station_file', default='stas.txt')
@click.option('-ts', '--start_time', required=True)
@click.option('-tf', '--end_time', required=True)
@click.option('-d', '--data_dir', default=os.getcwd())
def download_stations(station_file, start_time, end_time, data_dir):
    """
    Sets up the rfpy script to download a stationXML file from IRIS.
    Stations to request are provided by the -f (--station_file) parameter.
    The stationXML file will be downloaded to a Data folder located at the
    -d parameter.
    """
    stas = read_station_file(station_file)
    nets = ','.join(set([s[0].split('_')[0] for s in stas]))
    stas = ','.join(set([s[0].split('_')[1] for s in stas]))
    ts = UTCDateTime(start_time)
    tf = UTCDateTime(end_time)
    get_stations(data_path=data_dir, network=nets, station=stas, starttime=ts,
                 endtime=tf, level='station')


@cli.command('download_events')
@click.option('-m', '--minmagnitude', default=5.5)
@click.option('-ts', '--start_time', required=True)
@click.option('-tf', '--end_time', required=True)
@click.option('-d', '--data_dir', default=os.getcwd())
def download_events(minmagnitude, start_time, end_time, data_dir):
    """
    Sets up the rfpy script to download an earthquake catalog from IRIS.
    Earthquakes between --start_time and --end_time and with a magnitude
    greater than minmagnitude will be included in the catalog.  The quakeML
    file will be downloaded to a Data directory located in --data_dir.
    """
    ts = UTCDateTime(start_time)
    tf = UTCDateTime(end_time)
    get_events(data_path=data_dir, starttime=ts, endtime=tf,
               minmagnitude=minmagnitude)


@cli.command('download_data')
@click.option('-s', '--staxml', default='Data/RFTN_Stations.xml')
@click.option('-e', '--quakeml', default='Data/RFTN_Catalog.xml')
@click.option('-d', '--data_dir', default=os.getcwd())
@click.option('-u', '--username')
@click.option('-p', '--password')
def download_data(staxml, quakeml, data_dir, username, password):
    """
    Sets up the rfpy script to download actual waveform data.  Uses the
    stationXML file and the quakeML file from download_stations and
    download_events.  Data will be downloaded to a Data directory located in
    --data_dir.
    """
    if username and password:
        get_data(staxml, quakeml, data_path=data_dir, username=username,
                 password=password)
    else:
        get_data(staxml, quakeml, data_path=data_dir)


@cli.command('add_stations')
@click.option('-f', '--station_file', default='stas.txt')
def add_stations(station_file):
    """ Add stations, dependent on station file, to database """
    stas = read_station_file(station_file)
    for sta in stas:
        s = Stations(station=sta[0], latitude=sta[1], longitude=sta[2],
                     elevation=sta[3], status='T')
        db.session.add(s)
    # Fails if there are duplicates.  Need to catch the error and pass it on or
    # query db first, and only add to session if station doesn't exist
    db.session.commit()
    print(f'Added {len(stas)} stations to the database')


@cli.command('add_rftns')
@click.option('-f', '--rftn_file')
@click.option('-p', '--data_path')
def add_rftns(rftn_file, data_path):
    """
    Add receiver functions to database.  -f, --rftn_file reads receiver
    function paths from file. -p, --data_path searches a directory structure
    for receiver functions to add
    """
    if rftn_file:
        filt_count = 0
        rf_count = 0
        rftns = read_rftn_file(rftn_file)
        for key in rftns:
            sta_id = Stations.query.filter_by(station=key).first().id
            if not sta_id:
                raise LookupError("Station not in database: Please run"
                                  "add_stations command first")
            for k, v in rftns[key].items():
                # Try to grab the filter id.  If it doesn't exist then add the
                # filter to the database and get the id
                try:
                    filt_id = Filters.query.filter_by(filter=k).first().id
                except AttributeError:
                    f = Filters(filter=k)
                    db.session.add(f)
                    db.session.commit()
                    filt_id = Filters.query.filter_by(filter=k).first().id
                    filt_count += 1
                for pth in v:
                    rf = ReceiverFunctions(station=sta_id, filter=filt_id,
                                           path=pth,
                                           new_receiver_function=True,
                                           accepted=True)
                    db.session.add(rf)
                    rf_count += 1
        db.session.commit()
        print(f'Added {filt_count} Filters and {rf_count} receiver functions')

    if data_path:
        filt_count = 0
        rf_count = 0
        rftns = read_rftn_directory(data_path)
        for key in rftns:
            sta_id = Stations.query.filter_by(station=key).first().id
            if not sta_id:
                raise LookupError("Station not in database: Please run"
                                  "add_stations command first")
            for k, v in rftns[key].items():
                # Try to grab the filter id.  If it doesn't exist then add the
                # filter to the database and get the id
                try:
                    filt_id = Filters.query.filter_by(filter=k).first().id
                except AttributeError:
                    f = Filters(filter=k)
                    db.session.add(f)
                    db.session.commit()
                    filt_id = Filters.query.filter_by(filter=k).first().id
                    filt_count += 1
                for pth in v:
                    rf = ReceiverFunctions(station=sta_id, filter=filt_id,
                                           path=pth,
                                           new_receiver_function=True,
                                           accepted=True)
                    db.session.add(rf)
                    rf_count += 1
        db.session.commit()
        print(f'Added {filt_count} Filters and {rf_count} receiver functions')


@cli.command('start')
@click.option('-p', '--port', default='5000')
@click.option('-h', '--host', default='127.0.0.1')
def start(port, host):
    app.run(host=host, port=port, debug=True)


def run():
    cli(obj={})
