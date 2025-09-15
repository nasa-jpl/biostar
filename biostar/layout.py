import os

import dash_mantine_components as dmc
from dash import dcc

from biostar.body.left import LEFT_DIV
from biostar.body.popup import POPUP_DIV
from biostar.body.right import RIGHT_DIV

WEBMASTER_EMAIL = os.getenv("WEBMASTER_EMAIL")

# HEADER AND FOOTER COMPONENTS

# Navbar + title
header = dmc.Box(
    style={"position": "fixed", "top": 0, "width": "100%", "zIndex": 2},
    children=[
        dmc.Grid(
            justify="space-between",
            align="center",
            gutter=0,
            bg="gray.9",
            c="gray.1",
            py=8,
            children=[
                dmc.GridCol(
                    span="content",
                    pl=24,
                    children=dmc.Flex(
                        justify="center",
                        gap=0,
                        children=dmc.Anchor(
                            href="http://www.jpl.nasa.gov/",
                            target="_blank",
                            children=dmc.Image(src="/static/biostar/images/corner_logo.png"),
                        ),
                    ),
                ),
                dmc.GridCol(
                    span="content",
                    pr=16,
                    children=dmc.Grid(
                        justify="end",
                        gutter=0,
                        children=[
                            dmc.GridCol(
                                span="content",
                                children=dmc.NavLink(
                                    label="NASA",
                                    href="https://www.nasa.gov/",
                                    target="_blank",
                                    active=True,
                                    color="gray.1",
                                    variant="subtle",
                                    px=8,
                                    style={"fontWeight": 600},
                                ),
                            ),
                            dmc.GridCol(
                                span="content",
                                children=dmc.NavLink(
                                    label="JPL",
                                    href="https://www.jpl.nasa.gov/",
                                    target="_blank",
                                    active=True,
                                    color="gray.1",
                                    variant="subtle",
                                    px=8,
                                    style={"fontWeight": 600},
                                ),
                            ),
                            dmc.GridCol(
                                span="content",
                                children=dmc.NavLink(
                                    label="Caltech",
                                    href="https://www.caltech.edu/",
                                    target="_blank",
                                    active=True,
                                    color="gray.1",
                                    variant="subtle",
                                    px=8,
                                    style={"fontWeight": 600},
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
        dmc.Grid(
            justify="center",
            align="stretch",
            gutter=0,
            py=12,
            children=[
                dmc.GridCol(
                    "BioSTAR",
                    span="content",
                    my="auto",
                    pr=16,
                    fz=32,
                    style={
                        "fontWeight": 500,
                        "color": "var(--mantine-color-red-5)",
                        "borderRight": "1px solid var(--mantine-color-gray-5)",
                    },
                ),
                dmc.GridCol(
                    [
                        dmc.Box(
                            "Bioburden and Sampling Tool for Assessing Risk",
                            style={
                                "fontWeight": 500,
                                "color": "var(--mantine-color-gray-6)",
                                "height": "1em",
                                "lineHeight": "1em",
                            },
                            fz=32,
                            mb=4,
                        ),
                        dmc.Box(
                            "NASA's bioburden estimation and sampling optimization utility",
                            fz=16,
                            style={
                                "fontWeight": 450,
                                "color": "var(--mantine-color-gray-7)",
                                "height": "1em",
                                "lineHeight": "1em",
                            },
                            mb=2,
                        ),
                    ],
                    span="content",
                    pl=16,
                ),
            ],
            style={"borderBottom": "1px solid var(--mantine-color-gray-5)"},
        ),
    ],
)

# Footer component
footer = dmc.Box(
    style={
        "textAlign": "center",
        "fontSize": 12,
        "position": "fixed",
        "bottom": "0",
        "width": "100%",
        "zIndex": 2,
        "backgroundColor": "var(--mantine-color-gray-1)",
        "borderTop": "1px solid var(--mantine-color-gray-5)",
    },
    children=dmc.Box(
        py=16,
        children=[
            dmc.Flex(
                justify="center",
                gap="sm",
                children=[
                    dmc.Text("Last Update: September 9, 2025", fz=12),
                    dmc.Text("|", fz=12),
                    dmc.Text(
                        fz=12,
                        children=[
                            "Questions & Comments: ",
                            dmc.Anchor(
                                "Webmaster",
                                href=f"mailto:{WEBMASTER_EMAIL}",
                                target="_blank",
                                fz=12,
                            ),
                        ],
                    ),
                ],
            ),
            dmc.Text(
                fz=12,
                children=[
                    "JPL is a federally funded research and development center staffed and managed for ",
                    dmc.Anchor("NASA", href="http://www.nasa.gov", target="blank_", fz=12),
                    " by ",
                    dmc.Anchor("Caltech", href="http://www.caltech.edu", target="blank_", fz=12),
                ],
            ),
        ],
    ),
)


# MAIN APP BODY

body = dmc.Box(
    px=0,
    w="100%",
    style={
        "position": "fixed",
        "top": 0,
        "height": "calc(100vh - 136px)",
        "marginTop": "136px",
        "paddingBottom": "69px",
    },
    children=[
        dmc.Grid(
            gutter=0,
            pl=16,
            pr=0,
            children=[
                # LHS sidebar window
                dmc.GridCol(
                    LEFT_DIV,
                    id="inputs-pane",
                    span=4,
                    bd="1px solid var(--mantine-color-gray-3)",
                    p=16,
                    mt=16,
                    style={
                        "overflowY": "auto",
                        "height": "calc(100vh - 136px - 69px - 32px)",
                        "borderRadius": 5,
                    },
                ),
                # RHS main window
                dmc.GridCol(
                    RIGHT_DIV,
                    id="results-pane",
                    span=8,
                    pt=16,
                    px=16,
                    style={
                        "overflowY": "auto",
                        "height": "calc(100vh - 136px)",
                        "paddingBottom": "85px",
                    },
                ),
            ],
        ),
        POPUP_DIV,
    ],
)


# OVERALL APP LAYOUT

layout = dmc.Box(
    id="main-container",
    style={"minHeight": "100vh", "position": "relative"},
    children=[
        # Storage to track hardware and project
        # Groups and samples are stored as data in their respective DataTables
        dcc.Store(
            id="hardware-json",
            data={
                "My Component": {
                    "id": "My Component",
                    "parent_id": None,
                    "level": 2,
                    "group": None,
                    "is_component": True,
                    "valid": True,
                    "dim": "2D (Area)",
                    "area": 1,
                    "volume": "",
                    "type": "Sampled",
                    "analogy": "-- Generic --",
                    "implied_id": None,
                    "spec": None,
                    "handling": "",
                    "ventilation": "",
                    "composition": "",
                    "cleaning_fab": "",
                    "cleaning_pre": "",
                    "cleaning_sit": "",
                    "reduction_fab": "",
                    "reduction_pre": "",
                    "reduction_sit": "",
                    "notes": "",
                }
            },
        ),
        dcc.Store(id="project-json", data={"name": "My Project", "group": ""}),
        # Trackers to handle 2-stage wipe then import for PPEL
        dcc.Store(id="ppel-storage", data={}),
        dcc.Store(id="ppel-wipe-flag", data=0),
        dcc.Store(id="ppel-import-flag", data=0),
        # Storage to track previous state of hardware/components/samples/project to support partial updates
        dcc.Store(id="groups-prev", data=[]),
        dcc.Store(id="groups-diff", data={}),
        dcc.Store(id="hardware-prev", data={}),
        dcc.Store(id="hardware-diff", data={}),
        dcc.Store(id="samples-prev", data=[]),
        dcc.Store(id="samples-diff", data={}),
        dcc.Store(id="project-prev", data={}),
        dcc.Store(id="project-diff", data={}),
        # Storage to track component simulations and rollup calculations
        dcc.Store(id="sims-components-json", data={"noop": True, "sims": {}}),
        dcc.Store(id="sims-rollups-json", data={}),
        # Main frontend content
        header,
        body,
        footer,
    ],
)
