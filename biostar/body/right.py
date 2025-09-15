import dash_mantine_components as dmc
from dash import dash_table, dcc, html
from dash_iconify import DashIconify

from biostar.modules.data import PPEL_TABLE_COLUMNS, PPEL_TABLE_HIDDEN_COLUMNS
from biostar.modules.display import BASE_GRAPH_FIG, FONTS

HIERARCHY_TAB = [
    dmc.Flex(
        justify="space-between",
        align="center",
        pb=16,
        style={"borderBottom": "1px solid var(--mantine-color-default-border)"},
        children=[
            dmc.Flex(
                justify="start",
                align="center",
                gap="sm",
                children=[
                    dmc.Text("My Project", id="hierarchy-header", fw=500, fz="h2"),
                    dmc.Tooltip(
                        dmc.ActionIcon(
                            DashIconify(icon="carbon:settings", width=16),
                            id="button-configure-project",
                            size="md",
                            color="violet",
                            variant="light",
                        ),
                        position="bottom",
                        label="Configure project-level options",
                    ),
                    dmc.Button(
                        "Import from PPEL",
                        id="button-import-hardware",
                        size="xs",
                        color="violet",
                        n_clicks=0,
                    ),
                ],
            ),
            dmc.Flex(
                justify="end",
                align="center",
                gap="sm",
                children=[
                    dmc.Card(
                        withBorder=True,
                        radius="sm",
                        py=3,
                        my=6,
                        px=10,
                        fz=14,
                        bd="2px dashed var(--mantine-color-gray-6)",
                        bg="var(--mantine-color-gray-0)",
                        children="Rollup",
                    ),
                    dmc.Card(
                        withBorder=True,
                        radius="sm",
                        py=3,
                        my=6,
                        px=10,
                        fz=14,
                        bd="2px solid var(--mantine-color-yellow-6)",
                        bg="var(--mantine-color-yellow-0)",
                        children="Component (Unconfigured)",
                    ),
                    dmc.Card(
                        withBorder=True,
                        radius="sm",
                        py=3,
                        my=6,
                        px=10,
                        fz=14,
                        bd="2px solid var(--mantine-color-green-8)",
                        bg="var(--mantine-color-green-0)",
                        children="Component (Configured)",
                    ),
                ],
            ),
        ],
    ),
    dmc.Stack(
        [
            dmc.Grid(
                [
                    dmc.GridCol(dmc.Text("L2", fw=500, py=16), span="content"),
                    dmc.GridCol(
                        dmc.Flex(
                            id={"type": "hierarchy", "index": "l2"},
                            justify="start",
                            wrap="wrap",
                            columnGap="sm",
                            children=[],
                        ),
                        span="auto",
                    ),
                ],
                align="center",
                style={"borderBottom": "1px solid var(--mantine-color-default-border)"},
            ),
            dmc.Grid(
                [
                    dmc.GridCol(dmc.Text("L3", fw=500, py=16), span="content"),
                    dmc.GridCol(
                        dmc.Flex(
                            id={"type": "hierarchy", "index": "l3"},
                            justify="start",
                            wrap="wrap",
                            columnGap="sm",
                            children=[],
                        ),
                        span="auto",
                    ),
                ],
                align="center",
                style={"borderBottom": "1px solid var(--mantine-color-default-border)"},
            ),
            dmc.Grid(
                [
                    dmc.GridCol(dmc.Text("L4", fw=500, py=16), span="content"),
                    dmc.GridCol(
                        dmc.Flex(
                            id={"type": "hierarchy", "index": "l4"},
                            justify="start",
                            wrap="wrap",
                            columnGap="sm",
                            children=[],
                        ),
                        span="auto",
                    ),
                ],
                align="center",
                style={"borderBottom": "1px solid var(--mantine-color-default-border)"},
            ),
            dmc.Grid(
                [
                    dmc.GridCol(dmc.Text("L5", fw=500, py=16), span="content"),
                    dmc.GridCol(
                        dmc.Flex(
                            id={"type": "hierarchy", "index": "l5"},
                            justify="start",
                            wrap="wrap",
                            columnGap="sm",
                            children=[],
                        ),
                        span="auto",
                    ),
                ],
                align="center",
                style={"borderBottom": "1px solid var(--mantine-color-default-border)"},
            ),
            dmc.Grid(
                [
                    dmc.GridCol(dmc.Text("L6", fw=500, py=16), span="content"),
                    dmc.GridCol(
                        dmc.Flex(
                            id={"type": "hierarchy", "index": "l6"},
                            justify="start",
                            wrap="wrap",
                            columnGap="sm",
                            children=[],
                        ),
                        span="auto",
                    ),
                ],
                align="center",
                style={"borderBottom": "1px solid var(--mantine-color-default-border)"},
            ),
        ],
        gap=0,
    ),
    html.Div(id="temp-dump"),
]

