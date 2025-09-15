import dash_mantine_components as dmc
from dash import Dash, ctx
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from biostar.modules.data import ANALOGY_METADATA
from biostar.modules.parsing import (
    find_rollup_nested_component_ids,
    identify_valid_samples,
    unpack_deepdiff_loc,
)


def gen_card(hw: dict) -> dmc.Card:
    """Render a card + modal for configuring rollup hardware"""

    return dmc.Card(
        id={"type": "card-hardware", "index": hw["id"]},
        withBorder=True,
        radius="md",
        py=6,
        my=6,
        px=10,
        children=[
            dmc.Group(
                justify="space-between",
                gap="sm",
                children=[
                    hw["id"],
                    dmc.Tooltip(
                        dmc.ActionIcon(
                            DashIconify(icon="carbon:settings", width=16),
                            id={"type": "button-configure-hardware", "index": hw["id"]},
                            size="md",
                            color="violet",
                            variant="light",
                            n_clicks=0,
                        ),
                        label="Configure hardware element",
                    ),
                ],
            ),
        ],
    )


def attach_callbacks(app: Dash):
    """"""

    @app.callback(
        Output("hierarchy-header", "children"),
        Input("project-diff", "data"),
        State("project-json", "data"),
        prevent_initial_call=True,
    )
    def hierarchy_header(_, project_dict: dict):
        """Populate the hierarchy table header with project name"""

        return project_dict["name"]

    @app.callback(
        Output({"type": "hierarchy", "index": ALL}, "children"),
        Input("hardware-diff", "data"),
        State("hardware-json", "data"),
        State("hardware-prev", "data"),
        State({"type": "hierarchy", "index": ALL}, "children"),
    )
    def hierarchy_table(
        hardware_diff: dict,
        hardware_dict: dict,
        hardware_prev: dict,
        cards_list: list,
    ):
        """Populate the project hierarchy table with cards"""

        update = hardware_diff

        # Skip if hardware hasn't changed
        if not update:
            raise PreventUpdate

        # Case 1: handle batch import or removal of hardware
        if (
            "values_changed" in update
            and len(list(update["values_changed"].keys())) == 1
            and list(update["values_changed"].keys())[0] == "root"
        ):
            cards_list = [[], [], [], [], []]
            for hw in hardware_dict.values():
                cards_list[hw["level"] - 2].append(gen_card(hw))
            return cards_list

        # Case 2: single added hardware elem
        if "dictionary_item_added" in update and len(update["dictionary_item_added"]) == 1:
            update_loc = update["dictionary_item_added"][0]
            hw_id = unpack_deepdiff_loc(update_loc)[0]
            hw_new = hardware_dict[hw_id]
            cards_list[hw_new["level"] - 2].append(gen_card(hw_new))
            if hw_new["parent_id"]:
                parent_id = hw_new["parent_id"]
                level_idx_parent = hw_new["level"] - 3
                card_idx_parent = next(
                    idx
                    for idx, card in enumerate(cards_list[level_idx_parent])
                    if card["props"]["id"]["index"] == parent_id
                )
                cards_list[level_idx_parent][card_idx_parent] = gen_card(hardware_dict[parent_id])
            return cards_list

        # Case 3: removed hardware elem
        if (
            "dictionary_item_removed" in update
            and len(update["dictionary_item_removed"]) == 1
            and "dictionary_item_added" not in update
        ):
            update_loc = update["dictionary_item_removed"][0]
            hw_id = unpack_deepdiff_loc(update_loc)[0]
            hw_del = hardware_prev[hw_id]
            card_idx = next(
                idx
                for idx, card in enumerate(cards_list[hw_del["level"] - 2])
                if card["props"]["id"]["index"] == hw_id
            )
            del cards_list[hw_del["level"] - 2][card_idx]
            return cards_list

        # If none of these cases apply (e.g. patch single element) then skip
        raise PreventUpdate

    @app.callback(
        Output({"type": "card-hardware", "index": ALL}, "styles"),
        Input("hardware-json", "data"),
        prevent_initital_call=True,
    )
    def card_styles(hardware_dict: dict):
        """Style card borders according to rollup vs component and validity"""

        # Determine the target hardware IDs from output
        hw_ids = [x["id"]["index"] for x in ctx.outputs_list]

        # Skip if any of the target hardware no longer in the storage
        # This is to properly handle upload PPEL case when there is existing hardware
        # In these cases the hardware has already been overwritten but the call still executes
        if any([hw_id not in hardware_dict for hw_id in hw_ids]):
            raise PreventUpdate

        def get_card_styles(hw_id):
            hw = hardware_dict[hw_id]
            if hw["is_component"]:
                bd_color = "green-8" if hw["valid"] else "yellow-6"
                bg_color = "green-0" if hw["valid"] else "yellow-0"
                return {
                    "root": {
                        "border": f"2px solid var(--mantine-color-{bd_color})",
                        "backgroundColor": f"var(--mantine-color-{bg_color})",
                    },
                }
            return {
                "root": {
                    "border": "2px dashed var(--mantine-color-gray-6)",
                    "backgroundColor": "var(--mantine-color-gray-0)",
                },
            }

        return [get_card_styles(hw_id) for hw_id in hw_ids]

    app.clientside_callback(
        """
        function(nClicks, currentStyles) {
            if (!nClicks) return window.dash_clientside.no_update;
            const inputsPane = document.getElementById('inputs-pane');
            const newStyles = structuredClone(currentStyles);
            newStyles.content = { width: inputsPane.offsetWidth - 2, height: inputsPane.offsetHeight - 2 };
            return newStyles;
        }
        """,
        Output("modal-configure-hardware", "styles", allow_duplicate=True),
        Input({"type": "button-configure-hardware", "index": ALL}, "n_clicks"),
        State("modal-configure-hardware", "styles"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        """
        function(activeCell, currentStyles) {
            if (!activeCell || activeCell.column_id !== 'Hardware ID') return window.dash_clientside.no_update;
            const inputsPane = document.getElementById('inputs-pane');
            const newStyles = structuredClone(currentStyles);
            newStyles.content = { width: inputsPane.offsetWidth - 2, height: inputsPane.offsetHeight - 2 };
            return newStyles;
        }
        """,
        Output("modal-configure-hardware", "styles", allow_duplicate=True),
        Input("datatable-samples", "active_cell"),
        State("modal-configure-hardware", "styles"),
        prevent_initial_call=True,
    )

    app.clientside_callback(
        """
        function(activeCell, currentStyles) {
            if (!activeCell || activeCell.column_id !== 'Sample ID') return window.dash_clientside.no_update;
            const inputsPane = document.getElementById('inputs-pane');
            const newStyles = structuredClone(currentStyles);
            newStyles.content = { width: inputsPane.offsetWidth - 2, height: inputsPane.offsetHeight - 2 };
            return newStyles;
        }
        """,
        Output("modal-configure-sample", "styles"),
        Input("datatable-samples", "active_cell"),
        State("modal-configure-sample", "styles"),
    )

    app.clientside_callback(
        """
        function(nClicks, currentStyles) {
            if (!nClicks) return window.dash_clientside.no_update;
            const inputsPane = document.getElementById('inputs-pane');
            const newStyles = structuredClone(currentStyles);
            newStyles.content = { width: inputsPane.offsetWidth - 2, height: inputsPane.offsetHeight - 2 };
            return newStyles;
        }
        """,
        Output("modal-configure-project", "styles"),
        Input("button-configure-project", "n_clicks"),
        State("modal-configure-project", "styles"),
    )

    @app.callback(
        Output("datatable-samples", "hidden_columns"),
        Input("checklist-datatable-samples-columns", "value"),
        State("datatable-samples", "columns"),
        prevent_initial_call=True,
    )
    def sample_table_cols(selected_cols: list[str], all_cols: list[dict]):
        """Show/hide columns in the sample table based on user checklist"""

        return [col["id"] for col in all_cols if col["id"] not in selected_cols]

    @app.callback(
        Output("datatable-samples", "style_data_conditional"),
        Input("datatable-samples", "data"),
        Input("select-results-hardware-id", "value"),
        State("hardware-json", "data"),
    )
    def sample_table_style_rows(samples_list: list[dict], tgt_hw_id: str, hardware_dict: dict):
        """Highlight rows that are invalid or not PP accountable"""

        samples_valid = identify_valid_samples(samples_list, hardware_dict)
        invalid_idx = [i for i, s in enumerate(samples_list) if s["Sample ID"] not in samples_valid]
        invalid_rule = (
            [
                {
                    "if": {"row_index": invalid_idx},
                    "color": "var(--mantine-color-red-5)",
                }
            ]
            if invalid_idx
            else []
        )

        if tgt_hw_id == "-- Project --":
            active_hw_ids = find_rollup_nested_component_ids(tgt_hw_id, hardware_dict)
        elif not tgt_hw_id or tgt_hw_id not in hardware_dict:
            active_hw_ids = []
        elif not hardware_dict[tgt_hw_id]["is_component"]:
            active_hw_ids = find_rollup_nested_component_ids(tgt_hw_id, hardware_dict)
        else:
            active_hw_ids = [tgt_hw_id]
        active_idx = [i for i, s in enumerate(samples_list) if s["Hardware ID"] in active_hw_ids]
        active_rule = (
            [{"if": {"row_index": active_idx}, "backgroundColor": "var(--mantine-color-violet-0)"}]
            if active_idx
            else []
        )

        unaccounted_idx = [
            i for i, s in enumerate(samples_list) if s["PP Accountable"].lower() != "yes"
        ]
        unaccounted_rule = (
            [
                {
                    "if": {"row_index": unaccounted_idx},
                    "backgroundColor": "var(--mantine-color-gray-2)",
                }
            ]
            if unaccounted_idx
            else []
        )

        config_rule = [
            {
                "if": {"column_id": ["Sample ID", "Hardware ID"]},
                "color": "var(--mantine-color-blue-5)",
                "cursor": "pointer",
            }
        ]

        return invalid_rule + active_rule + unaccounted_rule + config_rule

    @app.callback(
        Output("modal-table-definitions", "opened", allow_duplicate=True),
        Input("button-table-definitions", "n_clicks"),
        prevent_initial_call=True,
    )
    def table_defs_open_button(_):
        """Open the table definitions modal on Export PPEL tab button click"""

        return True

    @app.callback(
        Output("modal-table-definitions", "opened", allow_duplicate=True),
        Input("link-table-definitions", "n_clicks"),
        prevent_initial_call=True,
    )
    def table_defs_open_link(_):
        """Open the table definitions modal on PPEL import modal link click"""

        return True

    @app.callback(
        Output("modal-table-definitions", "opened", allow_duplicate=True),
        Input("button-table-definitions-close", "n_clicks"),
        prevent_initial_call=True,
    )
    def table_defs_close(_):
        """Close the table definitions modal on button click"""

        return False

    @app.callback(
        Output("analogy-handling", "children"),
        Output("analogy-ventilation", "children"),
        Output("analogy-composition", "children"),
        Output("analogy-notes", "children"),
        Output("analogy-cleaning-fab", "children"),
        Output("analogy-cleaning-pre", "children"),
        Output("analogy-cleaning-sit", "children"),
        Output("analogy-reduction-fab", "children"),
        Output("analogy-reduction-pre", "children"),
        Output("analogy-reduction-sit", "children"),
        Input("select-hardware-analogy", "value"),
        prevent_initial_call=True,
    )
    def analogy_metadata(analogy_id: str):
        """Populate the analogy metadata info using currently selected analogy"""

        defaults = ["-"] * 10
        if analogy_id == "-- Generic --" or analogy_id not in ANALOGY_METADATA:
            return defaults

        return [
            ANALOGY_METADATA[analogy_id][x]
            for x in [
                "handling",
                "ventilation",
                "composition",
                "notes",
                "cleaning-fab",
                "cleaning-pre",
                "cleaning-sit",
                "reduction-fab",
                "reduction-pre",
                "reduction-sit",
            ]
        ]
