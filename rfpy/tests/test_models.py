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
    rf_description = [rf.id, rf.station, rf.filter, rf.path,
                      rf.new_receiver_function, rf.accepted]
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
    setup_db()
    sta = Stations(station='TA_M54A', latitude=41.444, longitude=-79.34,
                   elevation=345)
    db.session.add(sta)
    db.session.commit()
    sta_query = Stations.query.first()
    assert sta == sta_query


def test_add_receiver_functions():
    rftn = ReceiverFunctions(station=1, filter=1, path='/some/path/to/data',
                             new_receiver_function=True, accepted=True)
    db.session.add(rftn)
    db.session.commit()
    rftn_query = ReceiverFunctions.query.first()
    assert rftn == rftn_query


def test_add_hkresults():
    hk = HKResults(station=1, filter=1, hkpath='some/path',
                   savedhkpath='another/path', h=5.5, sigmah=0.2, k=1.75,
                   sigmak=0.03, vp=5.8)
    db.session.add(hk)
    db.session.commit()
    hk_query = HKResults.query.first()
    assert hk == hk_query


def test_add_filters():
    filt = Filters(filter=1.0)
    db.session.add(filt)
    db.session.commit()
    filt_query = Filters.query.first()
    assert filt == filt_query


def test_relationships():
    # First drop and rebuild the tables from prior test
    Stations.__table__.drop()
    ReceiverFunctions.__table__.drop()
    HKResults.__table__.drop()
    Filters.__table__.drop()
    setup_db()

    # add more rftn, stations, hkresults, and filters
    sta = Stations(station='PE_PARS', latitude=-23.333, longitude=-99.999,
                   elevation=234.3)
    sta_two = Stations(station='PE_PAKC', latitude=88.8888, longitude=234.23,
                       elevation=28.1)
    filt = Filters(filter=2.5)
    filt_two = Filters(filter=1.0)
    hk = HKResults(station=1, filter=1, hkpath='/some/path',
                   savedhkpath='/some/other/path', h=3.5, sigmah=1.4, k=1.7,
                   sigmak=0.2, vp=5.2)
    hk_two = HKResults(station=2, filter=2, hkpath='/some/path',
                       savedhkpath='/some/other/path', h=44.5, sigmah=1.4,
                       k=1.77, sigmak=0.2, vp=6.2)
    # Add 5 rftn to 1st station
    for i in range(5):
        rftn = ReceiverFunctions(station=1, filter=1,
                                 path='/some/path/to/data',
                                 new_receiver_function=True, accepted=True)
        db.session.add(rftn)
    # Add 9 rftn to 2nd station and 2nd filter
    for i in range(9):
        rftn = ReceiverFunctions(station=2, filter=2,
                                 path='/some/path/to/data',
                                 new_receiver_function=True, accepted=True)
        db.session.add(rftn)

    db.session.add(hk)
    db.session.add(hk_two)
    db.session.add(sta)
    db.session.add(sta_two)
    db.session.add(filt)
    db.session.add(filt_two)
    db.session.commit()

    # Stations and rf relationships, 1st station should have 5 rftn
    first_sta = Stations.query.get(1)
    second_sta = Stations.query.get(2)
    assert len(first_sta.station_receiver_functions) == 5
    assert len(second_sta.station_receiver_functions) == 5
