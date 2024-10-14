import threading
import plotly.graph_objects as go
from dash import dcc, html, Input, Output
import dash
import samplemaker.shapes as smsh
from samplemaker.shapes import GeomGroup
from samplemaker.devices import Device, DevicePort
import numpy as np
from dash.exceptions import PreventUpdate
import random


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
            
        elif geomtype == smsh.Circle:
            theta = np.linspace(0, 2 * np.pi, 100)
            x_circle = geom.x0 + geom.r * np.cos(theta)
            y_circle = geom.y0 + geom.r * np.sin(theta)
            patches.append(go.Scatter(x=x_circle, y=y_circle, fill="toself", line_color=lcolor))

        elif geomtype == smsh.Path:
            xy = np.transpose([geom.xpts, geom.ypts])
            patches.append(go.Scatter(x=xy[:, 0], y=xy[:, 1], mode='lines', line=dict(color=lcolor)))

        elif geomtype == smsh.Ellipse:
            theta = np.linspace(0, 2 * np.pi, 100)
            x_ellipse = geom.x0 + geom.r * np.cos(theta)
            y_ellipse = geom.y0 + geom.r1 * np.sin(theta)
            patches.append(go.Scatter(x=x_ellipse, y=y_ellipse, fill="toself", line_color=lcolor))

        elif geomtype == smsh.Ring:
            outer_circle = geom.r * np.column_stack((np.cos(np.linspace(0, 2 * np.pi, 100)), np.sin(np.linspace(0, 2 * np.pi, 100))))
            inner_circle = geom.r1 * np.column_stack((np.cos(np.linspace(0, 2 * np.pi, 100)), np.sin(np.linspace(0, 2 * np.pi, 100))))
            patches.append(go.Scatter(x=outer_circle[:, 0], y=outer_circle[:, 1], fill="toself", line_color=lcolor))
            patches.append(go.Scatter(x=inner_circle[:, 0], y=inner_circle[:, 1], fill="toself", line_color="white"))

        elif geomtype == smsh.Arc:
            theta = np.linspace(geom.start_angle, geom.end_angle, 100)
            x_arc = geom.x0 + geom.r * np.cos(theta)
            y_arc = geom.y0 + geom.r * np.sin(theta)
            patches.append(go.Scatter(x=x_arc, y=y_arc, mode='lines', line=dict(color=lcolor)))
            
    return patches


def __GetPortPatchesPlotly(port: DevicePort):
    if port.name == "":
        return []
    return [go.Scatter(x=[port.x0], y=[port.y0], mode="markers", marker=dict(symbol="arrow-bar-up", size=12))]


def __GetDevicePortsPatchesPlotly(dev: Device):
    patches = []
    for port in dev._ports.values():
        patches += __GetPortPatchesPlotly(port)
    return patches


def setup_layout(app, dev):
    global _ViewerCurrentDevice
    _ViewerCurrentDevice = dev

    geom = _ViewerCurrentDevice.run().flatten()

    fig = go.Figure()
    patches = __GeomGetPatchesPlotly(geom)
    patches += __GetDevicePortsPatchesPlotly(_ViewerCurrentDevice)

    for patch in patches:
        fig.add_trace(patch)

    bb = geom.bounding_box()
    fig.update_layout(
        title=_ViewerCurrentDevice._name,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(range=[bb.llx, bb.urx()], scaleanchor="y", scaleratio=1, showgrid=True, gridcolor='LightGray', zeroline=False),
        yaxis=dict(range=[bb.lly, bb.ury()], showgrid=True, gridcolor='LightGray', zeroline=False),
        showlegend=False
    )

    sliders = []
    for param in _ViewerCurrentDevice._p.keys():
        minv = 0
        maxv = _ViewerCurrentDevice._p[param] * 10 if _ViewerCurrentDevice._p[param] > 0 else 1
        prange = _ViewerCurrentDevice._prange[param]
        if prange[1] != np.inf:
            maxv = prange[1]
        if prange[0] != 0:
            minv = prange[0]
        step = _ViewerCurrentDevice._p[param] / 10 if _ViewerCurrentDevice._ptype[param] != int else 1

        slider = dcc.Slider(
            id=f'slider-{param}',
            min=minv,
            max=maxv,
            value=_ViewerCurrentDevice._p[param],
            step=step,
            marks=None,
            tooltip={"placement": "bottom", "always_visible": True}
        )
        sliders.append(html.Div([html.Label(f'{param}:'), slider]))

    app.layout = html.Div([
        html.H1(f"Device: {_ViewerCurrentDevice._name}"),
        dcc.Graph(id='device-graph', figure=fig),
        html.Div(id='slider-container', children=sliders)
    ], style={"background-color": "white", "padding": "20px", "border-radius": "10px", "height": "800px", "overflowY": "scroll", "text-align": "center"})


