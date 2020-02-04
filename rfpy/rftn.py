import os

from obspy import read, Trace, UTCDateTime, read_events, read_inventory
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees
from obspy.taup import TauPyModel

from rfpy import db
from rfpy.decov import decovit
from rfpy.models import Earthquakes, ReceiverFunctions, Filters, Stations

# Header map from obspy tr.stats['rf'] to sac.  rf stats that are not
# inherently in sac files are placed in 'user?' blocks. User blocks are chosen
# to be consistent with the output from Ammon's iterdecon.f
# user0: Gaussian Width
# user1: event id (only the integer portion)
# user2: incident angle
# user3: takeoff angle
# user4: ray_paramerer
# user5: rms

# NEED TO MAP EV_RESOURCE_ID TO A SINGLE NUMBER AS SAC CANNOT STORE ######
# STRINGS.  USE DB TABLE ID? OR HOW TO MAKE IT UNIQUE WITHOUT DB    ######
# 'ev_resource_id': 'user1',
HEADERS_MAP = {'ev_lat': 'evla', 'ev_lon': 'evlo',
               'ev_dep_m': 'evdp', 'sta_lat': 'stla',
               'sta_lon': 'stlo', 'baz': 'baz', 'gcarc': 'gcarc',
               'P': 'user0', 'trim_start': 'b',
               'ray_param': 'user8', 'incident_angle': 'user2',
               'takeoff_angle': 'user3', 'gaussian': 'user0', 'rms': 'user5'}


def _SAC2UTC(stats, head):
    from obspy.io.sac.util import get_sac_reftime
    return get_sac_reftime(stats.sac) + stats[head]


def _UTC2SAC(stats, head):
    from obspy.io.sac.util import get_sac_reftime
    return stats[head] - get_sac_reftime(stats.sac)


def _rf2sac_headers(tr, headers):
    if 'sac' not in tr.stats:
        tr.stats.sac = {}
    for key, value in headers.items():
        tr.stats.sac[value] = tr.stats.rf[key]


def _sac2rf_headers(tr, headers):
    if 'rf' not in tr.stats:
        tr.stats.rf = {}
    for key, value in headers.items():
        tr.stats.rf[key] = tr.stats.sac[value]


def set_stats(st, inv, ev):
    """
    Sets needed information for rftn calculation in the stats dictionary for
    each trace in the Stream.  This information consists of back_azimuth,
    distance, origin time, P wave arrival.
    :param st: Obspy Stream object containing one station 3 channels
    :param inv: Obpsy Inventory object containing stations
    :param ev: Obspy event object for the earthquake
    """

    origin_time = ev.origins[0].time
    ev_lat = ev.origins[0].latitude
    ev_lon = ev.origins[0].longitude
    ev_dep_m = ev.origins[0].depth
    ev_resource_id = ev.resource_id.id
    sta_inv = inv.select(network=st[0].stats.network,
                         station=st[0].stats.station)
    sta_lat = sta_inv[0][0].latitude
    sta_lon = sta_inv[0][0].longitude
    gcarc_m, baz, _ = gps2dist_azimuth(sta_lat, sta_lon, ev_lat, ev_lon)
    gcarc_deg = kilometer2degrees(gcarc_m/1000)
    rf = {
          'origin_time': origin_time,
          'ev_lat': ev_lat,
          'ev_lon': ev_lon,
          'ev_resource_id': ev_resource_id,
          'ev_dep_m': ev_dep_m,
          'sta_lat': sta_lat,
          'sta_lon': sta_lon,
          'gcarc': gcarc_deg,
          'baz': baz,
          'method': 'P'
    }
    for tr in st:
        tr.stats.rf = rf
        tr.stats['back_azimuth'] = baz


