import os
import shutil

from obspy import read, UTCDateTime, read_events, read_inventory
from rfpy.data import get_data, get_events, get_stations


def setup():
    ts = UTCDateTime("2019-09-28")
    tf = UTCDateTime("2019-09-30")
    return ts, tf


def test_get_stations():
    ts, tf = setup()
    get_stations(network="PE", station="PAKC", starttime=ts, endtime=tf,
                 level="station")
    assert os.path.exists('Data/RFTN_Stations.xml')
    inv = read_inventory('Data/RFTN_Stations.xml')
    assert len(inv) == 1
    assert inv[0].code == 'PE'
    assert inv[0][0].code == 'PAKC'


def test_get_events():
    ts, tf = setup()
    get_events(starttime=ts, endtime=tf, minmagnitude=6.0)
    assert os.path.exists('Data/RFTN_Catalog.xml')
    cat = read_events('Data/RFTN_Catalog.xml')
    assert len(cat) == 2
    assert cat[0].origins[0].latitude == -35.4756
    assert cat[1].origins[0].latitude == 5.6929


def test_get_data():
    get_data('Data/RFTN_Stations.xml', 'Data/RFTN_Catalog.xml')
    assert os.path.exists('Data/2019-09-29T02:02:51')
    assert os.path.exists('Data/2019-09-29T15:57:53')
    assert os.path.exists('Data/2019-09-29T15:57:53/PE_PAKC.mseed')
    st = read('Data/2019-09-29T15:57:53/PE_PAKC.mseed')
    assert len(st) == 3
    assert len(st[0]) == 40000
    assert st[0].stats.channel == 'HHE'


# def teardown():
#    shutil.rmtree('Data/')
