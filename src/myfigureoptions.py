# https://stackoverflow.com/questions/53099295/matplotlib-navigationtoolbar-advanced-figure-options
# https://github.com/matplotlib/matplotlib/blob/master/lib/matplotlib/backends/qt_editor/figureoptions.py
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# see the mpl licenses directory for a copy of the license
# Modified to add a title fontsize

"""Module that provides a GUI-based editor for matplotlib's figure options."""

import os.path
import re

import matplotlib
from matplotlib import cm, colors as mcolors, markers, image as mimage
import matplotlib.backends.qt_editor._formlayout as formlayout
from matplotlib.backends.qt_compat import QtGui


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

    # Get / General
    # Cast to builtin floats as they have nicer reprs.
    xmin, xmax = map(float, axes.get_xlim())
    ymin, ymax = map(float, axes.get_ylim())
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
               ('Scale', [axes.get_xscale(), 'linear', 'log', 'logit']),
               ('Upper Limit', axes.get_xlim()[0]),
               ('Lower Limit', axes.get_xlim()[1]),
               sep,
               (None, "<b>Y-Axis</b>"),
               ('Label', axes.get_ylabel()),
               ('Scale', [axes.get_yscale(), 'linear', 'log', 'logit']),
               ('Upper Limit', axes.get_ylim()[0]),
               ('Lower Limit', axes.get_ylim()[1])
               ]

    if axes.legend_ is not None:
        old_legend = axes.get_legend()
        _draggable = old_legend._draggable is not None
        _ncol = old_legend._ncol
        _fontsize = int(old_legend._fontsize)
        _frameon = old_legend._drawFrame
        _shadow = old_legend.shadow
        _fancybox = type(old_legend.legendPatch.get_boxstyle()) == matplotlib.patches.BoxStyle.Round
        _framealpha = old_legend.get_frame().get_alpha()
        _picker = 5
    else:
        _draggable = False
        _ncol = 1
        _fontsize = 15
        _frameon = True
        _shadow = True
        _fancybox = True
        _framealpha = 0.5
        _picker = 5

    legend = [('Draggable', _draggable),
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

    # Get / Curves
    linedict = {}
    for line in axes.get_lines():
        label = line.get_label()
        if label == '_nolegend_':
            continue
        linedict[label] = line
    curves = []

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
            ('Edge color (RGBA)', ec)]
        curves.append([curvedata, label, ""])
    # Is there a curve displayed?
    has_curve = bool(curves)

    # Get / Images
    imagedict = {}
    for image in axes.get_images():
        label = image.get_label()
        if label == '_nolegend_':
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

    def apply_callback(data):
        """This function will be called to apply changes"""

        general = data.pop(0)
        legend = data.pop(0)
        curves = data.pop(0) if has_curve else []
        images = data.pop(0) if has_image else []
        if data:
            raise ValueError("Unexpected field")

        # Set / General
        (title, titlesize, labelsize, ticksize, grid, xlabel, xscale, xlim_left, xlim_right,
         ylabel, yscale, ylim_left, ylim_right) = general

        if axes.get_xscale() != xscale:
            axes.set_xscale(xscale)
        if axes.get_yscale() != yscale:
            axes.set_yscale(yscale)

        axes.set_title(title)
        axes.title.set_fontsize(titlesize)

        axes.set_xlabel(xlabel)
        axes.set_xlim(xlim_left, xlim_right)
        axes.xaxis.label.set_size(labelsize)
        axes.xaxis.set_tick_params(labelsize=ticksize)

        axes.set_ylabel(ylabel)
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

        # Set / Legend
        (leg_draggable, leg_ncol, leg_fontsize, leg_frameon, leg_shadow,
         leg_fancybox, leg_framealpha, leg_picker) = legend

        new_legend = axes.legend(ncol=leg_ncol,
                                 fontsize=float(leg_fontsize),
                                 frameon=leg_frameon,
                                 shadow=leg_shadow,
                                 framealpha=leg_framealpha,
                                 fancybox=leg_fancybox)

        new_legend.set_picker(leg_picker)
        new_legend.set_draggable(leg_draggable)

        # Set / Curves
        for index, curve in enumerate(curves):
            line = linedict[curvelabels[index]]
            (label, linestyle, drawstyle, linewidth, color, marker, markersize,
             markerfacecolor, markeredgecolor) = curve
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

        # Set / Images
        for index, image_settings in enumerate(images):
            image = imagedict[imagelabels[index]]
            label, cmap, low, high, interpolation = image_settings
            image.set_label(label)
            image.set_cmap(cm.get_cmap(cmap))
            image.set_clim(*sorted([low, high]))
            image.set_interpolation(interpolation)

        # Redraw
        figure = axes.get_figure()
        figure.canvas.draw()

    data = formlayout.fedit(datalist, title="Figure options", parent=parent,
                            icon=get_icon('qt4_editor_options.svg'),
                            apply=apply_callback)

    if data is not None:
        apply_callback(data)


# Monkey-patch original figureoptions
from matplotlib.backends.qt_editor import figureoptions
figureoptions.figure_edit = figure_edit
