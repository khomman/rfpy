import os
import glob

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np

def rftn_plot(eqr_st,eqt_st,start_second=-1,end_second=10,
                base_path=os.getcwd()):
    '''
    Create individual plots of receiver functions.
    :param eqr_st: Obspy Stream of radial receiver functions
    :param eqt_st: Obspy Stream of transverse receiver functions
    :param start_second: Seconds before P-arrival to plot
    :param end_second: Seconds after P-arrival to plot
    :param base_path: Path to prepend to static/*svg
    '''
    plotfiles = []
    eqr_st = eqr_st.sort(['name'])
    eqt_st = eqt_st.sort(['name'])
    for filename in glob.glob(os.path.join(base_path,'static','*.svg')):
        os.remove(filename)
    for i,tr in enumerate(eqr_st):
        if tr.stats['name'][-3:] == 'eqr' and tr.stats['name'][:-3] == eqt_st[i].stats['name'][:-3]:
            delta = tr.stats.delta
            tr_start = tr.stats.sac['b']
            start_second = float(start_second)
            end_second = float(end_second)
            beg_sample = int(-1*tr_start/delta + start_second/delta)
            end_sample = int(-1*tr_start/delta + end_second/delta)
            eqttr = eqt_st[i]
            eqttimes = eqttr.times()+ tr_start
            eqtamplitudes = eqttr.data
            eqrtimes = tr.times() + tr_start
            eqramplitudes = tr.data
            trace = '{}'.format(tr.stats['name'].split('/')[-1])
            fig,(ax1,ax2) = plt.subplots(1,2,sharey=True,figsize=(12,1))
            ax1.plot(eqrtimes[beg_sample:end_sample],eqramplitudes[beg_sample:end_sample],
             'k-',linewidth=0.5)
            ax1.fill_between(eqrtimes[beg_sample:end_sample],0,
                eqramplitudes[beg_sample:end_sample],where=eqramplitudes[beg_sample:end_sample]>0,
                facecolor='red',interpolate=True,alpha=0.7)
            ax1.fill_between(eqrtimes[beg_sample:end_sample],0,
                eqramplitudes[beg_sample:end_sample],where=eqramplitudes[beg_sample:end_sample]<0,
                facecolor='blue',interpolate=True,alpha=0.7)
            ax1.spines['right'].set_visible(False)
            ax1.spines['top'].set_visible(False)
            ax1.xaxis.set_ticks_position('bottom')
            ax1.yaxis.set_ticks_position('left')
            ax2.plot(eqttimes[beg_sample:end_sample],eqtamplitudes[beg_sample:end_sample],
                'k-',linewidth=0.5)
            ax2.fill_between(eqttimes[beg_sample:end_sample],0,
                eqtamplitudes[beg_sample:end_sample],where=eqtamplitudes[beg_sample:end_sample]>0,
                facecolor='red',interpolate=True,alpha=0.7)
            ax2.fill_between(eqttimes[beg_sample:end_sample],0,
                eqtamplitudes[beg_sample:end_sample],where=eqtamplitudes[beg_sample:end_sample]<0,
                facecolor='blue',interpolate=True,alpha=0.7)
            ax2.spines['left'].set_visible(False)
            ax2.spines['top'].set_visible(False)
            ax2.xaxis.set_ticks_position('bottom')
            ax2.yaxis.set_ticks_position('none')
            if i == 0:
                ax1.set_title('EQR')
                ax2.set_title('EQT')
            plotfile = os.path.join(base_path,'static',f'{trace}.svg')
            plt.savefig(plotfile)
            plt.close()
            plotfiles.append(os.path.join('static', f'{trace}.svg'))
    return plotfiles

def _calulate_startend_sample(delta, starttime, plot_start, plot_end):
    beg_sample = int(-1*starttime/delta + plot_start/delta)
    end_sample = int(-1*starttime/delta + plot_end/delta)
    return beg_sample, end_sample

