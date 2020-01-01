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
        os.mkdir('Data')

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
        os.mkdir('Data')
    filename = os.path.join(data_path, 'Data', 'RFTN_Catalog.xml')
    cat.write(filename, format='QUAKEML')


def get_data(staxml, quakeml, data_path=os.getcwd(), **kwargs):
    client = init_client()
    cat = read_events(quakeml, format='QUAKEML')
    inv = read_inventory(staxml, format='STATIONXML')
    model = init_model()

    if not os.path.exists(os.path.join(data_path, 'Data')):
        os.mkdir(os.path.join(data_path, 'Data'))

    for event in cat:
        origin_time = event.origins[0].time.strftime("%Y-%m-%dT%I:%M:%S")
        if not os.path.exists(os.path.join(data_path, 'Data',
                              origin_time)):
            os.mkdir(os.path.join(data_path, 'Data', origin_time))

        for net in inv:
            for sta in net:
                # p_arrival = model.get_travel_times(s ource_depth_in_km=event.orgins[0].depth)
                sta_lat = sta.latitude
                sta_lon = sta.longitude
                ev_lat = event.origins[0].latitude
                ev_lon = event.origins[0].longitude
                ev_time = UTCDateTime(event.origins[0].time)
                dist_degree = kilometer2degrees(gps2dist_azimuth(sta_lat,
                                                sta_lon, ev_lat,
                                                ev_lon)[0]/1000)
                if dist_degree > 30 and dist_degree < 90:
                    try:
                        st = client.get_waveforms(net.code, sta.code, "*",
                                              "HH*", ev_time,
                                              ev_time + 300)
                        st.write(f'{os.path.join(data_path, "Data", origin_time)}/{net.code}_{sta.code}.mseed')
                    except:
                        pass
                print(net.code, sta.code)
                print(type(event.origins[0].time))
                print(ev_time)
                print(dist_degree)
        print(event.origins[0].time)



if __name__ == "__main__":
    ts = UTCDateTime("2016-01-01")
    tf = UTCDateTime("2019-12-20")
    get_stations(network="PE", starttime=ts, endtime=tf, level="station")
    get_events(starttime=ts, endtime=tf, minmagnitude=6.0)
    #invdict = tst.get_contents()
    # for i in cat:
    #    print(i)
    get_data('Data/RFTN_Stations.xml', 'Data/RFTN_Catalog.xml')