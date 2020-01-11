import os

from obspy import UTCDateTime, read_events, read_inventory
from obspy.clients.fdsn import Client
from obspy.taup import TauPyModel
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees


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
    """

    client = init_client()
    cat = client.get_events(**kwargs)
    if not os.path.exists(os.path.join(data_path, 'Data')):
        os.mkdir(os.path.join(data_path, 'Data'))
    filename = os.path.join(data_path, 'Data', 'RFTN_Catalog.xml')
    cat.write(filename, format='QUAKEML')


def get_data(staxml, quakeml, data_path=os.getcwd(), username=None,
             password=None, **kwargs):
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
                    except:
                        # TODO: Catch proper exception act accordingly
                        pass


def async_get_data(app, **kwargs):
    with app.app_context():
        get_stations(data_path=app.config['BASE_DIR'],
                     starttime=kwargs['starttime'], endtime=kwargs['endtime'],
                     network=kwargs['network'], station=kwargs['station'],
                     level="station")
        get_events(data_path=app.config['BASE_DIR'],
                   starttime=kwargs['starttime'], endtime=kwargs['endtime'],
                   minmagnitude=kwargs['minmagnitude'])
        get_data(os.path.join(app.config['BASE_DIR'],
                 'Data/RFTN_Stations.xml'), os.path.join(
                 app.config['BASE_DIR'], 'Data/RFTN_Catalog.xml'),
                 data_path=app.config['BASE_DIR'])

if __name__ == "__main__":
    # ts = UTCDateTime("2016-01-01")
    # tf = UTCDateTime("2019-12-20")
    # get_stations(network="PE", starttime=ts, endtime=tf, level="station")
    # get_events(starttime=ts, endtime=tf, minmagnitude=6.0)
    # invdict = tst.get_contents()
    # for i in cat:
    #    print(i)
    # get_data('Data/RFTN_Stations.xml', 'Data/RFTN_Catalog.xml')