def baz_plot(ax, st, scaling=1, plot_start=-2, plot_end=30,
            label_position="left", ylabel="Back Azimuth"):
    for tr in st:
        baz = tr.stats.sac['baz']
        tr_start = tr.stats.sac['b']
        delta = tr.stats.delta
        beg_sample, end_sample = _calulate_startend_sample(delta, tr_start, plot_start, plot_end)
        times = tr.times() + tr_start
        amplitudes = (tr.data * scaling) + baz
        ax.plot(times[beg_sample:end_sample], amplitudes[beg_sample:end_sample], 'k-', linewidth=0.3)
        ax.fill_between(times[beg_sample:end_sample],baz,
                amplitudes[beg_sample:end_sample],where=amplitudes[beg_sample:end_sample]>baz,
                facecolor='red',interpolate=True,alpha=0.85)
        ax.fill_between(times[beg_sample:end_sample],baz,
                amplitudes[beg_sample:end_sample],where=amplitudes[beg_sample:end_sample]<baz,
                facecolor='blue',interpolate=True,alpha=0.85)
        ax.set_ylim(-2, 362)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel(ylabel)
        if label_position == "right":
            ax.yaxis.set_label_position("right")
            ax.yaxis.tick_right()

def dist_plot(ax, st, scaling=1, plot_start=-2, plot_end=30,
                label_position="left",
                ylabel="Epicentral Distance ($^\circ$)"):
    for tr in st:
        dist = tr.stats.sac['gcarc']
        tr_start = tr.stats.sac['b']
        delta = tr.stats.delta
        beg_sample, end_sample = _calulate_startend_sample(delta, tr_start, plot_start, plot_end)
        times = tr.times() + tr_start
        amplitudes = (tr.data * scaling) + dist
        ax.plot(times[beg_sample:end_sample], amplitudes[beg_sample:end_sample], 'k-', linewidth=0.3)
        ax.fill_between(times[beg_sample:end_sample],dist,
                amplitudes[beg_sample:end_sample],where=amplitudes[beg_sample:end_sample]>dist,
                facecolor='red',interpolate=True,alpha=0.85)
        ax.fill_between(times[beg_sample:end_sample],dist,
                amplitudes[beg_sample:end_sample],where=amplitudes[beg_sample:end_sample]<dist,
                facecolor='blue',interpolate=True,alpha=0.85)
        ax.set_ylim(25, 95)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel(ylabel)
        if label_position == "right":
            ax.yaxis.set_label_position("right")
            ax.yaxis.tick_right()

def rayp_plot(ax, st, scaling=1, plot_start=-2, plot_end=30,
                label_position="left", ylabel="Ray Parameter"):
    for tr in st:
        rayp = tr.stats.sac['user8']
        tr_start = tr.stats.sac['b']
        delta = tr.stats.delta
        beg_sample, end_sample = _calulate_startend_sample(delta, tr_start, plot_start, plot_end)
        times = tr.times() + tr_start
        amplitudes = (tr.data * scaling) + rayp
        ax.plot(times[beg_sample:end_sample], amplitudes[beg_sample:end_sample], 'k-', linewidth=0.3)
        ax.fill_between(times[beg_sample:end_sample],rayp,
                amplitudes[beg_sample:end_sample],where=amplitudes[beg_sample:end_sample]>rayp,
                facecolor='red',interpolate=True,alpha=0.85)
        ax.fill_between(times[beg_sample:end_sample],rayp,
                amplitudes[beg_sample:end_sample],where=amplitudes[beg_sample:end_sample]<rayp,
                facecolor='blue',interpolate=True,alpha=0.85)
        ax.set_ylim(0.04, 0.081)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel(ylabel)
        if label_position == "right":
            ax.yaxis.set_label_position("right")
            ax.yaxis.tick_right()