PLOTS_TAB = [
    dmc.Grid(
        justify="space-between",
        align="flex-end",
        gutter="sm",
        mx=16,
        children=[
            dmc.GridCol(
                dmc.Select(
                    id="select-results-hardware-id",
                    searchable=True,
                    label="Hardware ID",
                    description="Hardware element for which to display results",
                    data=[],
                    value="My Component",
                    w="100%",
                ),
                span=6,
            ),
            dmc.GridCol(
                dmc.Select(
                    id="select-results-dim",
                    label="Dimension",
                    description="Display results for areas or volumes?",
                    data=[],
                    w="100%",
                ),
                span=6,
            ),
        ],
    ),
    dmc.Flex(
        justify="center",
        my=16,
        gap="md",
        children=[
            dmc.Alert(
                id="results-alert-mode", color="violet", title="Hardware Mode", children="--"
            ),
            dmc.Alert(
                id="results-alert-pct", color="violet", title="Sample Coverage", children="--"
            ),
            dmc.Alert(
                id="results-alert-density", color="violet", title="Target Density", children="--"
            ),
            dmc.Alert(
                id="results-alert-assessment",
                color="violet",
                title="Hardware Assessment",
                children="Target density satisfied for __% of simulations",
            ),
        ],
    ),
    dmc.Grid(
        [
            dmc.GridCol(
                span=6,
                children=dcc.Graph(id="bioburden-results", figure=BASE_GRAPH_FIG, responsive=True),
            ),
            dmc.GridCol(
                span=6,
                children=dcc.Graph(id="cfu-results", figure=BASE_GRAPH_FIG, responsive=True),
            ),
        ],
        mx=16,
    ),
    dmc.Grid(
        [
            dmc.GridCol(
                span=6,
                px=24,
                children=[
                    dmc.Table(
                        withColumnBorders=True,
                        withTableBorder=True,
                        styles={
                            "th": {"textAlign": "center", "width": "25%"},
                            "td": {"textAlign": "center", "width": "25%"},
                        },
                        children=[
                            dmc.TableThead(
                                [
                                    dmc.TableTr(
                                        [
                                            dmc.TableTh("Mean"),
                                            dmc.TableTh("5%"),
                                            dmc.TableTh("50%"),
                                            dmc.TableTh("95%"),
                                        ]
                                    )
                                ]
                            ),
                            dmc.TableTbody(id="bioburden-table", children=[]),
                        ],
                    )
                ],
            ),
            dmc.GridCol(
                span=6,
                px=24,
                children=[
                    dmc.Table(
                        withColumnBorders=True,
                        withTableBorder=True,
                        styles={
                            "th": {"textAlign": "center", "width": "25%"},
                            "td": {"textAlign": "center", "width": "25%"},
                        },
                        children=[
                            dmc.TableThead(
                                [
                                    dmc.TableTr(
                                        [
                                            dmc.TableTh("Mean"),
                                            dmc.TableTh("5%"),
                                            dmc.TableTh("50%"),
                                            dmc.TableTh("95%"),
                                        ]
                                    )
                                ]
                            ),
                            dmc.TableTbody(id="cfu-table", children=[]),
                        ],
                    )
                ],
            ),
        ],
        mx=16,
    ),
]

PPEL_TAB = [
    dcc.Download(id="download-ppel-export"),
    dmc.Flex(
        justify="end",
        align="center",
        gap="xs",
        direction="row-reverse",
        pb=8,
        children=[
            dmc.Menu(
                position="bottom-end",
                keepMounted=True,
                children=[
                    dmc.MenuTarget(dmc.Button("Toggle Columns", size="xs", color="gray.6")),
                    dmc.MenuDropdown(
                        style={"maxHeight": 300, "overflowY": "auto"},
                        children=[
                            dmc.CheckboxGroup(
                                id="checklist-datatable-ppel-columns",
                                value=[
                                    col["name"]
                                    for col in PPEL_TABLE_COLUMNS
                                    if col["name"] not in PPEL_TABLE_HIDDEN_COLUMNS
                                ],
                                children=dmc.Stack(
                                    p=8,
                                    children=[
                                        dmc.Checkbox(
                                            label=col["name"], value=col["name"], size="xs"
                                        )
                                        for col in PPEL_TABLE_COLUMNS
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            dmc.Button("Export to Excel", id="button-ppel-export", size="xs", color="teal.8"),
            dmc.SegmentedControl(
                id="control-ppel-percentile",
                value="Mean",
                data=["Mean", "5%", "50%", "95%"],
                size="xs",
                color="violet.2",
                autoContrast=True,
                styles={
                    "root": {"padding": 3},
                    "label": {"paddingLeft": 8, "paddingRight": 8},
                },
            ),
            dmc.Tooltip(
                dmc.ActionIcon(
                    DashIconify(icon="iconoir:info-circle", width=18),
                    id="button-table-definitions",
                    size="md",
                    color="indigo.4",
                ),
                label="Click to expand table defininitions",
                position="top-start",
            ),
        ],
    ),
    dash_table.DataTable(
        id="datatable-ppel",
        cell_selectable=False,
        data=[],
        columns=PPEL_TABLE_COLUMNS,
        hidden_columns=PPEL_TABLE_HIDDEN_COLUMNS,
        style_cell={
            "border": "1px solid var(--mantine-color-gray-5)",
            "fontFamily": FONTS,
            "fontSize": "14px",
            "paddingLeft": "8px",
            "paddingRight": "8px",
        },
        style_data={
            "backgroundColor": "var(--mantine-color-gray-0)",
        },
        style_header={
            "backgroundColor": "var(--mantine-color-gray-3)",
            "fontWeight": "bold",
        },
        style_table={"overflowX": "auto", "paddingBottom": 128},
        tooltip_duration=None,
    ),
]

RIGHT_DIV = dmc.Tabs(
    color="red.5",
    orientation="horizontal",
    value="estimate",
    variant="pills",
    children=[
        dmc.TabsList(
            grow=True,
            bd="1px solid var(--mantine-color-default-border)",
            mb=16,
            style={"borderRadius": "5px", "fontWeight": 600},
            children=[
                dmc.TabsTab("Build Project", value="hierarchy"),
                dmc.TabsTab("Estimate Bioburden", value="estimate"),
                dmc.TabsTab("Export PPEL", value="ppel"),
            ],
        ),
        dmc.TabsPanel(
            value="hierarchy",
            children=HIERARCHY_TAB,
        ),
        dmc.TabsPanel(value="estimate", children=PLOTS_TAB),
        dmc.TabsPanel(value="ppel", children=PPEL_TAB),
    ],
)
