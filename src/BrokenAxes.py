# see: https://github.com/bendichter/brokenaxes

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
from matplotlib import rcParams
from datetime import timedelta

import numpy as np

__author__ = 'Ben Dichter'


class BrokenAxes:
    def __init__(self, xlims=None, ylims=None, d=.01, tilt=45,
                 subplot_spec=None, fig=None, despine=True,
                 xscale=None, yscale=None, diag_color='k',
                 height_ratios=None, width_ratios=None,
                 *args, **kwargs):
        """Creates a grid of axes that act like a single broken axes
        
        Parameters
        ----------
        xlims, ylims: (optional) None or tuple of tuples, len 2
            Define the ranges over which to plot. If `None`, the axis is left
            unsplit.
        d: (optional) double
            Length of diagonal split mark used to indicate broken axes
        tilt: (optional) double
            Angle of diagonal split mark
        subplot_spec: (optional) None or Gridspec.subplot_spec
            Defines a subplot
        fig: (optional) None or Figure
            If no figure is defined, `plt.gcf()` is used
        despine: (optional) bool
            Get rid of inner spines. Default: True
        wspace, hspace: (optional) bool
            Change the size of the horizontal or vertical gaps
        xscale, yscale: (optional) None | str
            None: linear axis (default), 'log': log axis
        diag_color: (optional)
            color of diagonal lines
        {width, height}_ratios: (optional) | list of int
            The width/height ratios of the axes, passed to gridspec.GridSpec.
            By default, adapt the axes for a 1:1 scale given the ylims/xlims.
        hspace: float
            Height space between axes (NOTE: not horizontal space)
        wspace: float
            Widgth space between axes
        args, kwargs: (optional)
            Passed to gridspec.GridSpec
            
        Notes
        -----
        The broken axes effect is achieved by creating a number of smaller axes
        and setting their position and data ranges. A "big_ax" is used for
        methods that need the position of the entire broken axes object, e.g.
        `set_xlabel`.
        """

        self.diag_color = diag_color
        self.despine = despine
        self.d = d
        self.tilt = tilt

        if fig is None:
            self.fig = plt.gcf()
        else:
            self.fig = fig

        if width_ratios is None:
            if xlims:
                # Check if the user has asked for a log scale on x axis
                if xscale == 'log':
                    width_ratios = [np.log(i[1]) - np.log(i[0]) for i in xlims]
                else:
                    width_ratios = [i[1] - i[0] for i in xlims]
            else:
                width_ratios = [1]

            # handle datetime xlims
            if type(width_ratios[0]) == timedelta:
                width_ratios = [tt.total_seconds() for tt in width_ratios]

        if height_ratios is None:
            if ylims:
                # Check if the user has asked for a log scale on y axis
                if yscale == 'log':
                    height_ratios = [np.log(i[1]) - np.log(i[0])
                                     for i in ylims[::-1]]
                else:
                    height_ratios = [i[1] - i[0] for i in ylims[::-1]]
            else:
                height_ratios = [1]

            # handle datetime ylims
            if type(height_ratios[0]) == timedelta:
                width_ratios = [tt.total_seconds() for tt in height_ratios]

        ncols, nrows = len(width_ratios), len(height_ratios)

        kwargs.update(ncols=ncols, nrows=nrows, height_ratios=height_ratios,
                      width_ratios=width_ratios)

        gs = gridspec.GridSpec(*args, **kwargs)
        self.big_ax = self.fig.gca()

        self.old_lines = self.fig.axes[0].get_lines()

        xlabel = self.big_ax.get_xlabel()
        ylabel = self.big_ax.get_ylabel()
        xlabelsize = self.big_ax.xaxis.label.get_size()
        ticksize = 18
        yticks = self.big_ax.get_yticks()
        ymin, ymax = map(float, self.big_ax.get_ylim())

        if self.big_ax.get_legend() is not None:
            old_legend = self.big_ax.get_legend()
            leg_draggable = old_legend._draggable is not None
            try:
                # dependent on matplotlib version (>= 3.6.0 _ncols else _ncol)
                leg_ncol = old_legend._ncol
            except AttributeError:
                leg_ncol = old_legend._ncols
            leg_fontsize = int(old_legend._fontsize)
            leg_frameon = old_legend.get_frame_on()
            leg_shadow = old_legend.shadow
            leg_fancybox = type(old_legend.legendPatch.get_boxstyle())
            leg_framealpha = old_legend.get_frame().get_alpha()
            leg_picker = old_legend.get_picker()
        else:
            leg_draggable = False
            leg_ncol = 1
            leg_fontsize = 15
            leg_frameon = True
            leg_shadow = True
            leg_fancybox = True
            leg_framealpha = 0.5
            leg_picker = 5

        self.big_ax.clear()

        [sp.set_visible(False) for sp in self.big_ax.spines.values()]
        self.big_ax.set_xticks([])
        self.big_ax.set_yticks([])
        self.big_ax.set_xlabel(xlabel)
        self.big_ax.set_ylabel(ylabel)
        self.big_ax.xaxis.label.set_size(xlabelsize)
        self.big_ax.yaxis.label.set_size(xlabelsize)
        self.big_ax.xaxis.labelpad = 30
        self.big_ax.yaxis.labelpad = 45
        self.big_ax.patch.set_facecolor('none')

        self.axs = []
        for igs in gs:
            ax = plt.Subplot(self.fig, igs)
            ax.xaxis.set_tick_params(labelsize=ticksize)
            ax.yaxis.set_tick_params(labelsize=ticksize)
            self.fig.add_subplot(ax)
            self.axs.append(ax)

        self.fig.subplots_adjust(wspace=0.075)

        # get last axs row and first col
        self.last_row = []
        self.first_col = []
        for ax in self.axs:
            if ax.get_subplotspec().is_last_row():
                self.last_row.append(ax)
            if ax.get_subplotspec().is_first_col():
                self.first_col.append(ax)

        # Set common x/y lim for ax in the same col/row
        # and share x and y between them
        for i, ax in enumerate(self.axs):
            if ylims is not None:
                ax.set_ylim(ylims[::-1][i // ncols])
                ax.get_shared_y_axes().join(ax, self.first_col[i // ncols])
            if xlims is not None:
                ax.set_xlim(xlims[i % ncols])
                ax.get_shared_x_axes().join(ax, self.last_row[i % ncols])
                ax.set_yticks(yticks)
                ax.set_ylim(ymin, ymax)
        self.standardize_ticks()
        if d:
            self.draw_diags()
        if despine:
            self.set_spines()
        self.new_lines = []
        for ax in self.axs:
            self.new_lines.append([])
            for line in self.old_lines:
                new_line, = ax.plot(line.get_xdata(), line.get_ydata(), lw=line.get_lw(), ls=line.get_ls(),
                                    c=line.get_c(), label=line.get_label())
                new_line.set_marker(line.get_marker())
                new_line.set_markersize(line.get_markersize())
                new_line.set_markerfacecolor(line.get_markerfacecolor())
                new_line.set_markeredgecolor(line.get_markeredgecolor())
                self.new_lines[-1].append(new_line)

        self.big_ax.legend(
            self.axs[0].get_legend_handles_labels(),
            ncol=leg_ncol,
            fontsize=float(leg_fontsize),
            frameon=leg_frameon,
            shadow=leg_shadow,
            framealpha=leg_framealpha,
            fancybox=leg_fancybox
        )

        # set order of axes
        len_axs = len(self.axs)
        for l in range(len_axs):
            self.axs[l].set_zorder(l)
        self.big_ax.set_zorder(l + 1)

    @staticmethod
    def draw_diag(ax, xpos, xlen, ypos, ylen, **kwargs):
        return ax.plot((xpos - xlen, xpos + xlen), (ypos - ylen, ypos + ylen), label='_nolegend_',
                       **kwargs)

    def draw_diags(self):
        """
        
        Parameters
        ----------
        d: float
            Length of diagonal split mark used to indicate broken axes
        tilt: float
            Angle of diagonal split mark
        """
        size = self.fig.get_size_inches()
        ylen = self.d * np.sin(self.tilt * np.pi / 180) * size[0] / size[1]
        xlen = self.d * np.cos(self.tilt * np.pi / 180)
        d_kwargs = dict(transform=self.fig.transFigure, color=self.diag_color,
                        clip_on=False, in_layout=True, lw=rcParams['axes.linewidth'])

        ds = []
        for ax in self.axs:
            bounds = ax.get_position().bounds

            if ax.get_subplotspec().is_last_row():
                ypos = bounds[1]
                if not ax.get_subplotspec().is_last_col():
                    xpos = bounds[0] + bounds[2]
                    ds += self.draw_diag(ax, xpos, xlen, ypos, ylen,
                                         **d_kwargs)
                if not ax.get_subplotspec().is_first_col():
                    xpos = bounds[0]
                    ds += self.draw_diag(ax, xpos, xlen, ypos, ylen,
                                         **d_kwargs)

            if ax.get_subplotspec().is_first_col():
                xpos = bounds[0]
                if not ax.get_subplotspec().is_first_row():
                    ypos = bounds[1] + bounds[3]
                    ds += self.draw_diag(ax, xpos, xlen, ypos, ylen, **d_kwargs)
                if not ax.get_subplotspec().is_last_row():
                    ypos = bounds[1]
                    ds += self.draw_diag(ax, xpos, xlen, ypos, ylen, **d_kwargs)

            if not self.despine:
                if ax.get_subplotspec().is_first_row():
                    ypos = bounds[1] + bounds[3]
                    if not ax.get_subplotspec().is_last_col():
                        xpos = bounds[0] + bounds[2]
                        ds += self.draw_diag(ax, xpos, xlen, ypos, ylen,
                                             **d_kwargs)
                    if not ax.get_subplotspec().is_first_col():
                        xpos = bounds[0]
                        ds += self.draw_diag(ax, xpos, xlen, ypos, ylen,
                                             **d_kwargs)

                if ax.get_subplotspec().is_last_col():
                    xpos = bounds[0] + bounds[2]
                    if not ax.get_subplotspec().is_first_row():
                        ypos = bounds[1] + bounds[3]
                        ds += self.draw_diag(ax, xpos, xlen, ypos, ylen,
                                             **d_kwargs)
                    if not ax.get_subplotspec().is_last_row():
                        ypos = bounds[1]
                        ds += self.draw_diag(ax, xpos, xlen, ypos, ylen,
                                             **d_kwargs)
        self.diag_handles = ds

    def set_spines(self):
        """Removes the spines of internal axes that are not boarder spines.
        """
        for ax in self.axs:
            ax.xaxis.tick_bottom()
            ax.yaxis.tick_left()
            if not ax.get_subplotspec().is_last_row():
                ax.spines['bottom'].set_visible(False)
                plt.setp(ax.xaxis.get_minorticklabels(), visible=False)
                plt.setp(ax.xaxis.get_minorticklines(), visible=False)
                plt.setp(ax.xaxis.get_majorticklabels(), visible=False)
                plt.setp(ax.xaxis.get_majorticklines(), visible=False)
            if self.despine or not ax.get_subplotspec().is_first_row():
                ax.spines['top'].set_visible(True)
            if not ax.get_subplotspec().is_first_col():
                ax.spines['left'].set_visible(False)
                plt.setp(ax.yaxis.get_minorticklabels(), visible=False)
                plt.setp(ax.yaxis.get_minorticklines(), visible=False)
                plt.setp(ax.yaxis.get_majorticklabels(), visible=False)
                plt.setp(ax.yaxis.get_majorticklines(), visible=False)
            if not ax.get_subplotspec().is_last_col():
                ax.spines['right'].set_visible(False)

    def standardize_ticks(self, xbase=None, ybase=None):
        """Make all the internal axes share tick bases
        
        Parameters
        ----------
        xbase, ybase: (optional) None or float
            If `xbase` or `ybase` is a float, manually set all tick locators to
            this base. Otherwise, use the largest base across internal subplots
            for that axis.
        """
        if xbase is None:
            if self.axs[0].xaxis.get_scale() == 'log':
                xbase = max(ax.xaxis.get_ticklocs()[1] /
                            ax.xaxis.get_ticklocs()[0]
                            for ax in self.axs if ax.get_subplotspec().is_last_row())
            else:
                xbase = max(ax.xaxis.get_ticklocs()[1] -
                            ax.xaxis.get_ticklocs()[0]
                            for ax in self.axs if ax.get_subplotspec().is_last_row())
        if ybase is None:
            if not self.axs[0].get_yticks().any():
                pass
            elif self.axs[0].yaxis.get_scale() == 'log':
                ybase = max(ax.yaxis.get_ticklocs()[1] /
                            ax.yaxis.get_ticklocs()[0]
                            for ax in self.axs if ax.get_subplotspec().is_first_col())
            else:
                ybase = max(ax.yaxis.get_ticklocs()[1] -
                            ax.yaxis.get_ticklocs()[0]
                            for ax in self.axs if ax.get_subplotspec().is_first_col())

        for ax in self.axs:
            if not self.axs[0].get_yticks().any():
                pass
            elif ax.get_subplotspec().is_first_col():
                if ax.yaxis.get_scale() == 'log':
                    ax.yaxis.set_major_locator(ticker.LogLocator(ybase))
                else:
                    ax.yaxis.set_major_locator(ticker.MultipleLocator(ybase))
            if ax.get_subplotspec().is_last_row():
                if ax.xaxis.get_scale() == 'log':
                    ax.xaxis.set_major_locator(ticker.LogLocator(xbase))
                else:
                    ax.xaxis.set_major_locator(ticker.MultipleLocator(xbase))

    def __getattr__(self, method):
        """Catch all methods that are not defined and pass to internal axes
         (e.g. plot, errorbar, etc.).
        """
        return CallCurator(method, self)

    def subax_call(self, method, args, kwargs):
        """Apply method call to all internal axes. Called by CallCurator.
        """
        result = []
        for ax in self.axs:
            if ax.xaxis.get_scale() == 'log':
                ax.xaxis.set_major_locator(ticker.LogLocator())
            else:
                ax.xaxis.set_major_locator(ticker.AutoLocator())
            if ax.yaxis.get_scale() == 'log':
                ax.yaxis.set_major_locator(ticker.LogLocator())
            else:
                ax.yaxis.set_major_locator(ticker.AutoLocator())
            result.append(getattr(ax, method)(*args, **kwargs))

        self.standardize_ticks()
        self.set_spines()

        return result

    def set_xlabel(self, label, labelpad=100, **kwargs):
        return self.big_ax.set_xlabel(label, labelpad=labelpad, **kwargs)

    def set_ylabel(self, label, labelpad=100, **kwargs):
        return self.big_ax.set_ylabel(label, labelpad=labelpad, **kwargs)

    # def set_xlim(self, *args, **kwargs):
    #     return self.big_ax.set_xlim(self, *args, **kwargs)

    # def set_ylim(self, *args, **kwargs):
    #     return self.big_ax.set_ylim(self, *args, **kwargs)

    def set_title(self, *args, **kwargs):
        return self.big_ax.set_title(*args, **kwargs)

    def get_figure(self, *args, **kwargs):
        return self.big_ax.get_figure()

    def legend(self, *args, **kwargs):
        h, l = self.axs[1].get_legend_handles_labels()
        return self.big_ax.legend(h, l, *args, **kwargs)

    def axis(self, *args, **kwargs):
        [ax.axis(*args, **kwargs) for ax in self.axs]


class CallCurator:
    """Used by BrokenAxes.__getattr__ to pass methods to internal axes."""

    def __init__(self, method, broken_axes):
        self.method = method
        self.broken_axes = broken_axes

    def __call__(self, *args, **kwargs):
        return self.broken_axes.subax_call(self.method, args, kwargs)


def brokenaxes(*args, **kwargs):
    """Convenience method for `BrokenAxes` class.
    
    Parameters
    ----------
    args, kwargs: passed to `BrokenAxes()`
    
    Returns
    -------
    out: `BrokenAxes`
    """
    return BrokenAxes(*args, **kwargs)
