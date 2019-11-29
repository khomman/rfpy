import os
from multiprocessing import Pool

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from obspy import Stream
from scipy.signal import hilbert


class HKStack:
    """
    An HKstack object.

    This object takes an Obspy stream of receiver functions and performs the
    HKstack method of Zhu and Kanamori, 2001.  The option to use the Phase
    Weight Stacking method of Schimmel and Paulssen, 1997 is also added.  See
    chapter 4 of Philip Crotwells dissertation for a description of Phase
    weight stacking of receiver functions.
    """
    def __init__(self, stream, station=None, vp=6.2, depth_range=(32, 50),
                 depth_inc=0.1, kappa_range=(1.6, 1.9), kappa_inc=0.01, w1=0.7,
                 w2=0.2, w3=0.1, pws=False, bs=False, bs_replications=200,
                 nell=250, starttime=-2, endtime=30, plotfile='hkstack.svg'):
        """
        Creates a new HKstack object.

        :param stream: An obspy stream object
        :param station: The station name corresponding to the stream
        :param vp: P-wave velocity (km/s). Defaults to 6.2
        :param depth_range: Tuple containing minimum and maximum depth (km)
            to create the stack. Defaults to (32,50)
        :param depth_inc: Increment value to use in building the depth array
            Defaults to 0.01.
        :param kappa_range: Tuple containing minimum and maximum kappa
            (vp/vs) to create the stack. Defaults to (1.6,1.9)
        :param kappa_inc: Increment value to use in building the kappa array
            Defaults to 0.01.
        :param w1: Weight to assign to the Ps arrival during stacking.
            Defaults to 0.7
        :param w2: Weight to assign to the PpPs arrival during stacking.
            Defaults to 0.2
        :param w3: Weight to assign to the PpSs arrival during stacking.
            Defaults to 0.1
        :param pws: Bool describing whether to use the phase weight stacking
            method of Schimmel and Paulssen, 1997.  Defaults to False
        :param bs:  Bool describing whether to do the bootstrapping method of
            Effron and Tibshirani, 1980. Defaults to False
        :param bs_replications:  Number of bootstrap iterations to perform if
            bs == True.  Defaults to 200.
        :param nell: Size to set array in for the covariance ellipse.
            Defaults to 250.
        :param starttime: Time(s) to start the receiver function plots.
            Defaults to -2s
        :param endtime: Time(s) to end the receiver function plots.
            Defaults to 30s
        :param plotfile: Location to save HKStack figure
            Defaults to hkstack.svg in current directory
        :var depths: Numpy array of input depths
        :var kappas: Numpy array of input kappas
        :var hh: Meshgrid output for depths
        :var kk: Meshgrid output for kapps
        :var stack: The calculated HKStack numpy array.
        :var maxh: Maximum value for stack along the depth axis
        :var maxk: Maximum value for stack along the kappa axis
        :var bootstrap_st: Obspy stream containing a random traces from
            the input stream.  Used to calculate bootstrap error.
        :var sigmak: Error associated with maxk
        :var sigmah: Error associated with maxh
        :var correl:
        :var ellipes: Tuple containing the (X,Y) for the ellipse to use in
            plotting.
        """
        self.stream = stream
        self.station = station
        self.vp = vp
        self.vs = None
        self.depth_range = depth_range
        self.depth_inc = depth_inc
        self.kappa_range = kappa_range
        self.kappa_inc = kappa_inc
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.pws = pws
        self.bs = bs
        self.bs_replications = bs_replications
        self.nell = nell
        self.starttime = starttime
        self.endtime = endtime
        self.plotfile = plotfile
        self.depths = None
        self.kappas = None
        self.hh = None
        self.kk = None
        self.stack = None
        self.maxh = None
        self.maxk = None
        self.bootstrap_st = None
        self.sigmak = None
        self.sigmah = None
        self.correl = None
        self.ellipse = None
        self.gaussian = stream[0].stats.sac['user0']
        self.network = stream[0].stats.network

        self._set_hkgrid()
        self._do_hkstack()
        if bs:
            self._do_bootstrap()
            self._covariance_ellipse()

        self.plot_hkstack()
        self.plot_rftn()

    def _set_hkgrid(self):
        """
        Builds a grid of x and y values using Numpy's meshgrid.

        Requires the start and end parameters for each axis as well as the
        increment for spacing.
        """
        x_start = self.depth_range[0]
        x_end = self.depth_range[1]
        y_start = self.kappa_range[0]
        y_end = self.kappa_range[1]
        self.depths = np.arange(x_start, x_end, self.depth_inc)
        self.kappas = np.arange(y_start, y_end, self.kappa_inc)
        self.hh, self.kk = np.meshgrid(self.depths, self.kappas, sparse=True)
        return self.depths, self.kappas, self.hh, self.kk

    def _do_hkstack(self, is_bs=False):
        """
        Computes the hkstack based on Zhu and Kanamori, 2001.

        Requires a Numpy array for depth and kappa values.  Also requires
        the meshgrid outputs for these arrays.  These can be output from the
        set_hkgrid function.  In addition, do_hkstack requires an ObsPy stream
        object that contains the radial receiver functions.

        The pws argument is used to utilize the Phase Weight Stacking method of
        Schimmel and Paulssen, 1997.  See chapter 4 of Philip Crotwell's
        dissertation for a description of Phase Weight use.  pws is a bool and
        defaults to False.
        """
        if is_bs:
            st = self.bootstrap_st
        else:
            st = self.stream

        self.vs = self.vp/self.kk
        stack = np.zeros((len(self.kk), len(self.hh)))
        for tr in st:
            p = tr.stats.sac['user8']
            beg = tr.stats.sac['b']
            delta = tr.stats.sac['delta']
            etap = np.sqrt(1/(self.vp**2) - p**2)
            etas = np.sqrt(1/(self.vs**2) - p**2)
            time_Ps = self.hh*(etas - etap)
            time_PpPs = self.hh*(etas + etap)
            time_PpSs = self.hh*(2*etas)
        # First had 1 + time_Ps etc but it was consistently lower answers
        # than fortran.  Made 0 and now it's consistent.  Figure out which is
        # correct then adjust code. and PWS code.
            t1 = 0 + ((time_Ps - beg)/delta).astype(int)
            t2 = 0 + ((time_PpPs - beg)/delta).astype(int)
            t3 = 0 + ((time_PpSs - beg)/delta).astype(int)
            rf1 = tr.data[t1] + (tr.data[(t1+1)] - tr.data[t1]) * (
                  time_Ps - beg - (t1-0) * delta)/delta
            rf2 = tr.data[t2] + (tr.data[(t2+1)] - tr.data[t2]) * (
                time_PpPs - beg - (t2-0) * delta)/delta
            rf3 = tr.data[t3] + (tr.data[(t3+1)] - tr.data[t3]) * (
                time_PpSs - beg - (t3-0) * delta)/delta

        # Phase Stack section
            if self.pws:
                analytic_tr = hilbert(tr)
                imrf1 = (np.cos(analytic_tr[t1]) + (0+1j) * np.sin(analytic_tr[t1]))+(
                    (np.cos(analytic_tr[(t1+1)]) + (0+1j)*np.sin(analytic_tr[(t1+1)])) -
                    (np.cos(analytic_tr[t1]) + (0+1j) * np.sin(analytic_tr[t1]))) *(
                    (time_Ps-beg - (t1-0) * delta)/delta)
                imrf2 = (np.cos(analytic_tr[t2]) + (0+1j) * np.sin(analytic_tr[t2])) + (
                    (np.cos(analytic_tr[(t2+1)]) + (0+1j) * np.sin(analytic_tr[(t2+1)])) -
                    (np.cos(analytic_tr[t2]) + (0+1j) * np.sin(analytic_tr[t2]))) *(
                    (time_PpPs - beg - (t2-0) * delta)/delta)
                imrf3 = (np.cos(analytic_tr[t3]) + (0+1j) * np.sin(analytic_tr[t3])) + (
                    (np.cos(analytic_tr[(t3+1)]) + (0+1j) * np.sin(analytic_tr[(t3+1)])) -
                    (np.cos(analytic_tr[t3]) + (0+1j) * np.sin(analytic_tr[t3]))) * (
                    (time_PpSs - beg - (t3-0) * delta)/delta)
            # pws s(h,k)
                stack = stack + ((self.w1*rf1 + self.w2*rf2 - self.w3*rf3) *
                    ((1/len(st))*np.abs(self.w1*imrf1 + self.w2*imrf2 - self.w3*imrf3)))

            else:
                stack = stack + self.w1*rf1 + self.w2*rf2 - self.w3*rf3

        smax = np.amax(stack)
        maxhk = np.where(stack == smax)
        maxh = self.depths[maxhk[1]]
        maxk = self.kappas[maxhk[0]]
        stack = stack.clip(min=0)
        stack = (stack*100.0)/smax
        maxvs = self.vp/maxk
        if is_bs:
            return stack, maxh, maxk, maxvs
        else:
            self.maxh = maxh
            self.maxk = maxk
            self.stack = stack
            self.maxvs = maxvs
            return

    def _make_bootstrap_st(self):
        """
        Creates an ObsPy Stream object for computing the bootstrap.

        make_bootstrap_st() takes the stream object used for computing
        the hkstack and picks random indices.  This returns a new stream
        of the randomly indexed receiver functions in order to calculate
        the bootstrap method of Efron and Tibshirani, 1980.
        """
        self.bootstrap_st = Stream()
        st_len = len(self.stream)
        for i in range(st_len):
            rfid = int(st_len * np.random.rand())
            self.bootstrap_st += self.stream[rfid]
        return self.bootstrap_st

    def _bootstrap_iter(self, iter):
        bootstrap_st = self._make_bootstrap_st()
        stack, maxh, maxk, vs = self._do_hkstack(is_bs=True)
        return maxh, maxk

    def _do_bootstrap(self):
        """
        Computes the bootstrapping method of Efron and Tibshirani, 1980.

        For each iteration in the range of replications, do_bootstrap() makes
        a bootstrap stream (make_bootstrap_st) and calculates the hkstack for
        the new stream.
        """

        bs_kappas = np.zeros(self.bs_replications)
        bs_depths = np.zeros(self.bs_replications)

        # multi-process this?  Just split bs_reps into 2 or 4 sections?
        # for rep in range(self.bs_replications):
        #     print('Bootstrap #: ' + str(rep))
        #     bootstrap_st = self._make_bootstrap_st()
        #     stack, maxh, maxk, vs = self._do_hkstack(is_bs=True)
        #     bs_kappas[rep] = maxk
        #     bs_depths[rep] = maxh

        # The below multiprocessing Pool implementation speeds up bootstrapping
        # significantly.  For test the computation time went from 5:47.40 to
        # 2:34.25
        pool = Pool()
        pool_result = pool.map(self._bootstrap_iter, range(self.bs_replications))
        for i in range(self.bs_replications):
            bs_kappas[i] = pool_result[i][1]
            bs_depths[i] = pool_result[i][0]

        kavg = np.mean(bs_kappas)
        havg = np.mean(bs_depths)
        sumhk = np.sum((bs_depths-havg)*(bs_kappas-kavg))
        # sumhk = np.mean((bs_depths-havg)*(bs_kappas-kavg))

        # self.sigmak = np.round(np.std(bs_kappas),2)
        # self.sigmah = np.round(np.std(bs_depths),1)
        self.sigmak = np.std(bs_kappas)
        self.sigmah = np.std(bs_depths)
        # self.correl = 100.0*sumhk/(self.bs_replications-1)/self.sigmak/self.sigmah
        self.correl = np.corrcoef(bs_depths,y=bs_kappas)[0][1]
        return self.sigmak, self.sigmah, self.correl

    def _covariance_ellipse(self):
        """ Computes the covariance ellipse for plotting. """
        x_ell = np.zeros(self.nell)
        y_ell = np.zeros(self.nell)
        t = np.zeros(self.nell)
        # compute tilting
        #corr = self.correl/100.0
        corr = self.correl
        sigh = self.sigmah
        sigk = self.sigmak
        tilt = np.arctan(2.0*corr*sigh*sigk/(sigh*sigh-sigk*sigk))
        tilt = tilt/2.0
        # Compute Semidiameters of ellipse
        p1 = sigh*sigh*sigk*sigk*(1-corr*corr)/(sigk*sigk*np.cos(tilt)*
            np.cos(tilt)-2.0*corr*sigh*sigk*np.sin(tilt)*np.cos(tilt)+sigh*sigh*
            np.sin(tilt)*np.sin(tilt))
        p2 = sigh*sigh*sigk*sigk*(1-corr*corr)/(sigk*sigk*np.sin(tilt)*
            np.sin(tilt)+2.0*corr*sigh*sigk*np.sin(tilt)*np.cos(tilt)+sigh*sigh*
            np.cos(tilt)*np.cos(tilt))
        # Compute the actual 95% confidence ellipse
        nellarr = np.arange(0, self.nell, 1)
        t = nellarr*2*np.pi/self.nell
        xp = np.sqrt(p1)*np.cos(t)
        yp = np.sqrt(p2)*np.sin(t)
        x_ell = self.maxh + xp * np.cos(tilt) - yp*np.sin(tilt)
        y_ell = self.maxk + yp * np.cos(tilt) + xp*np.sin(tilt)
        self.ellipse = (x_ell, y_ell)

    def plot_hkstack(self):
        """
        Generates the HKstack figure.
        """
        cbticks = np.arange(0, 110, 10)
        cmap = plt.cm.get_cmap('viridis')
        levels = np.linspace(0, 100, num=100)
        self.fig = plt.figure(figsize=(11, 8))
        self.gs = gridspec.GridSpec(12, 12)
        ax1 = self.fig.add_subplot(self.gs[:10, :5])
        filled_cntr = ax1.contourf(self.depths, self.kappas, self.stack,
                                   cmap=cmap, levels=levels)
        for a in filled_cntr.collections:
            a.set_edgecolor('face')
        ax1.contour(self.depths, self.kappas, self.stack, colors='w',
                    levels=[70, 75, 80, 85, 90, 95])
        xlim = ax1.get_xlim()
        ylim = ax1.get_ylim()
        if self.bs:
            ax1.plot(self.ellipse[0], self.ellipse[1], 'k-')
            ax1.set_xlim(xlim[0], xlim[1])
            ax1.set_ylim(ylim[0], ylim[1])
            title = '{}    {} {}    {} {} {}   {} {} {}'.format(
                r'$Station:{}$'.format(self.station.replace('_', '\_')),
                r'$V_p = {}$'.format(self.vp),
                r'$\frac{km}{s}$',
                r'$h = {}$'.format(str(self.maxh).strip("[]")),
                r'$\pm$', r'${} km$'.format(np.round(self.sigmah, 1)),
                r'$\kappa = {}$'.format(str(self.maxk).strip('[]')),
                r'$\pm$',
                r'${}$'.format(np.round(self.sigmak, 2)))

        else:
            title = '{}    {} {}    {}    {}'.format(
                r'$Station:{}$'.format(self.station.replace('_', '\_')),
                r'$V_p = {}$'.format(self.vp),
                r'$\frac{km}{s}$',
                r'$h = {}$'.format(str(self.maxh).strip("[]")),
                r'$\kappa = {}$'.format(str(self.maxk).strip('[]')),
                )

        plt.suptitle(title, fontsize=18)
        plt.colorbar(filled_cntr, ticks=cbticks, shrink=0.75)
        ax1.grid(True, alpha=0.5)
        ax1.set_xlabel(r'$Depth (km)$')
        ax1.set_ylabel(r'$\kappa$')
        ax1.set_title('HK Stack')
        return self.fig, self.gs

    def plot_rftn(self):
        """
        Adds up to 30 receiver functions to the hkstack plot.  Marks
        the arrival times of the converted phases on the receiver functions.
        """
        def _plot_settings():
            ax.spines['top'].set_color('none')
            ax.spines['bottom'].set_color('none')
            ax.spines['left'].set_color('none')
            ax.spines['right'].set_color('none')
            ax.get_xaxis().set_ticks([])
            ax.get_yaxis().set_ticks([])
            ax.plot(tr.data, 'k')
            ax.axvline(Ps_samp, color='lightseagreen',
                       linestyle='solid')
            ax.axvline(PpPs_samp, color='lightseagreen',
                       linestyle='dashed')
            ax.axvline(PpSs_samp, color='lightseagreen',
                       linestyle='dotted')

        def _bottom_plot_settings():
            ax.set_xlabel('Time (s)')
            ax.set_xticks(ticks)
            ax.set_xticklabels(ticklabels, minor=False, fontsize=8)
            ax.set_xlim(start_sample, end_sample)
            ax.spines['bottom'].set_color('k')

        def _plot_legend_settings(style, wave):
            ax.axvline(0, color='lightseagreen',
                       linestyle=style)
            ax.set_xlim(-1, 1)
            ax.spines['top'].set_color('none')
            ax.spines['bottom'].set_color('none')
            ax.spines['left'].set_color('none')
            ax.spines['right'].set_color('none')
            ax.get_xaxis().set_ticks([])
            ax.get_yaxis().set_ticks([])
            ax.annotate(wave, xy=(0.2, 0.4), xytext=(0.2, .4), fontsize=10)

        vs = self.maxvs
        for i, tr in enumerate(self.stream):
            print(tr)
            p = tr.stats.sac['user8']
            beg = tr.stats.sac['b']
            delta = tr.stats.sac['delta']
            start_sample = int((self.starttime-beg)/delta)
            end_sample = int((self.endtime-beg)/delta)
            etap = np.sqrt(1/(self.vp**2) - p**2)
            etas = np.sqrt(1/(vs**2) - p**2)
            time_Ps = self.maxh*(etas-etap)
            time_PpPs = self.maxh*(etas+etap)
            time_PpSs = self.maxh*(2*etas)
            Ps_samp = int((time_Ps-beg)/delta)
            PpPs_samp = int((time_PpPs-beg)/delta)
            PpSs_samp = int((time_PpSs-beg)/delta)
            ticksstart = -beg/delta
            ticksend = (30 - beg)/delta
            samp_per_second = (1-beg)/delta - ticksstart
            if self.endtime - self.starttime > 20:
                ticks = np.arange(ticksstart, ticksend, 5*samp_per_second)
                ticks = np.rint(ticks)
            else:
                ticks = np.arange(ticksstart, ticksend, 2*samp_per_second)
                ticks = np.rint(ticks)

            ticklabels = ((ticks*delta) + beg).astype(int)
            ticklabels = [str(x) for x in ticklabels]

            if i < 10:
                ax = self.fig.add_subplot(self.gs[(-i+9), 5:7])
                _plot_settings()
                ax.set_xlim(start_sample, end_sample)
                if -i+9 == 9:
                    _bottom_plot_settings()

            if i >= 10 and i < 20:
                ax = self.fig.add_subplot(self.gs[(-i+19), 7:9])
                _plot_settings()
                ax.set_xlim(start_sample, end_sample)
                if -i+19 == 9:
                    _bottom_plot_settings()

            if i >= 20 and i < 30:
                ax = self.fig.add_subplot(self.gs[(-i+29), 9:11])
                _plot_settings()
                ax.set_xlim(start_sample, end_sample)
                if -i+29 == 9:
                    _bottom_plot_settings()

        print(self.gs.get_subplot_params())
        ax = self.fig.add_subplot(self.gs[9:10, 11:12])
        _plot_legend_settings('solid', 'Ps')
        ax = self.fig.add_subplot(self.gs[8:9, 11:12])
        _plot_legend_settings('dashed', 'PpPs')
        ax = self.fig.add_subplot(self.gs[7:8, 11:12])
        _plot_legend_settings('dotted', 'PpSs')
        plt.savefig(self.plotfile)
        plt.close()