def base_map(projection='local', center_lat=0, center_lon=0, extent=None,
            **kwargs):
    '''
    Function to plot a basic map which can be used to add data later.
    '''
    if projection == 'global':
                ax = plt.axes(projection=ccrs.Mollweide(central_longitude=center_lon))
    elif projection == 'local':
        ax = plt.axes(projection=ccrs.AlbersEqualArea(
            central_latitude=center_lat,
            central_longitude=center_lon))
        if extent:
            ax.set_extent(extent)
    else:
        print('Projection not supported')
    ax.coastlines()
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.BORDERS, linestyle='-')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    return ax

def _calculate_extent_with_cushion(lats, lons):
    max_lat = max(lats)
    min_lat = min(lats)
    max_lon = max(lons)
    min_lon = min(lons)
    #try to set reasonable map distance around stations
    if abs(max_lat - min_lat) < 1:
        lat_cushion = 0.25
    elif 1 < abs(max_lat - min_lat) < 5:
        lat_cushion = 0.5
    else:
        lat_cushion = 1.0
    if abs(max_lon - min_lon) < 1:
        lon_cushion = 0.25
    elif 1 < abs(max_lon - min_lon) < 5:
        lon_cushion = 0.5
    else:
        lon_cushion = 1.0
    extent = [min_lon-lon_cushion, max_lon+lon_cushion, min_lat-lat_cushion,
                max_lat+lat_cushion]
    return extent

def station_map(sta_lats, sta_lons, sta_names=None, projection='local',
                filename=None):
    '''
    Plot a simple station map.  Currently only uses one color and symbol.
    :param sta_lats: List of latitudes for stations
    :type sta_lats: List
    :param sta_lons: List of longitudes for stations
    :type sta_lons: List
    :param sta_names: List of optional station names
    :type sta_names: List
    :param projection: Type of projection to use.  Currently supports
                        'local' and 'global'
    :type projection: Str
    '''
    center_lat = np.mean(sta_lats)
    center_lon = np.mean(sta_lons)
    data_crs = ccrs.Geodetic()
    if projection == 'global':
        ax = base_map(projection='global', center_lat=0,
                        center_lon=center_lon)
        ax.scatter(sta_lons, sta_lats, color='red', marker='v',
                    transform=data_crs)
    elif projection == 'local':
        extent = _calculate_extent_with_cushion(sta_lats, sta_lons)
        ax = base_map(projection='local', center_lat=center_lat,
                    center_lon=center_lon,extent=extent)
        ax.scatter(sta_lons, sta_lats, color='red', marker='v',
                    transform=data_crs)
    if sta_names:
        for i,name in enumerate(sta_names):
            ax.text(sta_lons[i], sta_lats[i]+0.1, name,
            transform=data_crs)

    if filename:
        plt.savefig(filename)
        return
    return ax

def hk_map(sta_lats, sta_lons, hk_vals, sta_names=None, projection='local',
            filename=None):
    '''
    Plots a simple map of stations colored by HK stack results
    '''
    center_lat = np.mean(sta_lats)
    center_lon = np.mean(sta_lons)
    data_crs = ccrs.Geodetic()
    if projection == 'global':
        ax = base_map(projection='global', center_lat=0,
                        center_lon=center_lon)
        ax.scatter(sta_lons, sta_lats, c=hk_vals, marker='v', cmap='viridis',
                    transform=data_crs)
    elif projection == 'local':
        extent = _calculate_extent_with_cushion(sta_lats, sta_lons)
        ax = base_map(projection='local', center_lat=center_lat,
                    center_lon=center_lon,extent=extent)
        ax.scatter(sta_lons, sta_lats, c=hk_vals, marker='v',
                    cmap='viridis', transform=data_crs)
    if sta_names:
        for i,name in enumerate(sta_names):
            ax.text(sta_lons[i], sta_lats[i]+0.1, name,
            transform=data_crs)
    
    if filename:
        plt.savefig(filename)
        return
    return ax