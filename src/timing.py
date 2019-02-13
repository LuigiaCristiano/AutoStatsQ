from pyrocko import pile, trace, util
import numpy as num
import math
import matplotlib.pyplot as plt
import matplotlib
from pyrocko.guts import Object, Dict, String, Float, Int


def test(input):
    print(input)


matplotlib.rc('xtick', labelsize=20)
matplotlib.rc('ytick', labelsize=20)

def ccs_allstats_one_event(i_ev, ev, stat_list, all_stations,
                           datapath, syndatapath,
                           out_dir, bp, arrT_array, cc_thresh,
                           debug_mode=False):
    '''
    for one event: call cc_single_stat_single_event for each station,
    collect optimal time shifts
    return list with timeshift, fixed order of stations!
    '''

    ev_t_str = util.time_to_str(ev.time).replace(' ', '_')
    # load data and syndata
    p_obs = pile.make_pile(datapath+ev_t_str, show_progress=False)
    p_syn = pile.make_pile(syndatapath+ev_t_str, show_progress=False)

    tshift_list = []

    if p_obs and p_syn:
        for i_st, st in enumerate(stat_list):
            try:
                s = st.station
                n = st.network
                l = 'not_set'
            except:
                n, s, l, c = st

            i_ast = [i_ast for i_ast, ast in enumerate(all_stations)
                     if ast.network == n and ast.station == s]
            if len(i_ast) >= 1:
                ii_ast = i_ast[0]
                tmin = arrT_array[i_ev, ii_ast]-30

            elif len(i_ast) == 0:
                print('station %s.%s not in all station list' % (n, s))
                continue

            if l != 'not_set':
                tr_obs = p_obs.all(
                            trace_selector=lambda tr: tr.network == n and
                            tr.station == s and
                            tr.location == l and
                            tr.channel == 'Z',
                            tmin=tmin,
                            tmax=tmin+300,
                            want_incomplete=True)
            else:
                tr_obs = p_obs.all(
                                trace_selector=lambda tr: tr.network == n and
                                tr.station == s and
                                tr.channel == 'Z',
                                tmin=tmin,
                                tmax=tmin+300,
                                want_incomplete=True)
            tr_syn = p_syn.all(
                            trace_selector=lambda tr: tr.network == n and
                            tr.station == s and
                            tr.channel == 'Z',
                            tmin=tmin,
                            tmax=tmin+300,
                            want_incomplete=True)

            if len(tr_obs) != 0 and len(tr_syn) != 0:
                tr_syn = tr_syn[0]
                tr_obs = tr_obs[0]
                tr_obs.bandpass(bp[0], bp[1], bp[2])
                tr_syn.bandpass(bp[0], bp[1], bp[2])

                c = trace.correlate(tr_syn, tr_obs, mode='same',
                                    normalization='normal')
                t, coef = c.max()

                if debug_mode is True:
                    print(t, coef)
                    trace.snuffle([tr_syn, tr_obs])
                    trace.snuffle([c])

                if coef > cc_thresh:
                    tshift_list.append(t)
                else:
                    tshift_list.append(num.nan)
            else:
                tshift_list.append(num.nan)

    return tshift_list


def correct_for_med_tshifts(tshift_array):
    '''
    get median time shift of each event
    subtract median of each single value
    return corrected array
    '''
    tshift_medians = num.nanmedian(tshift_array, axis=0)
    tshift_corr = num.empty((tshift_array.shape))

    for i_ev in range(tshift_medians.shape[0]):
        for i_st in range(tshift_array.shape[0]):
            v = tshift_array[i_st, i_ev]
            if not num.isnan(v):
                tshift_corr[i_st, i_ev] = v - tshift_medians[i_ev]
            else:
                tshift_corr[i_st, i_ev] = v

    return tshift_corr


def plot_matrix(tshifts, tshifts_cor, stations, dir_time):

    fig, ax = plt.subplots(nrows=2, figsize=(10, 20))
    min_col = num.min([num.nanmin(tshifts), num.nanmin(tshifts_cor)])
    max_col = num.max([num.nanmax(tshifts), num.nanmax(tshifts_cor)])
    absmax = 20#num.max([abs(min_col), abs(max_col)])
    a = ax[0].imshow(tshifts, vmin=-absmax,
                     vmax=+absmax, interpolation='nearest')
    ax[0].set_title('Not corrected')
    ax[0].set_xlabel('Events')
    ax[0].set_ylabel('Stations')
    try:
        stats = ['%s.%s' % (st.network, st.station) for st in stations]
    except AttributeError:
        stats = ['%s.%s.%s' % (st[0], st[1], st[2]) for st in stations]
    ax[0].set_yticks(num.arange(len(stats)))
    ax[0].set_yticklabels(stats)
    cbar = plt.colorbar(a, ax=ax[0], extend='both')
    cbar.set_label('Timing error [s]', rotation=90)
    b = ax[1].imshow(tshifts_cor, vmin=-absmax,
                     vmax=absmax, interpolation='nearest')
    ax[1].set_title('Corrected for median of event.')
    ax[1].set_xlabel('Events')
    ax[1].set_ylabel('Stations')
    ax[1].set_yticks(num.arange(len(stats)))
    ax[1].set_yticklabels(stats)
    cbar = plt.colorbar(b, ax=ax[1], extend='both')
    cbar.set_label('Timing error [s]', rotation=90)
    plt.tight_layout()
    fig.savefig(dir_time + 'timing_arrays.png')
    plt.close()


