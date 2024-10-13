# -*- coding: utf-8 -*-
"""
Basic functions to plot and inspect geometries.

These are very basic plotting functions to speed up the development of masks
and circuits. They can be used instead of writing and opening GDS files external
viewers. 
"""

import samplemaker.shapes as smsh
from samplemaker.shapes import GeomGroup
from samplemaker.devices import Device, DevicePort
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

_ViewerCurrentSliders = []
_ViewerCurrentDevice = None
_ViewerCurrentFigure = None


def __GeomGetPatchesPlotly(grp: "GeomGroup"):
    prop_cycle = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
    patches = []
    for geom in grp.group:
        geomtype = type(geom)
        if geom.layer < 0:
            continue
        lcolor = prop_cycle[np.mod(geom.layer, 10)]
        if geomtype == smsh.Poly:
            N = int(len(geom.data) / 2)
            xy = np.reshape(geom.data, (N, 2))
            patches.append(go.Scatter(x=xy[:, 0], y=xy[:, 1], fill="toself", line_color=lcolor))
            continue
        if geomtype == smsh.Circle:
            patches.append(go.Scatter(x=[geom.x0], y=[geom.y0], marker=dict(size=geom.r*2, color=lcolor), mode="markers"))
            continue
        if geomtype == smsh.Path:
            xy = np.transpose([geom.xpts, geom.ypts])
            patches.append(go.Scatter(x=xy[:, 0], y=xy[:, 1], line=dict(color=lcolor)))
            continue
        if geomtype == smsh.Text:
            print("text display is not supported, please convert to polygon first.")
            continue
        if geomtype == smsh.SRef:
            continue
        if geomtype == smsh.ARef:
            continue
        if geomtype == smsh.Ellipse:
            patches.append(go.Scatter(x=[geom.x0], y=[geom.y0], marker=dict(size=geom.r*2, color=lcolor), mode="markers"))
            continue
        if geomtype == smsh.Ring:
            gpl = geom.to_polygon()
            geom = gpl.group[0]
            N = int(len(geom.data) / 2)
            xy = np.reshape(geom.data, (N, 2))
            patches.append(go.Scatter(x=xy[:, 0], y=xy[:, 1], fill="toself", line_color=lcolor))
            continue
        if geomtype == smsh.Arc:
            gpl = geom.to_polygon()
            geom = gpl.group[0]
            N = int(len(geom.data) / 2)
            xy = np.reshape(geom.data, (N, 2))
            patches.append(go.Scatter(x=xy[:, 0], y=xy[:, 1], fill="toself", line_color=lcolor))
            continue
    return patches


def __GetPortPatchesPlotly(port: DevicePort):
    if port.name == "":
        return []
    patches = [go.Scatter(x=[port.x0], y=[port.y0], mode="markers", marker=dict(symbol="arrow-bar-up", size=12))]
    return patches


def __GetDevicePortsPatchesPlotly(dev: Device):
    patches = []
    for port in dev._ports.values():
        patches += __GetPortPatchesPlotly(port)

    return patches


def GeomView(grp: GeomGroup):
    """
    Plots a geometry in a Plotly window.
    Only polygons and circles are displayed. Most elements are either 
    ignored or converted to polygon.
    No flattening is performed, thus structure references are not displayed.

    Parameters
    ----------
    grp : samplemaker.shapes.GeomGroup
        The geometry to be displayed.

    Returns
    -------
    None.

    """
    patches = __GeomGetPatchesPlotly(grp)
    fig = go.Figure()
    for patch in patches:
        fig.add_trace(patch)

    fig.update_layout(
        showlegend=False, 
        title="Geometry View", 
        xaxis=dict(scaleanchor=None),  # Allow flexible zoom
        yaxis=dict(scaleratio=None)    # Allow flexible zoom
    )
    fig.show()


def __update_scrollbar_plotly(val):
    global _ViewerCurrentDevice
    global _ViewerCurrentSliders
    global _ViewerCurrentFigure

    dev = _ViewerCurrentDevice
    for slider, param in zip(_ViewerCurrentSliders, dev._p.keys()):
        dev.set_param(param, slider.value)

    dev.use_references = False
    dev.initialize()
    geomE = dev.run()
    bb = geomE.bounding_box()
    patches = __GeomGetPatchesPlotly(geomE)
    patches += __GetDevicePortsPatchesPlotly(dev)

    _ViewerCurrentFigure.data = []  # clear old data
    for patch in patches:
        _ViewerCurrentFigure.add_trace(patch)

    _ViewerCurrentFigure.update_layout(
        title=dev._name,
        xaxis=dict(range=[bb.llx, bb.urx()]),
        yaxis=dict(range=[bb.lly, bb.ury()]),
        showlegend=False
    )
    _ViewerCurrentFigure.show()


def DeviceInspect(devcl: Device):
    """
    Interactive display of devices defined from `samplemaker.devices`.
    The device is rendered according to the default parameters.
    Additionally, a set of sliders is created to interactively modify 
    the parameters and observe the changes in real-time.
    If the device includes ports, they are displayed as blue arrows.    
    
    Parameters
    ----------
    devcl : samplemaker.devices.Device
        A device object to be displayed.

    Returns
    -------
    None.

    """
    global _ViewerCurrentDevice
    global _ViewerCurrentSliders
    global _ViewerCurrentFigure

    dev = devcl.build()
    _ViewerCurrentDevice = dev
    geomE = dev.run()
    geomE = geomE.flatten()

    patches = __GeomGetPatchesPlotly(geomE)
    patches += __GetDevicePortsPatchesPlotly(dev)

    fig = go.Figure()
    for patch in patches:
        fig.add_trace(patch)

    bb = geomE.bounding_box()
    fig.update_layout(
        title=dev._name,
        xaxis=dict(range=[bb.llx, bb.urx()]),
        yaxis=dict(range=[bb.lly, bb.ury()]),
        showlegend=False
    )
    fig.show()

    _ViewerCurrentFigure = fig

    sliders = []
    for param in dev._p.keys():
        slider = go.layout.Slider(
            currentvalue={"visible": True, "prefix": param + ": "},
            steps=[{'label': str(i), 'value': i} for i in range(0, int(dev._p[param] * 10) + 1, int(dev._p[param] / 10))],
            value=dev._p[param]
        )
        sliders.append(slider)

    _ViewerCurrentSliders = sliders
