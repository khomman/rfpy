import os

from rfpy import db
from rfpy.models import Stations, ReceiverFunctions, HKResults, Filters


def setup_db():
    db.create_all()


def teardown_db():
    db.session.remove()
    db.drop_all()
    os.remove('db/rftns.db')
    os.rmdir('db')
    os.rmdir('plots')
    os.rmdir('exports')


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


def build_test_data():
    # First drop and rebuild the tables from prior test
    db.drop_all()
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


def test_relationships():
    build_test_data()
    # Stations and rf relationships, 1st station should have 5 rftn, 2nd 9
    first_sta = Stations.query.get(1)
    first_sta_receiver_functions = [i for i in first_sta.receiver_functions]
    second_sta = Stations.query.get(2)
    second_sta_receiver_functions = [i for i in second_sta.receiver_functions]
    assert len(first_sta_receiver_functions) == 5
    assert len(second_sta_receiver_functions) == 9

    # Stations and hk relationship
    first_hk = [i for i in first_sta.hks]
    second_hk = [i for i in second_sta.hks]
    assert len(first_hk) == 1
    assert len(second_hk) == 1
    assert first_hk[0].h == 3.5
    assert first_hk[0].k == 1.7
    assert second_hk[0].h == 44.5
    assert second_hk[0].k == 1.77

    first_filt = Filters.query.get(1)
    first_filt_rf = [i for i in first_filt.receiver_functions]
    second_filt = Filters.query.get(2)
    second_filt_rf = [i for i in second_filt.receiver_functions]
    assert len(first_filt_rf) == 5
    assert len(second_filt_rf) == 9

    first_filt_hk = [i for i in first_filt.hks]
    second_filt_hk = [i for i in second_filt.hks]
    assert len(first_filt_hk) == 1
    assert len(second_filt_hk) == 1


def test_backref():
    build_test_data()
    # hk backrefs
    hks = HKResults.query.all()
    backref_station_first = hks[0].hk_station
    backref_station_second = hks[1].hk_station
    backref_filt_first = hks[0].hk_filter
    backref_filt_second = hks[1].hk_filter
    assert backref_station_first.station == 'PE_PARS'
    assert backref_station_second.station == 'PE_PAKC'
    assert backref_filt_first.filter == 2.5
    assert backref_filt_second.filter == 1.0

    # rftn backrefs
    rfs = ReceiverFunctions.query.all()
    backref_station_first = rfs[0].station_receiver_functions
    backref_station_last = rfs[-1].station_receiver_functions
    backref_filt_first = rfs[0].filter_receiver_functions
    backref_filt_last = rfs[-1].filter_receiver_functions
    assert backref_station_first.station == 'PE_PARS'
    assert backref_station_last.station == 'PE_PAKC'
    assert backref_filt_first.filter == 2.5
    assert backref_filt_last.filter == 1.0

    teardown_db()
