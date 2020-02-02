import os

from obspy import UTCDateTime, read_events, read_inventory
from obspy.clients.fdsn import Client
from obspy.taup import TauPyModel
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees

from rfpy import db
from rfpy.models import Earthquakes, RawData, Stations, Arrivals


def init_client(client="IRIS"):
    """ Initilize an Obspy Client object """
    client = Client(client)
    return client


def init_model(model='iasp91'):
    """ Initialize a TauPyModel object """
    model = TauPyModel(model=model)
    return model


def check_data_directory(data_path):
    if not os.path.exists(os.path.join(data_path, 'Data')):
        os.mkdir(os.path.join(data_path, 'Data'))


def _check_st_len(st):
    """
    Verifies a stream is only 3 channels.  If stream is longer than 3 channels
    this function trims the stream to only include the first 3.  If channels
    contain 1 or 2 instead of N or S it will rotate to ZNE coordinates
    """
    if len(st) > 3:
        newst = st[:3]
    else:
        newst = st
    return newst


def _check_ZNE(st, inv):
    chans = [tr.stats.channel[-1] for tr in st]
    if '1' or '2' in chans:
        st.rotate('->ZNE', inventory=inv)


def get_stations(data_path=os.getcwd(), add_to_db=False, **kwargs):
    """
    Gets an inventory object from the client. Save the inventory as a
    STATIONXML file in the base_path location.
    :param data_path: Top level location to store stationXML
    :param add_to_db: Add data to the rfpy database instance
    """
    client = init_client()
    inv = client.get_stations(**kwargs)
    check_data_directory(data_path)
    filename = os.path.join(data_path, 'Data', 'RFTN_Stations.xml')
    inv.write(filename, format='STATIONXML')
    if add_to_db:
        sta_query = [s.station for s in Stations.query.all()]
        for net in inv:
            for sta in net:
                station_name = f'{net.code}_{sta.code}'
                if station_name not in sta_query:
                    lat = sta.latitude
                    lon = sta.longitude
                    ele = sta.elevation
                    s = Stations(station=station_name, latitude=lat,
                                 longitude=lon, elevation=ele, status='T')
                    db.session.add(s)
        db.session.commit()


def get_events(data_path=os.getcwd(), add_to_db=False, **kwargs):
    """
    Gets a catalog object from the client.  Saves the catalog as a QUAKEML file
    in the base_path location.
    :param data_path: Top level location to download quakeml
    :param add_to_db: Add data to the rfpy database instance
    """

    client = init_client()
    cat = client.get_events(**kwargs)
    check_data_directory(data_path)
    filename = os.path.join(data_path, 'Data', 'RFTN_Catalog.xml')
    cat.write(filename, format='QUAKEML')
    if add_to_db:
        eq_query = [e.resource_id for e in Earthquakes.query.all()]
        # check resource id against cuurrent db.  If it doesn't exist
        # then add it to the earhtquake table
        for ev in cat:
            resource_id = ev.resource_id.id
            if resource_id not in eq_query:
                origin = ev.origins[0].time.strftime("%Y-%m-%dT%H:%M:%S.%f")
                lat = ev.origins[0].latitude
                lon = ev.origins[0].longitude
                dep = ev.origins[0].depth
                utilized = False
                eq = Earthquakes(resource_id=resource_id, origin_time=origin,
                                 latitude=lat, longitude=lon, depth=dep,
                                 utilized=utilized)
                db.session.add(eq)
        db.session.commit()


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
    check_data_directory(data_path)
    cat_size = len(cat)
    cnt = 0

    if username and password is not None:
        # set_credentials doesn't appear to be working..
        # try to set the user and password instance variables directly
        # client.set_credentials(username, password)
        client.user = username
        client.password = password

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

    if add_to_db:
        utilized_events = [e.resource_id for e in
                           Earthquakes.query.filter_by(utilized=True)]
        sta_dict = {}
        query = Stations.query.all()
        for i in query:
            sta_dict[i.station] = i.id

    for event in cat:
        # temporary status update to be polled by frontend
        cnt += 1
        with open(os.path.join(data_path, 'Data', '.stat.txt'), 'w') as f:
            f.write(f'{int(100*cnt/cat_size)}')

        origin_time = event.origins[0].time.strftime("%Y-%m-%dT%H:%M:%S")
        if not os.path.exists(os.path.join(data_path, 'Data',
                              origin_time)):
            os.mkdir(os.path.join(data_path, 'Data', origin_time))
            os.mkdir(os.path.join(data_path, 'Data', origin_time, 'RAW'))
            os.mkdir(os.path.join(data_path, 'Data', origin_time, 'RF'))

        for net in inv:
            for sta in net:
                sta_lat = sta.latitude
                sta_lon = sta.longitude
                ev_lat = event.origins[0].latitude
                ev_lon = event.origins[0].longitude
                ev_time = UTCDateTime(event.origins[0].time)
                ev_dep_km = event.origins[0].depth/1000.0
                dist_deg = kilometer2degrees(gps2dist_azimuth(sta_lat,
                                             sta_lon, ev_lat,
                                             ev_lon)[0]/1000)
                if dist_deg > 30 and dist_deg < 90:
                    arr = model.get_travel_times(source_depth_in_km=ev_dep_km,
                                                 distance_in_degree=dist_deg,
                                                 phase_list=['P'])
                    start_time = ev_time + arr[0].time - 100
                    end_time = ev_time + arr[0].time + 300
                    try:
                        # Request data from client using 100 seconds before P
                        # and 300 seconds after P
                        st = client.get_waveforms(net.code, sta.code, location,
                                                  channel, start_time,
                                                  end_time, **kwargs)
                        ev_dir = os.path.join(data_path, "Data", origin_time,
                                              'RAW')
                        st = _check_st_len(st)
                        _check_ZNE(st, inv)
                        st.write(f'{ev_dir}/{net.code}_{sta.code}.mseed')
                        if add_to_db:
                            sta_id = sta_dict[f'{net.code}_{sta.code}']
                            ev_id = event.resource_id.id
                            eq_query = Earthquakes.query.\
                                filter_by(resource_id=ev_id).first()
                            eq_query_id = eq_query.id
                            dat = RawData(sta_id=sta_id,
                                          earthquake_id=eq_query_id,
                                          path=f'{ev_dir}/{net.code}_'
                                               f'{sta.code}.mseed',
                                               new_data=True)
                            arrival = Arrivals(arr_type='P',
                                               time=str(ev_time+arr[0].time),
                                               station_id=sta_id,
                                               eq_id=eq_query_id)
                            # Check if event is currently marked as used.
                            # If not change the utilized col in Earthquakes
                            if ev_id not in utilized_events:
                                eq_query.utilized = True

                            db.session.add(dat)
                            db.session.add(arrival)
                            db.session.commit()
                    except Exception:
                        # TODO: Catch proper exception act accordingly
                        pass


def _async_get_data(app, **kwargs):
    """
    Internal helper function for flask app to download data asynchronusly to
    not block other web functionality
    """
    with app.app_context():
        get_stations(data_path=app.config['BASE_DIR'],
                     starttime=kwargs['starttime'], endtime=kwargs['endtime'],
                     network=kwargs['network'], station=kwargs['station'],
                     level="channel", add_to_db=True)
        get_events(data_path=app.config['BASE_DIR'],
                   starttime=kwargs['starttime'], endtime=kwargs['endtime'],
                   minmagnitude=kwargs['minmagnitude'], add_to_db=True)

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