def plot_tshifts(tshifts_cor, means, stdevs, outfile, stations):
    # scatter plot: for each station all offsets
    n_per_row = 20
    n_plotrows = math.ceil(len(stations)/n_per_row)

    try:
        stations_sorted = sorted(stations,
                                 key=lambda k: '%s.%s' % (k.network, k.station))
        indices_st = [i for (i, j) in sorted(enumerate(stations),
                      key=lambda k: '%s.%s' % (k[1].network, k[1].station))]

        # print([(s.network, s.station) for s in stations])
        # print([(s.network, s.station) for s in stations_sorted])
        # print(indices_st)

    except:
        stations_sorted = sorted(stations,
                                 key=lambda k: '%s.%s.%s' % (k[0], k[1], k[2]))
        indices_st = [i for (i, j) in sorted(enumerate(stations),
                      key=lambda k: '%s.%s.%s' % (k[1][0], k[1][1], k[1][2]))]

        # print([(s[0], s[1], s[2]) for s in stations])
        # print([(s[0], s[1], s[2]) for s in stations_sorted])
        # print(indices_st)
    cnt=0
    fig, ax = plt.subplots(nrows=n_plotrows, figsize=(30, n_plotrows*10),
                           squeeze=False)
    for i_row in range(n_plotrows):
        ax[i_row, 0].set_ylim(num.nanmin(tshifts_cor), num.nanmax(tshifts_cor))
        ax[i_row, 0].set_xlim(-1, n_per_row)
        i_start = i_row*n_per_row
        i_stop = i_start + n_per_row
        for i_st, st in enumerate(stations_sorted[i_start:i_stop]):
            i_st_all = indices_st[i_st+i_row*(n_per_row)]
            yval = tshifts_cor[i_st_all, :]
            xval = [i_st for val in yval]
            ax[i_row, 0].scatter(xval, yval, marker='o', s=20)
            ax[i_row, 0].plot(i_st, means[i_st_all], 'ro', markersize=20)

        try:
            stats = ['%s.%s' % (st.network, st.station)
                     for st in stations_sorted[i_row+(i_row*(n_per_row-1)):(n_per_row-1)*(i_row+1)+1]]
        except AttributeError:
            stats = ['%s.%s.%s' % (st[0], st[1], st[2])
                     for st in stations_sorted[i_row+(i_row*(n_per_row-1)):(n_per_row-1)*(i_row+1)+1]]
            # print([(i,j) for (i,j) in enumerate(stats)])

        ax[i_row, 0].set_xticks(num.arange(len(stats)))
        ax[i_row, 0].set_xticklabels(stats, rotation=60, fontsize=20)
        ax[i_row, 0].set_ylabel('Time shift [s]', fontsize=20)

    plt.tight_layout()
    fig.savefig(outfile)
    plt.close()


class results_dict(Object):
    medians = Dict.T(String.T(), Float.T())
    means = Dict.T(String.T(), Float.T())
    st_devs = Dict.T(String.T(), Float.T())
    n_ev = Dict.T(String.T(), Int.T())


def save_mms(medians, means, stdevs, stations, out_dir, n_evs):

    medians = list(num.round(medians, decimals=1))
    means = list(num.round(means, decimals=1))
    stdevs = list(num.round(stdevs, decimals=1))

    meds = dict(zip(['%s.%s.%s' % (s[0], s[1], s[2]) for s in stations], medians))
    ms = dict(zip(['%s.%s.%s' % (s[0], s[1], s[2]) for s in stations], means))
    sts = dict(zip(['%s.%s.%s' % (s[0], s[1], s[2]) for s in stations], stdevs))
    ns = dict(zip(['%s.%s.%s' % (s[0], s[1], s[2]) for s in stations], n_evs))

    results_ = results_dict(medians=meds, means=ms, st_devs=sts, n_ev=ns)

    results_.regularize()
    results_.validate()
    results_.dump(filename='%s/timings.yaml' % out_dir)