def DeviceInspect(devcl: Device, fix_aspect_ratio=True, plot_height=800):
    # Create a new app for each device inspection
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    setup_layout(app, devcl.build())

    @app.callback(
        Output('device-graph', 'figure'),
        [Input(f'slider-{param}', 'value') for param in _ViewerCurrentDevice._p.keys()]
    )
    def update_graph(*slider_values):
        if _ViewerCurrentDevice is None:
            raise PreventUpdate

        dev = _ViewerCurrentDevice
        for param, value in zip(dev._p.keys(), slider_values):
            dev.set_param(param, value)

        dev.use_references = False
        dev.initialize()
        geom = dev.run()

        fig = go.Figure()
        patches = __GeomGetPatchesPlotly(geom)
        patches += __GetDevicePortsPatchesPlotly(dev)

        for patch in patches:
            fig.add_trace(patch)

        bb = geom.bounding_box()
        xaxis_config = dict(range=[bb.llx, bb.urx()], showgrid=True, gridcolor='LightGray', zeroline=False)
        yaxis_config = dict(range=[bb.lly, bb.ury()], showgrid=True, gridcolor='LightGray', zeroline=False)

        if fix_aspect_ratio:
            xaxis_config.update(scaleanchor="y", scaleratio=1)

        fig.update_layout(
            title=dev._name,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=xaxis_config,
            yaxis=yaxis_config,
            showlegend=False,
            height=plot_height  # Set the height of the plot
        )

        return fig

    # Assign a unique port to avoid conflicts
    port = random.randint(8050, 8099)

    # Run the app in a new thread
    threading.Thread(target=app.run_server, kwargs={'port': port, 'debug': True, 'use_reloader': False}).start()


def GeomView(grp: GeomGroup, fix_aspect_ratio=True, plot_height=800):
    """
    Plots a geometry in a Plotly window.
    Only polygons, circles, paths, ellipses, rings, and arcs are displayed.
    No flattening is performed, thus structure references are not displayed.

    Parameters
    ----------
    grp : samplemaker.shapes.GeomGroup
        The geometry to be displayed.
    fix_aspect_ratio : bool, optional
        If True, the plot will have an aspect ratio of 1:1. If False, the aspect ratio will be auto.
    plot_height : int, optional
        The height of the plot in pixels. Default is 800.

    Returns
    -------
    None.
    """
    patches = __GeomGetPatchesPlotly(grp)
    fig = go.Figure()
    for patch in patches:
        fig.add_trace(patch)

    xaxis_config = dict(showgrid=True, gridcolor='LightGray', zeroline=False)
    yaxis_config = dict(showgrid=True, gridcolor='LightGray', zeroline=False)

    if fix_aspect_ratio:
        xaxis_config.update(scaleanchor="y", scaleratio=1)

    fig.update_layout(
        showlegend=False,
        title="Geometry View",
        xaxis=xaxis_config,
        yaxis=yaxis_config,
        paper_bgcolor="white",  # Background color for the outer area
        plot_bgcolor="white",   # Background color for the plot area
        height=plot_height      # Set the height of the plot
    )
    fig.show()
