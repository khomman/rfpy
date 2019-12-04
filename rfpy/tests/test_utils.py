import os
import shutil

from rfpy.util import read_station_file, read_rftn_file, read_rftn_directory


def build_test_directory_structure():
    stas = ['PE_PAKC', 'TA_O54A']
    pe_filts = ['1.0', '5.0']
    ta_filts = ['2.5']
    os.mkdir('TestData')
    os.mkdir('TestData/Data')
    for sta in stas:
        os.mkdir(f'TestData/Data/{sta}')
        if sta.startswith('PE'):
            for f in pe_filts:
                os.mkdir(f'TestData/Data/{sta}/{f}')
                with open(f'TestData/Data/{sta}/{f}/tmp1', 'w'):
                    pass
                with open(f'TestData/Data/{sta}/{f}/tmp2', 'w'):
                    pass
        if sta.startswith('TA'):
            for f in ta_filts:
                os.mkdir(f'TestData/Data/{sta}/{f}')
                with open(f'TestData/Data/{sta}/{f}/tmp1', 'w'):
                    pass


def teardown_test_directory_structure():
    shutil.rmtree('TestData')


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


def test_read_rftn_directory():
    cur = os.getcwd()
    build_test_directory_structure()
    rfs = read_rftn_directory(os.path.join(cur, 'TestData'))
    assert 'TA_O54A' in rfs
    assert 'PE_PAKC' in rfs
    assert '1.0' in rfs['PE_PAKC']
    assert '5.0' in rfs['PE_PAKC']
    assert '2.5' in rfs['TA_O54A']
    assert len(rfs['PE_PAKC']['1.0']) == 2
    assert len(rfs['TA_O54A']['2.5']) == 1
    assert rfs['PE_PAKC']['5.0'][0] == f'{cur}/TestData/Data/PE_PAKC/5.0/tmp2'
    teardown_test_directory_structure()