def _rel_trim(st, before, after, reference='P'):
    """
    Internal trim function. Uses obspy trim function to cut waveforms
    relative to the arrival provided by reference
    :param st: Obspy stream
    :param before: Seconds before reference time to start trim
    :param after: Seconds after reference time to end trim
    :param reference: Header value containing arrival time to trim around.
        header is in trace.stats.rf
    """
    for tr in st:
        try:
            start_cut = tr.stats.rf[reference] - before
            end_cut = tr.stats.rf[reference] + after
        except KeyError:
            print(f'Trace {tr.id} is missing arrival information')
            print('Removing from stream')
            st.remove(tr)
            continue

        if len(tr) == 0:
            print(f'Arrival is out of range for {tr.id}')
            print('Removing from stream')
            st.remove(tr)
            continue

        tr.trim(starttime=start_cut, endtime=end_cut, nearest_sample=False)
    return


def _add_arrivals(st, use_db=True, model='iasp91'):
    """
    Internal function to calculate or retrieve the theoretical arrival times.
    Will grab from the Arrivals table in the database by defualt or will
    calculate arrival times using obspy.taup and the given model
    :param st: Obspy stream object
    :param use_db: Use the rfpy database to query the arrival table
    :param model: Model to use to calculate arrival time if use_db is False
    """
    sta = f'{st[0].stats.network}_{st[0].stats.station}'
    # Query Earthquakes and use backrefs to get arrivals and station info for
    # that event.  Add to trace.stats.rf dict once a matching station arrival
    # is found.
    if use_db:
        ev_id = st[0].stats.rf['ev_resource_id']
        eq_db = Earthquakes.query.filter_by(resource_id=ev_id).first()
        for i in eq_db.earthquake_arr:
            if i.station.station == sta:
                arr = UTCDateTime(i.time)
                rayp = i.rayp
                inc_angle = i.inc_angle
                take_angle = i.take_angle
                break
    else:
        if not isinstance(model, TauPyModel):
            model = TauPyModel(model)
        ev_dep_km = st[0].stats.rf['ev_dep']/1000.0
        dist_deg = st[0].stats.rf['gcarc']
        ev_time = st[0].stats.rf['origin_time']
        arrs = model.get_travel_times(source_depth_in_km=ev_dep_km,
                                      distance_in_degree=dist_deg,
                                      phase_list=['P'])
        arr = ev_time + arrs[0].time

    for tr in st:
        tr.stats.rf['P'] = arr
        tr.stats.rf['ray_param'] = rayp
        tr.stats.rf['incident_angle'] = inc_angle
        tr.stats.rf['takeoff_angle'] = take_angle
    return


def rf_calc(st, prefilt=(0.05, 8), dt=0.1, gauss=[1.0], trim=(10, 100),
            use_db=True):
    """
    Processes the 3 channel stream and calculates the radial and transverse
    receiver functions.  Processing consists of removing the trends, filtering,
    and windowing the data around the P-wave.  The rftn is calculated by the
    decovit function from Xumi1993/seispy/decov.py
    Assumes that rf headers (gcarc, baz, sta_lat, sta_lon, ev_lat, ev_lon) are
    included in Trace.stats.rf
    :param st: Obspy stream containing 1 station 3 channels
    :param filter: Tuple with the minimum and maximum freqs for bandpass filter
    :param dt: sample rate for interpolating the stream
    :param gauss: List containing the gaussian filter values
    """
    back_azimuth = st[0].stats.rf['baz']
    _add_arrivals(st)
    _rel_trim(st, trim[0], trim[1])
    st.detrend('demean')
    st.detrend('linear')
    st.taper(max_percentage=0.05, max_length=0.2)
    st.filter(type='bandpass', freqmin=prefilt[0], freqmax=prefilt[1])
    st.interpolate(1/dt)
    st.rotate('NE->RT', back_azimuth=back_azimuth)
    vert = st.select(component='Z')[0]
    radial = st.select(component='R')[0]
    trans = st.select(component='T')[0]
    rfs = []
    for g in gauss:
        rad_rf_data = decovit(radial, vert, dt=dt, f0=g)
        trans_rf_data = decovit(trans, vert, dt=dt, f0=g)
        rad_rf = Trace(rad_rf_data[0], header=radial.stats)
        rad_rf_rms = rad_rf_data[1][-1]
        trans_rf = Trace(trans_rf_data[0], header=trans.stats)
        trans_rf_rms = trans_rf_data[1][-1]
        rad_rf.stats.rf['gaussian'] = str(g)
        rad_rf.stats.rf['rms'] = rad_rf_rms
        rad_rf.stats.rf['trim_start'] = -trim[0]
        trans_rf.stats.rf['gaussian'] = str(g)
        trans_rf.stats.rf['rms'] = trans_rf_rms
        trans_rf.stats.rf['trim_start'] = -trim[0]

        rfs.append((rad_rf, trans_rf, rad_rf_rms, g))

    return rfs


