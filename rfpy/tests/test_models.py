import os

from rfpy import db
from rfpy.models import Stations, ReceiverFunctions, HKResults, Filters

def setup_db():
    db.create_all()

def teardown_db():
    db.session.remove()
    db.drop_all()
    os.remove('db/rftns.db')
    os.rmdir('db/')

def test_stations():
    sta = Stations(station="PE_PARS", latitude=41.555, longitude=-77.342, 
                    elevation=234.2, status="D")
    sta_description = [sta.id, sta.station, sta.latitude, sta.longitude,
                        sta.elevation, sta.status]
    assert sta_description == [None, "PE_PARS", 41.555, -77.342, 234.2, "D"]

def test_receiver_functions():
    rf = ReceiverFunctions(station=1, filter=1, path="/path/to/rftn", 
                            new_receiver_function=1, accepted=0)
    rf_description = [rf.id, rf.station, rf.filter, rf.path, rf.new_receiver_function,
                        rf.accepted]
    assert rf_description == [None, 1, 1, "/path/to/rftn", 1, 0]

def test_filters():
    filter = Filters(filter=2.5)
    assert 2.5 == filter.filter

def test_hkresult():
    hk = HKResults(station=2, filter=1, hkpath="/path/to/HK",
                    savedhkpath="/path/to/saved/HK", h=5.5, sigmah=0.5,
                    k=1.75, sigmak=0.15, vp=6.2)
    hk_description = [hk.station, hk.filter, hk.hkpath, hk.savedhkpath,
                        hk.h, hk.sigmah, hk.k, hk.sigmak, hk.vp]
    assert hk_description == [2, 1, "/path/to/HK", "/path/to/saved/HK", 5.5,
                                0.5, 1.75, 0.15, 6.2]
    
def test_add_stations():
    pass

def test_add_receiver_functions():
    pass

def test_add_hkresults():
    pass

def test_add_filters():
    pass

