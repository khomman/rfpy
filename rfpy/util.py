from obspy import read, Stream
# from rfpy import app, db
# from rfpy.models import Stations, Data, Filters, HKResults
# from config import DATA_ARCHIVE_STRUCTURE


def read_station_file(stafile):
    '''
    Reads a file in the current directory that contains space delimited
    station information.  Columns consist of station, latitude, longitude,
    elevation.

    TA_M55A 41.555 -77.555 234.0
    TA_M54A 40.234 -78.092 353.5

    :param stafile: Name of input file
    :type stafile: str
    :return: List of lists of stations... [[TA_M55A, 41.555, -77.555, 234.0],
                                           [TA_M54A, 40.234, -78.092, 353.5]]
    :rtype: List
    '''

    stas = []
    with open(stafile, 'r') as f:
        for line in f.readlines():
            sta, lat, lon, ele = line.split()
            stas.append([sta, lat, lon, ele])
    return stas


def read_rftn_file(rftn_file):
    data_paths = {}
    with open(rftn_file, 'r') as f:
        for line in f.readlines():
            if line.startswith("#"):
                continue
            station, filter, path = line.split()
            if station not in data_paths:
                data_paths[station] = {}
            if filter not in data_paths[station]:
                data_paths[station][filter] = []

            data_paths[station][filter].append(path)

    return data_paths


def rftn_stream(rftn_list):
    st = Stream()
    for i, rftn in enumerate(rftn_list):
        st += read(rftn)
        st[i].stats['name'] = rftn
    return st