def rfpy_calc_rf(st, data_path=os.getcwd(), rms_cutoff=0.15, **kwargs):
    """
    Calculate receiver functions specifically for rfpy web app.  Saves
    receiver functions in data location under RF directory
    :param st: Obspy Stream containing 1 station 3 channels
    :param data_path: base directory for data
    """
    rfs = rf_calc(st, **kwargs)
    event = rfs[0][0].stats.rf['origin_time'].strftime("%Y-%m-%dT%H:%M:%S")
    save_path = os.path.join(data_path, 'Data', event, 'RF')

    station = f'{rfs[0][0].stats.network}_{rfs[0][0].stats.station}'

    sta_id = Stations.query.filter_by(station=station).first().id

    # Ensure all gaussian filters are in filter table
    filts = [f.filter for f in Filters.query.all()]
    for g in kwargs['gauss']:
        if g not in filts:
            print(f"{g} not in filters table..Adding now")
            filter = Filters(filter=float(g))
            db.session.add(filter)
            db.session.commit()
    # AFter filters checked get filter id adn write traces files to sac(others?
    # and add to receiver function db table
    for rf in rfs:
        gauss = rf[3]
        fname = f'{station}_{event}_{gauss}.eq'
        trans_name = f'{fname}t'
        rad_name = f'{fname}r'
        filt_id = Filters.query.filter_by(filter=float(gauss)).first().id
        rms = rf[2]
        rad_rf = rf[0]
        trans_rf = rf[1]
        _rf2sac_headers(rad_rf, HEADERS_MAP)
        _rf2sac_headers(trans_rf, HEADERS_MAP)
        rad_rf.write(f'{save_path}/{rad_name}', format="SAC")
        trans_rf.write(f'{save_path}/{trans_name}', format="SAC")
        initial_accept = True if rms < rms_cutoff else False

        rad_rf_db = ReceiverFunctions(station=sta_id, filter=filt_id,
                                      path=f'{save_path}/{rad_name}',
                                      new_receiver_function=True,
                                      accepted=initial_accept)
        trans_rf_db = ReceiverFunctions(station=sta_id, filter=filt_id,
                                        path=f'{save_path}/{trans_name}',
                                        new_receiver_function=True,
                                        accepted=initial_accept)
        db.session.add(rad_rf_db)
        db.session.add(trans_rf_db)
        db.session.commit()


def _async_rf_calc(app, **kwargs):
    data = kwargs['data']
    rms_cut = kwargs['rms_cut']
    kwargs.pop('data')
    kwargs.pop('rms_cut')
    inv_path = os.path.join(app.config["BASE_DIR"], 'Data/RFTN_Stations.xml')
    cat_path = os.path.join(app.config["BASE_DIR"], 'Data/RFTN_Catalog.xml')
    inv = read_inventory(inv_path)
    cat = read_events(cat_path)
    for d in data:
        st = read(d[0])
        eq_id = d[1]
        eq_time = Earthquakes.query.filter_by(id=eq_id).first().origin_time
        origin_time = UTCDateTime(eq_time)
        t1 = origin_time - 1
        t2 = origin_time + 1
        ev = cat.filter(f"time >= {t1}", f"time <= {t2}")[0]
        set_stats(st, inv, ev)
        rfpy_calc_rf(st, rms_cutoff=rms_cut, **kwargs)
