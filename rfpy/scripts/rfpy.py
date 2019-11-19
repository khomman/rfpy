import click

from rfpy import app, db
from rfpy.models import Stations, ReceiverFunctions, Filters
from rfpy.util import read_station_file, read_rftn_file


@click.group()
def cli():
    pass


@cli.command('db_init')
def db_init():
    """ Create database """
    db.create_all()


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
    if rftn_file:
        filt_count = 0
        rf_count = 0
        rftns = read_rftn_file(rftn_file)
        for key in rftns:
            sta_id = Stations.query.filter_by(station=key).first().id
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
        print(data_path)


@cli.command('start')
@click.option('-p', '--port', default='5000')
@click.option('-h', '--host', default='127.0.0.1')
def start(port, host):
    app.run(host=host, port=port, debug=True)


def run():
    cli(obj={})
