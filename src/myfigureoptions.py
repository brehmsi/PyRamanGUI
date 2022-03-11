#!/usr/bin/python
# -*- coding: <encoding name> -*-
# https://stackoverflow.com/questions/53099295/matplotlib-navigationtoolbar-advanced-figure-options
# https://github.com/matplotlib/matplotlib/blob/master/lib/matplotlib/backends/qt_editor/figureoptions.py
# Copyright at 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# see the mpl licenses directory for a copy of the license
# Modified to add a title fontsize

"""Module that provides a GUI-based editor for matplotlib's figure options."""

import os.path
import re
import numpy as np
import math
from BrokenAxes import brokenaxes

import matplotlib
from matplotlib import cm, colors as mcolors, markers, image as mimage
import matplotlib.backends.qt_editor._formlayout as formlayout
from matplotlib.backends import qt_compat
from PyQt5 import QtGui, QtWidgets


def get_icon(name):
    basedir = os.path.join(matplotlib.rcParams['datapath'], 'images')
    return QtGui.QIcon(os.path.join(basedir, name))


LINESTYLES = {'-': 'Solid',
              '--': 'Dashed',
              '-.': 'DashDot',
              ':': 'Dotted',
              'None': 'None',
              }

DRAWSTYLES = {
    'default': 'Default',
    'steps-pre': 'Steps (Pre)', 'steps': 'Steps (Pre)',
    'steps-mid': 'Steps (Mid)',
    'steps-post': 'Steps (Post)'}

MARKERS = markers.MarkerStyle.markers


