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
from matplotlib.backends.qt_compat import QtGui


number_of_axis = 0

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

    if len(axes) == 1:
        axes, = axes
    else:
        figure_edit_brokenaxis(axes)
        return

    # Get / General
    # Cast to builtin floats as they have nicer reprs.
    xmin, xmax = map(float, axes.get_xlim())
    ymin, ymax = map(float, axes.get_ylim())
    xticks = axes.get_xticks()
    yticks = axes.get_yticks()
    if xticks != []:
        xtickspace = xticks[1] - xticks[0]
    else:
        xtickspace = None
    if yticks != []:
        ytickspace = yticks[1] - yticks[0]
    else:
        ytickspace = None

    if 'labelsize' in axes.xaxis._major_tick_kw:
        _ticksize = int(axes.xaxis._major_tick_kw['labelsize'])
    else:
        _ticksize = 15
    general = [(None, "<b>Figure Title</b>"),
               ('Title', axes.get_title()),
               ('Font Size', int(axes.title.get_fontsize())),
               sep,
               (None, "<b>Axes settings</b>"),
               ('Label Size', int(axes.xaxis.label.get_fontsize())),
               ('Tick Size', _ticksize),
               ('Show grid', axes.xaxis._gridOnMajor),
               sep,
               (None, "<b>X-Axis</b>"),
               ('Label', axes.get_xlabel()),
               ('Label Pad', axes.xaxis.labelpad),
               ('Scale', [axes.get_xscale(), 'linear', 'log', 'logit']),
               ('Lower Limit', axes.get_xlim()[0]),
               ('Upper Limit', axes.get_xlim()[1]),
               ('Tick Step Size', xtickspace),
               sep,
               (None, "<b>Y-Axis</b>"),
               ('Label', axes.get_ylabel()),
               ('Label Pad', axes.yaxis.labelpad),
               ('Scale', [axes.get_yscale(), 'linear', 'log', 'logit']),
               ('Lowet Limit', axes.get_ylim()[0]),
               ('Upper Limit', axes.get_ylim()[1]),
               ('Tick Step Size', ytickspace),
               sep,
               (None, "<b>Axis Break</b>"),
               ('x-Axis Break', False),
               ('start', 0.0),
               ('end', 0.0),
               ('y-Axis Break', False),
               ('start', 0.0),
               ('end', 0.0)
               ]

    if axes.legend_ is not None:
        old_legend = axes.get_legend()
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
    xconverter = axes.xaxis.converter
    yconverter = axes.yaxis.converter
    xunits = axes.xaxis.get_units()
    yunits = axes.yaxis.get_units()

    # Sorting for default labels (_lineXXX, _imageXXX).
    def cmp_key(label):
        match = re.match(r"(_line|_image)(\d+)", label)
        if match:
            return match.group(1), int(match.group(2))
        else:
            return label, 0

    # Get / Curves / errorbar capline
    linedict = {}
    ebcaplinedict = {}          # capline of errorbar
    for line in axes.get_lines():
        label = line.get_label()
        if '_nolegend_' in label:
            continue
        elif label.split(' ', 1)[0] == '_Hidden':     # Errorbars
            rest = label.split('_Hidden ', 1)[1]
            ebcaplinedict[rest] = line
            continue
        else:
            pass
        linedict[label] = line
    curves = []
    ebcaplines = []               # capline of errorbar

    # Get / errorbar barline
    ebbarlinedict = {}            # barline of errorbar
    for collection in axes.collections:
        label = collection.get_label()
        if '_nolegend_' in label:
            continue
        elif label.split(' ', 1)[0] == '_Hidden':     # Errorbars
            rest = label.split('_Hidden ', 1)[1]
            ebbarlinedict[rest] = collection
            continue
        else:
            pass
    ebbarlines = []                 # barline of errorbar

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
        line = linedict[label]
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

    # Errorbar capline
    ebcaplinelabels = sorted(ebcaplinedict, key=cmp_key)
    for label in ebcaplinelabels:
        line = ebcaplinedict[label]
        ec = mcolors.to_hex(
            mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
            keep_alpha=True)
        caplinedata = [
              ('Cap Size', line.get_markersize()),
              ('Edge color (RGBA)', ec)]
        ebcaplines.append([caplinedata, label, ""])
    # Is there a errorbar capline displayed?
    has_ebcaplines = bool(ebcaplines)

    # Errorbar barline
    ebbarlinelabels = sorted(ebbarlinedict, key=cmp_key)
    for label in ebbarlinelabels:
        collection = ebbarlinedict[label]
        color = mcolors.to_hex(
            mcolors.to_rgba(line.get_color(), line.get_alpha()),
            keep_alpha=True)
        barlinedata = [
              ('Line Width', collection.get_linewidth()[0]),
              ('Color (RGBA)', color)]
        ebbarlines.append([barlinedata, label, ""])
    # Is there a errorbar barline displayed?
    has_ebbarlines = bool(ebbarlines)

    # Get / Images
    imagedict = {}
    for image in axes.get_images():
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
    datalist = [(general, "Axes", ""), (legend, "Legend", "")]

    if curves:
        datalist.append((curves, "Curves", ""))
    if images:
        datalist.append((images, "Images", ""))
    if ebcaplines:
        datalist.append((ebcaplines, "Errorbar caplines", ""))
    if ebbarlines:
        datalist.append((ebbarlines, "Errorbar barlines", ""))

    def apply_callback(data):
        """This function will be called to apply changes"""

        figure = axes.get_figure()

        general = data.pop(0)
        legend = data.pop(0)
        curves = data.pop(0) if has_curve else []
        images = data.pop(0) if has_image else []
        ebcaplines = data.pop(0) if has_ebcaplines else []
        ebbarlines = data.pop(0) if has_ebbarlines else []
        if data:
            raise ValueError("Unexpected field")

        # Set / General
        (title, titlesize, labelsize, ticksize, grid, xlabel, xlabelpad, xscale, 
         xlim_left, xlim_right, xtickspace, ylabel, ylabelpad, yscale, ylim_left, ylim_right, ytickspace, 
         xbreak, xbreak_start, xbreak_end, ybreak, ybreak_start, ybreak_end) = general

        if axes.get_xscale() != xscale:
            axes.set_xscale(xscale)
        if axes.get_yscale() != yscale:
            axes.set_yscale(yscale)

        axes.set_title(title)
        axes.title.set_fontsize(titlesize)

        axes.set_xlabel(xlabel)
        axes.xaxis.labelpad = xlabelpad
        if xtickspace != None:
            xtick_space_start =  math.ceil(xlim_left / xtickspace) * xtickspace
            axes.xaxis.set_ticks(np.arange(xtick_space_start, xlim_right, xtickspace))
        axes.set_xlim(xlim_left, xlim_right)
        axes.xaxis.label.set_size(labelsize)
        axes.xaxis.set_tick_params(labelsize=ticksize)

        axes.set_ylabel(ylabel)
        axes.yaxis.labelpad = ylabelpad
        if ytickspace != None:
            ytick_space_start =  math.ceil(ylim_left / ytickspace) * ytickspace
            axes.yaxis.set_ticks(np.arange(ytick_space_start, ylim_right, ytickspace))
        axes.set_ylim(ylim_left, ylim_right)
        axes.yaxis.label.set_size(labelsize)
        axes.yaxis.set_tick_params(labelsize=ticksize)

        axes.grid(grid)

        # Restore the unit data
        axes.xaxis.converter = xconverter
        axes.yaxis.converter = yconverter
        axes.xaxis.set_units(xunits)
        axes.yaxis.set_units(yunits)
        axes.xaxis._update_axisinfo()
        axes.yaxis._update_axisinfo()

        if xbreak == True and ybreak ==True:
            baxes = brokenaxes(xlims=((xlim_left, xbreak_start), (xbreak_end, xlim_right)), 
                              ylims=((ylim_left, ybreak_start), (ybreak_end, ylim_right)), 
                              hspace=.05, fig=figure)
        elif xbreak == True:
            baxes = brokenaxes(xlims=((xlim_left, xbreak_start), (xbreak_end, xlim_right)), fig=figure)
        elif ybreak == True:
            baxes = brokenaxes(ylims=((ylim_left, ybreak_start), (ybreak_end, ylim_right)), hspace=.05, fig=figure)
        else:
            pass


        # Set / Legend
        (leg_visible, leg_draggable, leg_ncol, leg_fontsize, leg_frameon, leg_shadow,
         leg_fancybox, leg_framealpha, leg_picker) = legend

        new_legend = axes.legend(ncol=leg_ncol,
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
            line = linedict[curvelabels[index]]
            (label, linestyle, drawstyle, linewidth, color, marker, markersize,
             markerfacecolor, markeredgecolor, removeLine) = curve
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
            if removeLine == True:
                line.remove()

        # Set / Errorbar Caplines
        for index, capline in enumerate(ebcaplines):
            line = ebcaplinedict[ebcaplinelabels[index]]
            (markersize, markeredgecolor) = capline
            line.set_markersize(markersize)
            line.set_markerfacecolor(markerfacecolor)
            line.set_markeredgecolor(markeredgecolor)

        # Set / Errorbar Barlines
        for index, barline in enumerate(ebbarlines):
            collection = ebbarlinedict[ebbarlinelabels[index]]
            (linewidth, color) = barline
            collection.set_linewidth(linewidth)
            collection.set_color(color)

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

    data = formlayout.fedit(datalist, title="Figure options", parent=parent,
                            icon=get_icon('qt4_editor_options.svg'),
                            apply=apply_callback)

    if data is not None:
        apply_callback(data)




def figure_edit_brokenaxis(axes, parent = None):
    """Edit matplotlib figure options for broken axis"""
    sep = (None, None)  # separator

    # Get / General
    # Cast to builtin floats as they have nicer reprs.


    if 'labelsize' in axes[1].xaxis._major_tick_kw:
        _ticksize = int(axes[1].xaxis._major_tick_kw['labelsize'])
    else:
        _ticksize = 15
    general = [(None, "<b>Figure Title</b>"),
                ('Title', axes[0].get_title()),
                ('Font Size', int(axes[0].title.get_fontsize())),
                sep,
                (None, "<b>Axes settings</b>"),
                ('Label Size', int(axes[0].xaxis.label.get_fontsize())),
                ('Tick Size', _ticksize),
                ('Show grid', axes[0].xaxis._gridOnMajor),
                sep,
                (None, "<b>X-Axis</b>"),
                ('Label', axes[0].get_xlabel()),
                ('Label Pad', axes[0].xaxis.labelpad),

                sep,
                (None, "<b>Y-Axis</b>"),
                ('Label', axes[0].get_ylabel()),
                ('Label Pad', axes[0].yaxis.labelpad),
                ]

    xmin, xmax = map(float, axes[1].get_xlim())
    ymin, ymax = map(float, axes[1].get_ylim())
    xticks = axes[1].get_xticks()
    yticks = axes[1].get_yticks()
    if xticks != []:
        xtickspace = xticks[1] - xticks[0]
    else:
        xtickspace = None
    if yticks != []:
        ytickspace = yticks[1] - yticks[0]
    else:
        ytickspace = None

    axis_options = [
               # sep,
               # (None, "<b>Axis Break</b>"),
               # ('x-Axis Break', False),
               # ('start', 0.0),
               # ('end', 0.0),
               # ('y-Axis Break', False),
               # ('start', 0.0),
               # ('end', 0.0)           
               # sep,
                (None, "<b>X-Axis</b>"),
                ('Scale', [axes[1].get_xscale(), 'linear', 'log', 'logit']),
                # ('Lower Limit', axes[1].get_xlim()[0]),
                # ('Upper Limit', axes[1].get_xlim()[1]),
                ('Tick Step Size', xtickspace),
                sep,
                (None, "<b>Y-Axis</b>"),
                ('Scale', [axes[1].get_yscale(), 'linear', 'log', 'logit']),
                ('Lowet Limit', axes[1].get_ylim()[0]),
                ('Upper Limit', axes[1].get_ylim()[1]),
                ('Tick Step Size', ytickspace)
                ]

    for idx, itm in enumerate(axes[1:]):
        axis_options.insert(3+idx*3, (None, "%i. Segment"%(idx+1)))
        axis_options.insert(4+idx*3, ('Lower Limit', itm.get_xlim()[0]))
        axis_options.insert(5+idx*3, ('Upper Limit', itm.get_xlim()[1]))


    if axes[2].legend_ is not None:
        old_legend = axes[2].get_legend()
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
    xconverter = axes[0].xaxis.converter
    yconverter = axes[0].yaxis.converter
    xunits = axes[0].xaxis.get_units()
    yunits = axes[0].yaxis.get_units()

    # Sorting for default labels (_lineXXX, _imageXXX).
    def cmp_key(label):
        match = re.match(r"(_line|_image)(\d+)", label)
        if match:
            return match.group(1), int(match.group(2))
        else:
            return label, 0

    # Get / Curves / errorbar capline
    linedict = []
    ebcaplinedict = {}          # capline of errorbar
    for idx, ax in enumerate(axes[1:]):
        linedict.append({})
        for line in ax.get_lines():
            label = line.get_label()
            if '_nolegend_' in label:
                continue
            elif label.split(' ', 1)[0] == '_Hidden':     # Errorbars
                rest = label.split('_Hidden ', 1)[1]
                ebcaplinedict[rest] = line
                continue
            else:
                pass
            linedict[idx][label] = line
    curves = []
    ebcaplines = []               # capline of errorbar

    # Get / errorbar barline
    ebbarlinedict = {}            # barline of errorbar
    for collection in axes[1].collections:
        label = collection.get_label()
        if '_nolegend_' in label:
            continue
        elif label.split(' ', 1)[0] == '_Hidden':     # Errorbars
            rest = label.split('_Hidden ', 1)[1]
            ebbarlinedict[rest] = collection
            continue
        else:
            pass
    ebbarlines = []                 # barline of errorbar

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


    curvelabels = sorted(linedict[0], key=cmp_key)
    for label in curvelabels:
        line = linedict[0][label]
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

    # Errorbar capline
    ebcaplinelabels = sorted(ebcaplinedict, key=cmp_key)
    for label in ebcaplinelabels:
        line = ebcaplinedict[label]
        ec = mcolors.to_hex(
            mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
            keep_alpha=True)
        caplinedata = [
              ('Cap Size', line.get_markersize()),
              ('Edge color (RGBA)', ec)]
        ebcaplines.append([caplinedata, label, ""])
    # Is there a errorbar capline displayed?
    has_ebcaplines = bool(ebcaplines)

    # Errorbar barline
    ebbarlinelabels = sorted(ebbarlinedict, key=cmp_key)
    for label in ebbarlinelabels:
        collection = ebbarlinedict[label]
        color = mcolors.to_hex(
            mcolors.to_rgba(line.get_color(), line.get_alpha()),
            keep_alpha=True)
        barlinedata = [
              ('Line Width', collection.get_linewidth()[0]),
              ('Color (RGBA)', color)]
        ebbarlines.append([barlinedata, label, ""])
    # Is there a errorbar barline displayed?
    has_ebbarlines = bool(ebbarlines)

    # Get / Images
    imagedict = {}
    for image in axes[0].get_images():
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

    datalist = [(general, "Axes", ""), (axis_options, "Axes", ""), (legend, "Legend", "")]
    if curves:
        datalist.append((curves, "Curves", ""))
    if images:
        datalist.append((images, "Images", ""))
    if ebcaplines:
        datalist.append((ebcaplines, "Errorbar caplines", ""))
    if ebbarlines:
        datalist.append((ebbarlines, "Errorbar barlines", ""))

    def apply_callback(data):
        """This function will be called to apply changes"""

        figure = axes[0].get_figure()

        general = data.pop(0)
        axis_options = data.pop(0)
        legend = data.pop(0)
        curves = data.pop(0) if has_curve else []
        images = data.pop(0) if has_image else []
        ebcaplines = data.pop(0) if has_ebcaplines else []
        ebbarlines = data.pop(0) if has_ebbarlines else []
        if data:
            raise ValueError("Unexpected field")

        # Set / General
        (title, titlesize, labelsize, ticksize, grid, 
            xlabel, xlabelpad, ylabel, ylabelpad) = general

        (xscale, xtickspace, *xlim,
            yscale, ylim_left, ylim_right, ytickspace) = axis_options

        xlim_left  = []
        xlim_right = []

        for j in range(0, len(xlim), 2):
            xlim_left.append(xlim[j])
            xlim_right.append(xlim[j+1])

        if axes[1].get_xscale() != xscale:
            axes[1].set_xscale(xscale)
            axes[2].set_xscale(xscale)
        if axes[1].get_yscale() != yscale:
            axes[1].set_yscale(yscale)
            axes[2].set_yscale(yscale)

        axes[0].set_title(title)
        axes[0].title.set_fontsize(titlesize)

        axes[0].set_xlabel(xlabel)
        axes[0].xaxis.labelpad = xlabelpad
        if xtickspace != None:
            xtick_space_start =  math.ceil(xlim_left[0] / xtickspace) * xtickspace
            axes[1].xaxis.set_ticks(np.arange(xtick_space_start, xlim_right[0], xtickspace))
            axes[2].xaxis.set_ticks(np.arange(xtick_space_start, xlim_right[1], xtickspace))
        axes[1].set_xlim(xlim_left[0], xlim_right[0])
        axes[2].set_xlim(xlim_left[1], xlim_right[1])
        axes[0].xaxis.label.set_size(labelsize)
        axes[1].xaxis.set_tick_params(labelsize=ticksize)
        axes[2].xaxis.set_tick_params(labelsize=ticksize)

        axes[0].set_ylabel(ylabel)
        axes[0].yaxis.labelpad = ylabelpad
        if ytickspace != None:
            ytick_space_start =  math.ceil(ylim_left / ytickspace) * ytickspace
            axes[1].yaxis.set_ticks(np.arange(ytick_space_start, ylim_right, ytickspace))
            axes[2].yaxis.set_ticks(np.arange(ytick_space_start, ylim_right, ytickspace))
        axes[1].set_ylim(ylim_left, ylim_right)
        axes[0].yaxis.label.set_size(labelsize)
        axes[1].yaxis.set_tick_params(labelsize=ticksize)
        axes[2].yaxis.set_tick_params(labelsize=ticksize)

        axes[1].grid(grid)
        axes[2].grid(grid)

        # Restore the unit data
        axes[0].xaxis.converter = xconverter
        axes[0].yaxis.converter = yconverter
        axes[0].xaxis.set_units(xunits)
        axes[0].yaxis.set_units(yunits)
        axes[0].xaxis._update_axisinfo()
        axes[0].yaxis._update_axisinfo()

        # if xbreak == True and ybreak ==True:
        #     baxes = brokenaxes(xlims=((xlim_left, xbreak_start), (xbreak_end, xlim_right)), 
        #                       ylims=((ylim_left, ybreak_start), (ybreak_end, ylim_right)), 
        #                       hspace=.05, fig=figure)
        # elif xbreak == True:
        #     baxes = brokenaxes(xlims=((xlim_left, xbreak_start), (xbreak_end, xlim_right)), fig=figure)
        # elif ybreak == True:
        #     baxes = brokenaxes(ylims=((ylim_left, ybreak_start), (ybreak_end, ylim_right)), hspace=.05, fig=figure)
        # else:
        #     pass


        # Set / Legend
        (leg_visible, leg_draggable, leg_ncol, leg_fontsize, leg_frameon, leg_shadow,
         leg_fancybox, leg_framealpha, leg_picker) = legend

        new_legend = axes[2].legend(ncol=leg_ncol,
                                 fontsize=float(leg_fontsize),
                                 frameon=leg_frameon,
                                 shadow=leg_shadow,
                                 framealpha=leg_framealpha,
                                 fancybox=leg_fancybox)

        new_legend.set_visible(leg_visible)
        new_legend.set_picker(leg_picker)
        new_legend.set_draggable(leg_draggable)

        # Set / Curves
        for ld in linedict:
            for index, curve in enumerate(curves):
                line = ld[curvelabels[index]]
                (label, linestyle, drawstyle, linewidth, color, marker, markersize,
                 markerfacecolor, markeredgecolor, removeLine) = curve
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
                if removeLine == True:
                    line.remove()

        # Set / Errorbar Caplines
        for index, capline in enumerate(ebcaplines):
            line = ebcaplinedict[ebcaplinelabels[index]]
            (markersize, markeredgecolor) = capline
            line.set_markersize(markersize)
            line.set_markerfacecolor(markerfacecolor)
            line.set_markeredgecolor(markeredgecolor)

        # Set / Errorbar Barlines
        for index, barline in enumerate(ebbarlines):
            collection = ebbarlinedict[ebbarlinelabels[index]]
            (linewidth, color) = barline
            collection.set_linewidth(linewidth)
            collection.set_color(color)

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

    data = formlayout.fedit(datalist, title="Figure options", parent=parent,
                            icon=get_icon('qt4_editor_options.svg'),
                            apply=apply_callback)

    if data is not None:
        apply_callback(data)

    

# Monkey-patch original figureoptions
from matplotlib.backends.qt_editor import figureoptions
figureoptions.figure_edit = figure_edit
