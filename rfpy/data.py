import os

from obspy import UTCDateTime, read_events, read_inventory
from obspy.clients.fdsn import Client
from obspy.taup import TauPyModel
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees

from rfpy import db
from rfpy.models import Stations, RawData


def init_client(client="IRIS"):
    client = Client(client)
    return client


def init_model(model='iasp91'):
    model = TauPyModel(model=model)
    return model


def get_stations(data_path=os.getcwd(), **kwargs):
    """
    Gets an inventory object from the client. Save the inventory as a
    STATIONXML file in the base_path location.
    :param data_path: Top level location to store stationXML
    """
    client = init_client()
    inv = client.get_stations(**kwargs)
    if not os.path.exists(os.path.join(data_path, 'Data')):
        os.mkdir(os.path.join(data_path, 'Data'))

    filename = os.path.join(data_path, 'Data', 'RFTN_Stations.xml')
    inv.write(filename, format='STATIONXML')


def get_events(data_path=os.getcwd(), **kwargs):
    """
    Gets a catalog object from the client.  Saves the catalog as a QUAKEML file
    in the base_path location.
    :param data_path: Top level location to download quakeml
    """

    client = init_client()
    cat = client.get_events(**kwargs)
    if not os.path.exists(os.path.join(data_path, 'Data')):
        os.mkdir(os.path.join(data_path, 'Data'))
    filename = os.path.join(data_path, 'Data', 'RFTN_Catalog.xml')
    cat.write(filename, format='QUAKEML')


def get_data(staxml, quakeml, data_path=os.getcwd(), username=None,
             password=None, add_to_db=False, **kwargs):
    """
    Request event data from an obspy client.  Reads an earthquake and a station
    file and downloads waveforms from stations that are between 30 and 90
    degrees away from event
    :param staxml: StationXML file location
    :param quakeml: QuakeML file location
    :data_path: location to store downloaded waveforms
    :username: FDSN username for restricted data (If needed)
    :password: FDSN password for restricted data (If needed)
    :add_to_db: Add data to the flask database associated with the rfpy project
    """
    client = init_client()
    cat = read_events(quakeml, format='QUAKEML')
    inv = read_inventory(staxml, format='STATIONXML')
    model = init_model()

    if username and password is not None:
        client.set_credentials(username, password)

    if 'channel' not in kwargs:
        channel = "HH*,BH*"
    else:
        channel = kwargs['channel']
        del kwargs['channel']

    if 'location' not in kwargs:
        location = "*"
    else:
        location = kwargs['location']
        del kwargs['location']

    if not os.path.exists(os.path.join(data_path, 'Data')):
        os.mkdir(os.path.join(data_path, 'Data'))

    if add_to_db:
        sta_dict = {}
        query = Stations.query.all()
        for i in query:
            sta_dict[i.station] = i.id

    for event in cat:
        origin_time = event.origins[0].time.strftime("%Y-%m-%dT%H:%M:%S")
        if not os.path.exists(os.path.join(data_path, 'Data',
                              origin_time)):
            os.mkdir(os.path.join(data_path, 'Data', origin_time))

        for net in inv:
            for sta in net:
                sta_lat = sta.latitude
                sta_lon = sta.longitude
                ev_lat = event.origins[0].latitude
                ev_lon = event.origins[0].longitude
                ev_time = UTCDateTime(event.origins[0].time)
                ev_depth_km = event.origins[0].depth/1000.0
                dist_degree = kilometer2degrees(gps2dist_azimuth(sta_lat,
                                                sta_lon, ev_lat,
                                                ev_lon)[0]/1000)
                if dist_degree > 30 and dist_degree < 90:
                    arr = model.get_travel_times(source_depth_in_km=ev_depth_km,
                                                 distance_in_degree=dist_degree,
                                                 phase_list=['P'])
                    start_time = ev_time + arr[0].time - 100
                    end_time = ev_time + arr[0].time + 300
                    try:
                        # Request data from client using 100 seconds before P
                        # and 300 seconds after P
                        st = client.get_waveforms(net.code, sta.code, location,
                                                  channel, start_time,
                                                  end_time, **kwargs)
                        ev_dir = os.path.join(data_path, "Data", origin_time)
                        st.write(f'{ev_dir}/{net.code}_{sta.code}.mseed')
                        if add_to_db:
                            sta_id = sta_dict[f'{net.code}_{sta.code}']
                            dat = RawData(sta_id=sta_id,
                                          path=f'{ev_dir}/{net.code}_'
                                               f'{sta.code}.mseed',
                                               new_data=True)
                            db.session.add(dat)
                            db.session.commit()
                    except:
                        # TODO: Catch proper exception act accordingly
                        pass


def _async_get_data(app, **kwargs):
    """
    Internal helper function for flask app to install data asynchronusly to not
    block other web functionality
    """
    with app.app_context():
        get_stations(data_path=app.config['BASE_DIR'],
                     starttime=kwargs['starttime'], endtime=kwargs['endtime'],
                     network=kwargs['network'], station=kwargs['station'],
                     level="station")
        get_events(data_path=app.config['BASE_DIR'],
                   starttime=kwargs['starttime'], endtime=kwargs['endtime'],
                   minmagnitude=kwargs['minmagnitude'])

        if 'username' in kwargs:
            get_data(os.path.join(app.config['BASE_DIR'],
                     'Data/RFTN_Stations.xml'), os.path.join(
                     app.config['BASE_DIR'], 'Data/RFTN_Catalog.xml'),
                     data_path=app.config['BASE_DIR'],
                     username=kwargs['username'],
                     password=kwargs['password'], add_to_db=True)
        else:
            get_data(os.path.join(app.config['BASE_DIR'],
                     'Data/RFTN_Stations.xml'), os.path.join(
                     app.config['BASE_DIR'], 'Data/RFTN_Catalog.xml'),
                     data_path=app.config['BASE_DIR'], add_to_db=True)