def figure_edit(axes, parent=None):
    """Edit matplotlib figure options"""
    sep = (None, None)  # separator
    # check if more than one axis exists => broken axis

    if len(axes) == 1:
        ax, = axes
        ax1 = ax
        axl = ax
        figure_edit.axis_is_broken = False
    else:
        ax = axes[0]         # main axis
        ax1 = axes[1]        # axis of first segment
        axl = axes[-1]       # axis of last segment
        figure_edit.axis_is_broken = True

    # Get / General
    # Cast to builtin floats as they have nicer reprs.
    xmin, xmax = map(float, ax1.get_xlim())
    ymin, ymax = map(float, ax1.get_ylim())
    xticks = ax1.get_xticks()
    yticks = ax1.get_yticks()

    if xticks != []:
        xtickspace = xticks[1] - xticks[0]
    else:
        xtickspace = None
    if yticks != []:
        ytickspace = yticks[1] - yticks[0]
    else:
        ytickspace = None

    if 'labelsize' in ax1.xaxis._major_tick_kw:
        _ticksize = int(ax1.xaxis._major_tick_kw['labelsize'])
    else:
        _ticksize = 15

    if figure_edit.axis_is_broken:
        axis_options = [
            (None, "<b>X-Axis</b>"),
            ('Scale', [ax1.get_xscale(), 'linear', 'log', 'logit']),
            # ('Lower Limit', ax1.get_xlim()[0]),
            # ('Upper Limit', ax1.get_xlim()[1]),
            ('Tick Step Size', xtickspace),
            sep,
            (None, "<b>Y-Axis</b>"),
            ('Scale', [ax1.get_yscale(), 'linear', 'log', 'logit']),
            ('Lower Limit', ax1.get_ylim()[0]),
            ('Upper Limit', ax1.get_ylim()[1]),
            ('Tick Step Size', ytickspace)
        ]

        for idx, itm in enumerate(axes[1:]):
            axis_options.insert(3 + idx * 3, (None, "%i. Segment" % (idx + 1)))
            axis_options.insert(4 + idx * 3, ('Lower Limit', itm.get_xlim()[0]))
            axis_options.insert(5 + idx * 3, ('Upper Limit', itm.get_xlim()[1]))
    else:
        axis_options = [(None, "<b>X-Axis</b>"),
                        ('Scale', [ax.get_xscale(), 'linear', 'log', 'logit']),
                        ('Lower Limit', ax.get_xlim()[0]),
                        ('Upper Limit', ax.get_xlim()[1]),
                        ('Tick Step Size', xtickspace),
                        sep,
                        (None, "<b>Y-Axis</b>"),
                        ('Scale', [ax.get_yscale(), 'linear', 'log', 'logit']),
                        ('Lower Limit', ax.get_ylim()[0]),
                        ('Upper Limit', ax.get_ylim()[1]),
                        ('Tick Step Size', ytickspace),
                        sep,
                        (None, "<b>Axis Break</b>"),
                        ('x-Axis Break', False),
                        ('start', 0.0),
                        ('end', 0.0),
                        ('y-Axis Break', False),
                        ('start', 0.0),
                        ('end', 0.0)]

    general = [(None, "<b>Figure Title</b>"),
               ('Title', ax.get_title()),
               ('Font Size', int(ax.title.get_fontsize())),
               sep,
               (None, "<b>Axes settings</b>"),
               ('Label Size', int(ax.xaxis.label.get_fontsize())),
               ('Tick Size', _ticksize),
               #('Show grid', ax.xaxis._gridOnMajor),
               ('Show grid', ax.xaxis._major_tick_kw['gridOn']),
               sep,
               (None, "<b>X-Axis</b>"),
               ('Label', ax.get_xlabel()),
               ('Label Pad', ax.xaxis.labelpad),
               sep,
               (None, "<b>Y-Axis</b>"),
               ('Label', ax.get_ylabel()),
               ('Label Pad', ax.yaxis.labelpad)
               ]

    if ax.legend_ is not None:
        old_legend = ax.get_legend()
        _visible = old_legend._visible
        _draggable = old_legend._draggable is not None
        _ncol = old_legend._ncol
        _fontsize = int(old_legend._fontsize)
        _frameon = old_legend.get_frame_on()
        _shadow = old_legend.shadow
        _fancybox = type(old_legend.legendPatch.get_boxstyle()) == matplotlib.patches.BoxStyle.Round
        _framealpha = old_legend.get_frame().get_alpha()
        _picker = 5
    else:
        _visible = True
        _draggable = False
        _ncol = 1
        _fontsize = 15
        _frameon = True
        _shadow = True
        _fancybox = True
        _framealpha = 0.5
        _picker = 5

    legend = [('Visible', _visible),
              ('Draggable', _draggable),
              ('Columns', _ncol),
              ('Font Size', _fontsize),
              ('Frame', _frameon),
              ('Shadow', _shadow),
              ('FancyBox', _fancybox),
              ('Alpha', _framealpha),
              ('Picker', _picker)
              ]

    # Save the unit data
    xconverter = ax.xaxis.converter
    yconverter = ax.yaxis.converter
    xunits = ax.xaxis.get_units()
    yunits = ax.yaxis.get_units()

    # Sorting for default labels (_lineXXX, _imageXXX).
    def cmp_key(label):
        match = re.match(r"(_line|_image)(\d+)", label)
        if match:
            return match.group(1), int(match.group(2))
        else:
            return label, 0

    # Get / Curves
    linedict = {}
    for a in axes:
        for line in a.get_lines():
            label = line.get_label()
            if '_nolegend_' in label:
                continue
            else:
                pass
            if label in linedict:
                linedict[label].append(line)
            else:
                linedict[label] = [line]
    curves = []

    errorbar_dict = {}
    for container in ax1.containers:
        if type(container) == matplotlib.container.ErrorbarContainer:
            label = container.get_label()
            if label is not None:
                name = label.split('_Hidden errorbar ', 1)[1]
            else:
                name = 'errorbar'
            errorbar_dict[name] = container
    errorbars = []

    fill_dict = {}
    for col in ax.collections:
        if type(col) == matplotlib.collections.PolyCollection:
            label = col.get_label()
            if label is not None:
                try:
                    name = label.split('_Hidden Fill ', 1)[1]
                except IndexError:
                    name = label
            else:
                name = 'Fill'
            fill_dict[name] = col
    fills = []

    def prepare_data(d, init):
        """Prepare entry for FormLayout.

        `d` is a mapping of shorthands to style names (a single style may
        have multiple shorthands, in particular the shorthands `None`,
        `"None"`, `"none"` and `""` are synonyms); `init` is one shorthand
        of the initial style.

        This function returns an list suitable for initializing a
        FormLayout combobox, namely `[initial_name, (shorthand,
        style_name), (shorthand, style_name), ...]`.
        """
        if init not in d:
            d = {**d, init: str(init)}
        # Drop duplicate shorthands from dict (by overwriting them during
        # the dict comprehension).
        name2short = {name: short for short, name in d.items()}
        # Convert back to {shorthand: name}.
        short2name = {short: name for name, short in name2short.items()}
        # Find the kept shorthand for the style specified by init.
        canonical_init = name2short[d[init]]
        # Sort by representation and prepend the initial value.
        return ([canonical_init] +
                sorted(short2name.items(),
                       key=lambda short_and_name: short_and_name[1]))

    curvelabels = sorted(linedict, key=cmp_key)
    for label in curvelabels:
        line = linedict[label][0]
        color = mcolors.to_hex(
            mcolors.to_rgba(line.get_color(), line.get_alpha()),
            keep_alpha=True)
        ec = mcolors.to_hex(
            mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
            keep_alpha=True)
        fc = mcolors.to_hex(
            mcolors.to_rgba(line.get_markerfacecolor(), line.get_alpha()),
            keep_alpha=True)
        curvedata = [
            ('Label', label),
            sep,
            (None, '<b>Line</b>'),
            ('Line style', prepare_data(LINESTYLES, line.get_linestyle())),
            ('Draw style', prepare_data(DRAWSTYLES, line.get_drawstyle())),
            ('Width', line.get_linewidth()),
            ('Color (RGBA)', color),
            ('Fill Area under curve', False),
            sep,
            (None, '<b>Marker</b>'),
            ('Style', prepare_data(MARKERS, line.get_marker())),
            ('Size', line.get_markersize()),
            ('Face color (RGBA)', fc),
            ('Edge color (RGBA)', ec),
            sep,
            sep,
            ('Remove Line', False)]
        curves.append([curvedata, label, ""])
    # Is there a curve displayed?
    has_curve = bool(curves)

    # Errorbar
    errorbar_labels = sorted(errorbar_dict, key=cmp_key)
    for label in errorbar_labels:
        plotline, caplines, barlinecols = errorbar_dict[label]
        ec = mcolors.to_hex(
            mcolors.to_rgba(caplines[0].get_markerfacecolor(), barlinecols[0].get_alpha()),
            keep_alpha=True)
        errorbar_data = [
            ('Cap Size', caplines[0].get_markersize()),
            ('Line Width', caplines[0].get_markeredgewidth()),
            ('Edge color (RGBA)', ec)]
        errorbars.append([errorbar_data, label, ""])
    # Is there a errorbar capline displayed?
    has_errorbar = bool(errorbars)

    # Fill under curves
    fill_labels = sorted(fill_dict, key=cmp_key)
    for label in fill_labels:
        fill = fill_dict[label]
        fill_color = mcolors.to_hex(
            fill.get_facecolor()[0],
            keep_alpha=True)
        fill_data = [
            ('Color', fill_color),
            sep,
            sep,
            ('Remove Fill', False)]
        fills.append([fill_data, label, ""])
    has_fills = bool(fills)

    # Get / Images
    imagedict = {}
    for image in ax.get_images():
        label = image.get_label()
        if '_nolegend_' in label:
            continue
        imagedict[label] = image
    imagelabels = sorted(imagedict, key=cmp_key)
    images = []
    cmaps = [(cmap, name) for name, cmap in sorted(cm.cmap_d.items())]
    for label in imagelabels:
        image = imagedict[label]
        cmap = image.get_cmap()
        if cmap not in cm.cmap_d.values():
            cmaps = [(cmap, cmap.name)] + cmaps
        low, high = image.get_clim()
        imagedata = [
            ('Label', label),
            ('Colormap', [cmap.name] + cmaps),
            ('Min. value', low),
            ('Max. value', high),
            ('Interpolation',
             [image.get_interpolation()]
             + [(name, name) for name in sorted(mimage.interpolations_names)])]
        images.append([imagedata, label, ""])
    # Is there an image displayed?
    has_image = bool(images)

    datalist = [(general, "General", ""), (axis_options, "Axis", ""), (legend, "Legend", "")]
    if curves:
        datalist.append((curves, "Curves", ""))
    if images:
        datalist.append((images, "Images", ""))
    if errorbars:
        datalist.append((errorbars, "Errorbar", ""))
    if fills:
        datalist.append((fills, "Fill under curves", ""))

    def apply_callback(data):
        """This function will be called to apply changes"""

        figure = ax.get_figure()

        general = data.pop(0)
        axis_options = data.pop(0)
        legend = data.pop(0)
        curves = data.pop(0) if has_curve else []
        images = data.pop(0) if has_image else []
        errorbars = data.pop(0) if has_errorbar else []
        fills = data.pop(0) if has_fills else []
        if data:
            raise ValueError("Unexpected field")

        # Set / General
        (title, titlesize, labelsize, ticksize, grid,
         xlabel, xlabelpad, ylabel, ylabelpad) = general

        ax.set_title(title)
        ax.title.set_fontsize(titlesize)

        ax.set_xlabel(xlabel)
        ax.xaxis.labelpad = xlabelpad
        ax.set_ylabel(ylabel)
        ax.yaxis.labelpad = ylabelpad
        ax.xaxis.label.set_size(labelsize)
        ax.yaxis.label.set_size(labelsize)

        if figure_edit.axis_is_broken is False:
            (xscale, xlim_left, xlim_right, xtickspace, yscale, ylim_left, ylim_right, ytickspace,
             xbreak, xbreak_start, xbreak_end, ybreak, ybreak_start, ybreak_end) = axis_options
            if ax.get_xscale() != xscale:
                ax.set_xscale(xscale)
            if ax.get_yscale() != yscale:
                ax.set_yscale(yscale)

            if xtickspace == 0:
                axes.xaxis.set_ticks([])
            elif xtickspace is not None:
                xtick_space_start = math.ceil(xlim_left / xtickspace) * xtickspace
                ax.xaxis.set_ticks(np.arange(xtick_space_start, xlim_right, xtickspace))
            ax.set_xlim(xlim_left, xlim_right)

            ax.xaxis.set_tick_params(labelsize=ticksize)

            if ytickspace == 0:
                ax.yaxis.set_ticks([])
            elif ytickspace is not None:
                ytick_space_start = math.ceil(ylim_left / ytickspace) * ytickspace
                ax.yaxis.set_ticks(np.arange(ytick_space_start, ylim_right, ytickspace))
            ax.set_ylim(ylim_left, ylim_right)
            ax.yaxis.set_tick_params(labelsize=ticksize)
            ax.grid(grid)
        else:
            (xscale, xtickspace, *xlim,
             yscale, ylim_left, ylim_right, ytickspace) = axis_options

            xlim_left = []
            xlim_right = []
            for j in range(0, len(xlim), 2):
                xlim_left.append(xlim[j])
                xlim_right.append(xlim[j + 1])

            if axes[1].get_xscale() != xscale:
                axes[1].set_xscale(xscale)
                axes[2].set_xscale(xscale)
            if axes[1].get_yscale() != yscale:
                axes[1].set_yscale(yscale)
                axes[2].set_yscale(yscale)

            if xtickspace is not None:
                xtick_space_start = math.ceil(xlim_left[0] / xtickspace) * xtickspace
                axes[1].xaxis.set_ticks(np.arange(xtick_space_start, xlim_right[0], xtickspace))
                axes[2].xaxis.set_ticks(np.arange(xtick_space_start, xlim_right[1], xtickspace))
            axes[1].set_xlim(xlim_left[0], xlim_right[0])
            axes[2].set_xlim(xlim_left[1], xlim_right[1])
            axes[1].xaxis.set_tick_params(labelsize=ticksize)
            axes[2].xaxis.set_tick_params(labelsize=ticksize)

            if ytickspace is not None:
                ytick_space_start = math.ceil(ylim_left / ytickspace) * ytickspace
                axes[1].yaxis.set_ticks(np.arange(ytick_space_start, ylim_right, ytickspace))
                axes[2].yaxis.set_ticks(np.arange(ytick_space_start, ylim_right, ytickspace))
            axes[1].set_ylim(ylim_left, ylim_right)
            axes[1].yaxis.set_tick_params(labelsize=ticksize)
            axes[2].yaxis.set_tick_params(labelsize=ticksize)

            axes[1].grid(grid)
            axes[2].grid(grid)

        # Restore the unit data
        ax.xaxis.converter = xconverter
        ax.yaxis.converter = yconverter
        ax.xaxis.set_units(xunits)
        ax.yaxis.set_units(yunits)
        ax.xaxis._update_axisinfo()
        ax.yaxis._update_axisinfo()

        if figure_edit.axis_is_broken is False:
            if xbreak is True and ybreak is True:
                if xbreak_start < xbreak_end and ybreak_start < ybreak_end:
                    baxes = brokenaxes(xlims=((xlim_left, xbreak_start), (xbreak_end, xlim_right)),
                                       ylims=((ylim_left, ybreak_start), (ybreak_end, ylim_right)),
                                       hspace=.05, fig=figure)
                    figure_edit.axis_is_broken = True
            elif xbreak is True:
                if xbreak_start < xbreak_end:
                    baxes = brokenaxes(xlims=((xlim_left, xbreak_start), (xbreak_end, xlim_right)), fig=figure)
                    figure_edit.axis_is_broken = True
                else:
                    print("The first limit has to be smaller than the second one.")
            elif ybreak is True:
                if ybreak_start < ybreak_end:
                    baxes = brokenaxes(ylims=((ylim_left, ybreak_start), (ybreak_end, ylim_right)),
                                       hspace=.05, fig=figure)
                    figure_edit.axis_is_broken = True

        # Set / Legend
        (leg_visible, leg_draggable, leg_ncol, leg_fontsize, leg_frameon, leg_shadow,
         leg_fancybox, leg_framealpha, leg_picker) = legend

        if figure_edit.axis_is_broken:
            handles, labels = figure.axes[2].get_legend_handles_labels()
        else:
            handles, labels = ax.get_legend_handles_labels()
        new_legend = ax.legend(handles, labels,
                               ncol=leg_ncol,
                               fontsize=float(leg_fontsize),
                               frameon=leg_frameon,
                               shadow=leg_shadow,
                               framealpha=leg_framealpha,
                               fancybox=leg_fancybox)

        new_legend.set_visible(leg_visible)
        new_legend.set_picker(leg_picker)
        new_legend.set_draggable(leg_draggable)

        # Set / Curves
        for index, curve in enumerate(curves):
            (label, linestyle, drawstyle, linewidth, color, create_fill, marker, markersize,
             markerfacecolor, markeredgecolor, remove_line) = curve
            lines = linedict[curvelabels[index]]
            for line in lines:
                line.set_label(label)
                line.set_linestyle(linestyle)
                line.set_drawstyle(drawstyle)
                line.set_linewidth(linewidth)
                rgba = mcolors.to_rgba(color)
                line.set_alpha(None)
                line.set_color(rgba)
                if marker != 'none':
                    line.set_marker(marker)
                    line.set_markersize(markersize)
                    line.set_markerfacecolor(markerfacecolor)
                    line.set_markeredgecolor(markeredgecolor)
                if create_fill is True:
                    if line.get_label() in fill_dict.keys():
                        pass
                    else:
                        new_fill = ax.fill_between(line.get_xdata(), line.get_ydata(), color=color)
                        new_fill.set_label('_Hidden Fill {}'.format(line.get_label()))
                        fill_dict[line.get_label()] = new_fill
                if remove_line is True:
                    try:
                        parent.signal_remove_line.emit(line)
                        line.remove()
                    except ValueError as e:
                        print(e)

        # Set / Errorbar Caplines
        for index, params in enumerate(errorbars):
            errorbar = errorbar_dict[errorbar_labels[index]]
            plotline, caplines, barlinecols = errorbar
            barlinecol = barlinecols[0]
            (markersize, linewidth, color) = params

            errorbar.set_label('_Hidden errorbar {}'.format(plotline.get_label()))

            for capline in caplines:
                capline.set_markersize(markersize)
                capline.set_markeredgewidth(linewidth)
                capline.set_markerfacecolor(color)
                capline.set_markeredgecolor(color)
            barlinecol.set_linewidth(linewidth)
            barlinecol.set_color(color)

        # Set / Fill under Curves
        for index, params in enumerate(fills):
            fill = fill_dict[fill_labels[index]]
            (face_color, remove_fill) = params

            fill.set_facecolor(face_color)

            if remove_fill:
                try:
                    fill.remove()
                except ValueError as e:
                    print(e)

        # Set / Images
        for index, image_settings in enumerate(images):
            image = imagedict[imagelabels[index]]
            label, cmap, low, high, interpolation = image_settings
            image.set_label(label)
            image.set_cmap(cm.get_cmap(cmap))
            image.set_clim(*sorted([low, high]))
            image.set_interpolation(interpolation)

        # Redraw
        figure.canvas.draw()

    data = formlayout.fedit(datalist, title="Figure options", parent=parent, apply=apply_callback)
                            # icon=get_icon('qt4_editor_options.svg'),


    if data is not None:
        apply_callback(data)

# Monkey-patch original figureoptions
from matplotlib.backends.qt_editor import figureoptions
figureoptions.figure_edit = figure_edit





