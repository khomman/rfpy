import os

import numpy as np

from rfpy.util import read_station_file, read_rftn_file


def build_test_station_file():
    # station file
    stas = ['TA_M55A 41.555 -77.555 234.0',
            'TA_M54A 41.234 -78.234 254.2',
            'PE_PAKC 40.534 -77.328 823.2']

    with open('test_read_sta.txt', 'w') as f:
        for sta in stas:
            f.write(f'{sta}\n')


def build_test_rftn_file():
    # Receiver Function file
    rfs = ['TA_O56A 1.0 /path/to/data/1',
           'TA_O56A 2.5 /path/to/data/2',
           'PE_PSUF 5.0 /path/to/data/3',
           'LD_ALLY 1.0 /path/to/data/4']

    with open('test_read_rf.txt', 'w') as f:
        for rf in rfs:
            f.write(f'{rf}\n')


def teardown_test_files():
    os.remove('test_read_rf.txt')
    os.remove('test_read_sta.txt')


def test_read_station_filt():
    build_test_station_file()
    stas = read_station_file('test_read_sta.txt')
    assert len(stas) == 3
    assert stas[0][0] == 'TA_M55A'
    assert stas[-1][-1] == '823.2'


def test_read_rftn_file():
    build_test_rftn_file()
    rf = read_rftn_file('test_read_rf.txt')
    assert len(rf) == 3
    assert rf['TA_O56A']['1.0'] == ['/path/to/data/1']
    assert rf['TA_O56A']['2.5'] == ['/path/to/data/2']
    teardown_test_files()