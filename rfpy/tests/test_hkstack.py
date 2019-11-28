import numpy as np
from obspy import read
from rfpy.hkstack import HKStack


def build_test_stream():
    st = read('../../sampledata/TA/M54A/*1.0.eqr')
    return st


def test_set_hkgrid():
    st = build_test_stream()
    hk = HKStack(st, station='TA_M54A', depth_range=(30, 40), depth_inc=1,
                 kappa_range=(1.6, 2.0), kappa_inc=0.1)
    depths = hk.depths
    kappas = hk.kappas
    assert [depths[0], depths[-1], kappas[0], np.round(kappas[-1], 1),
            len(depths), len(kappas)] == [30, 39, 1.6, 1.9, 10, 4]


def test_make_bootstrap_st():
    st = build_test_stream()
    hk = HKStack(st, station='TA_M54A')
    bs_st = hk._make_bootstrap_st()
    assert len(bs_st) == len(st)


def test_covariance_ellipse():
    pass


def test_do_hkstack():
    pass
