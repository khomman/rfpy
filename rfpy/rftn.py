from obspy import Trace, UTCDateTime
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees
from obspy.taup import TauPyModel

from rfpy.decov import decovit
from rfpy.models import Earthquakes


def set_stats(st, inv, ev):
    """
    Sets need information for rftn calculation in the stats dictionary for
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
    return


def rf(st, filter=(0.05, 8), dt=0.1, gauss=[1.0], trim=(10, 100), use_db=True):
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
    st.filter(type='bandpass', freqmin=filter[0], freqmax=filter[1])
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
        trans_rf.stats.rf['gaussian'] = str(g)
        trans_rf.stats.rf['rms'] = trans_rf_rms

        rfs.append((rad_rf, trans_rf, g))

    return rfs
