from datetime import date

import dash_mantine_components as dmc
from dash import dash_table, html
from dash_iconify import DashIconify

from biostar.modules.data import (
    PROCESSING_TECHNIQUES,
    SAMPLE_TABLE_COLUMNS,
    SAMPLE_TABLE_HIDDEN_COLUMNS,
    SAMPLING_DEVICE_TYPE_MAP,
)
from biostar.modules.display import FONTS

ADD_HARDWARE_TAB = [
    html.Div(id="notifications-group"),
    html.Div(id="notifications-hardware"),
    dmc.Accordion(
        multiple=True,
        variant="contained",
        radius="xs",
        value=["new-hardware-element"],
        children=[
            dmc.AccordionItem(
                value="new-hardware-group",
                children=[
                    dmc.AccordionControl("New Hardware Group"),
                    dmc.AccordionPanel(
                        [
                            dmc.TextInput(
                                id="input-group-tag",
                                label="Group Tag",
                                description="Any string to uniquely identify the group (descriptive ones are better!)",
                                value="",
                                w="100%",
                                mb=4,
                            ),
                            dmc.Flex(
                                justify="space-between",
                                gap="sm",
                                mb=4,
                                children=[
                                    dmc.NumberInput(
                                        id="input-group-density-2d",
                                        min=0,
                                        w="100%",
                                        label="Target Density (2D) (spores / m²)",
                                        description="Used to assess associated areas",
                                    ),
                                    dmc.NumberInput(
                                        id="input-group-density-3d",
                                        min=0,
                                        w="100%",
                                        label="Target Density (3D) (spores / cm³)",
                                        description="Used to assess associated volumes",
                                    ),
                                ],
                            ),
                            dmc.Flex(
                                justify="end",
                                mt=12,
                                children=[
                                    dmc.Button(
                                        "Record Group",
                                        id="button-record-group",
                                        color="violet",
                                        size="sm",
                                        n_clicks=0,
                                        disabled=True,
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
            ),
            dmc.AccordionItem(
                value="groups-summary",
                children=[
                    dmc.AccordionControl("Groups Summary"),
                    dmc.AccordionPanel(
                        [
                            dash_table.DataTable(
                                id="datatable-groups",
                                row_deletable=True,
                                data=[],
                                columns=[
                                    {
                                        "name": col,
                                        "id": col,
                                        "editable": col != "Group Tag",
                                        "type": "text" if col == "Group Tag" else "numeric",
                                    }
                                    for col in [
                                        "Group Tag",
                                        "Target Density (2D)",
                                        "Target Density (3D)",
                                    ]
                                ],
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
                                style_table={"overflowX": "auto"},
                            ),
                        ]
                    ),
                ],
            ),
            dmc.AccordionItem(
                value="new-hardware-element",
                children=[
                    dmc.AccordionControl("New Hardware Element"),
                    dmc.AccordionPanel(
                        [
                            dmc.TextInput(
                                id="input-hardware-id",
                                label="Hardware ID",
                                description="Any string to uniquely identify the hardware element (descriptive ones are better!)",
                                mb=4,
                            ),
                            dmc.Select(
                                id="select-hardware-parent-id",
                                description="Parent hardware element, if applicable (elements with no parent assumed L2)",
                                placeholder="Select one or leave blank for top-level (L2) components...",
                                clearable=True,
                                searchable=True,
                                mb=8,
                                label=dmc.Flex(
                                    justify="start",
                                    align="center",
                                    gap=4,
                                    children=[
                                        "Parent ID",
                                        dmc.Tooltip(
                                            DashIconify(
                                                icon="material-symbols-light:indeterminate-question-box-rounded",
                                                width=20,
                                            ),
                                            label="Don't see the hardware you are looking for? Make sure there are no samples for it in the database (rollup hardware cannot have samples)!",
                                            boxWrapperProps={"style": {"display": "flex"}},
                                        ),
                                    ],
                                ),
                            ),
                            dmc.Flex(
                                justify="end",
                                mt=12,
                                children=[
                                    dmc.Button(
                                        "Record Hardware",
                                        id="button-record-hardware",
                                        color="violet",
                                        size="sm",
                                        n_clicks=0,
                                        disabled=True,
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
            ),
        ],
    ),
]


SAMPLES_TAB = [
    html.Div(id="notifications-sample-add"),
    html.Div(id="notifications-sample-change"),
    dmc.Accordion(
        multiple=True,
        variant="contained",
        radius="xs",
        value=[],
        children=[
            dmc.AccordionItem(
                value="add-sample",
                children=[
                    dmc.AccordionControl("Add Sample"),
                    dmc.AccordionPanel(
                        [
                            dmc.Center(
                                "REQUIRED INPUTS",
                                style={"borderBottom": "1px solid var(--mantine-color-gray-5)"},
                                c="gray.6",
                                mb=4,
                            ),
                            dmc.TextInput(
                                id="input-sample-id",
                                mb=4,
                                label="Sample ID",
                                description="Any string to uniquely identify the sample (descriptive ones are better!)",
                            ),
                            dmc.Select(
                                id="select-sample-hardware-id",
                                mb=4,
                                placeholder="Select one or define new components to add options...",
                                allowDeselect=False,
                                label=dmc.Flex(
                                    justify="start",
                                    align="center",
                                    gap=4,
                                    children=[
                                        "Sampled Hardware ID",
                                        dmc.Tooltip(
                                            DashIconify(
                                                icon="material-symbols-light:indeterminate-question-box-rounded",
                                                width=20,
                                            ),
                                            label="Don't see the hardware you are looking for? Make sure it has Component Type 'Sampled' and provides all required inputs (the component should be green on the Build Project tab)!",
                                            boxWrapperProps={"style": {"display": "flex"}},
                                        ),
                                    ],
                                ),
                            ),
                            dmc.Select(
                                id="select-sample-accountable",
                                data=[
                                    {"label": "Yes", "value": "Yes"},
                                    {"label": "No", "value": "No"},
                                ],
                                value="Yes",
                                mb=4,
                                label="PP Accountable",
                                description="Non-accountable samples will be recorded in the tool but ignored for all bioburden calculations",
                                allowDeselect=False,
                            ),
                            dmc.Flex(
                                justify="space-between",
                                gap="sm",
                                children=[
                                    dmc.Select(
                                        id="select-sample-device",
                                        data=[
                                            {"label": opt, "value": opt} for opt in ["Swab", "Wipe"]
                                        ],
                                        value="Swab",
                                        w="100%",
                                        placeholder="Select one...",
                                        label="Sampling Device",
                                        allowDeselect=False,
                                    ),
                                    dmc.Select(
                                        id="select-sample-device-type",
                                        w="100%",
                                        data=SAMPLING_DEVICE_TYPE_MAP["Swab"],
                                        value="Puritan Cotton",
                                        placeholder="Select one...",
                                        label="Sampling Device Type",
                                        allowDeselect=False,
                                    ),
                                ],
                                mb=4,
                            ),
                            dmc.Select(
                                id="select-sample-technique",
                                data=PROCESSING_TECHNIQUES,
                                value="NASA Standard",
                                mb=4,
                                placeholder="Select one...",
                                label="Processing Technique",
                                allowDeselect=False,
                            ),
                            dmc.NumberInput(
                                id="input-sample-area-volume",
                                min=0,
                                step=0.1,
                                mb=4,
                                label="Sampled Area (m²)",
                            ),
                            dmc.NumberInput(
                                id="input-sample-fraction",
                                value=0.8,
                                min=0,
                                max=1,
                                step=0.1,
                                mb=4,
                                label="Pour Fraction",
                                description="Defaults provided but feel free to change for your sample",
                            ),
                            dmc.NumberInput(
                                id="input-sample-cfu",
                                min=0,
                                step=1,
                                allowDecimal=False,
                                label="CFU",
                                mb=12,
                                description="Total colony forming units observed across all dishes",
                            ),
                            dmc.Center(
                                "METADATA",
                                style={"borderBottom": "1px solid var(--mantine-color-gray-5)"},
                                c="gray.6",
                                mb=4,
                            ),
                            dmc.Flex(
                                justify="space-between",
                                gap="sm",
                                mb=4,
                                children=[
                                    dmc.TextInput(
                                        id="input-sample-assay-name",
                                        label="Assay Name",
                                        w="100%",
                                    ),
                                    dmc.DateInput(
                                        id="input-sample-assay-date",
                                        valueFormat="YYYY-MM-DD",
                                        value=date.today(),
                                        w="100%",
                                        label="Assay Date",
                                    ),
                                ],
                            ),
                            dmc.Flex(
                                justify="space-between",
                                gap="sm",
                                mb=4,
                                children=[
                                    dmc.TextInput(
                                        id="input-sample-pp-cert",
                                        label="PP Cert #",
                                        w="100%",
                                    ),
                                    dmc.Select(
                                        id="select-sample-control",
                                        data=[
                                            "Facility Control",
                                            "Negative Control",
                                            "Positive Control",
                                            "Field Control",
                                            "Other Control",
                                            "Not Control",
                                        ],
                                        value="Not Control",
                                        label="Control Type",
                                        allowDeselect=False,
                                        w="100%",
                                    ),
                                ],
                            ),
                            dmc.Textarea(
                                id="input-sample-notes",
                                label="Sampling Notes",
                                required=False,
                            ),
                            dmc.Flex(
                                justify="end",
                                gap="sm",
                                mt=12,
                                children=[
                                    dmc.Button(
                                        "Record Sample",
                                        id="button-record-sample",
                                        color="violet",
                                        size="sm",
                                        n_clicks=0,
                                        disabled=True,
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
            ),
        ],
    ),
    dmc.Flex(
        justify="end",
        gap="xs",
        direction="row-reverse",
        mt=12,
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
                                id="checklist-datatable-samples-columns",
                                value=[
                                    col["name"]
                                    for col in SAMPLE_TABLE_COLUMNS
                                    if col["name"] not in SAMPLE_TABLE_HIDDEN_COLUMNS
                                ],
                                children=dmc.Stack(
                                    p=8,
                                    children=[
                                        dmc.Checkbox(
                                            label=col["name"], value=col["name"], size="xs"
                                        )
                                        for col in SAMPLE_TABLE_COLUMNS
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            dmc.Button(
                "Import from PPS",
                id="button-import-samples",
                color="violet",
                size="xs",
                n_clicks=0,
            ),
        ],
    ),
    dash_table.DataTable(
        id="datatable-samples",
        row_deletable=True,
        data=[
            {
                "Sample ID": "My Sample",
                "Hardware ID": "My Component",
                "PP Accountable": "Yes",
                "Sampled Area": 0.0025,
                "Sampled Volume": None,
                "Sampling Device": "Swab",
                "Sampling Device Type": "Puritan Cotton",
                "Processing Technique": "NASA Standard",
                "Pour Fraction": 0.8,
                "CFU": 0,
                "Assay Name": "My Assay",
                "Assay Date": date.today().isoformat(),
                "PP Cert #": "12345",
                "Control Type": "Not Control",
                "Sampling Notes": "",
            }
        ],
        columns=SAMPLE_TABLE_COLUMNS,
        hidden_columns=SAMPLE_TABLE_HIDDEN_COLUMNS,
        style_cell={
            "border": "1px solid var(--mantine-color-gray-5)",
            "whiteSpace": "nowrap",
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
        sort_action="native",
        sort_mode="multi",
    ),
]

LEFT_DIV = dmc.Tabs(
    orientation="horizontal",
    value="samples",
    children=[
        dmc.TabsList(
            grow=True,
            mb=12,
            children=[
                dmc.TabsTab("Hardware", value="hardware"),
                dmc.TabsTab("Samples", value="samples"),
            ],
        ),
        dmc.TabsPanel(value="hardware", children=ADD_HARDWARE_TAB),
        dmc.TabsPanel(value="samples", children=SAMPLES_TAB),
    ],
)
