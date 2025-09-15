import dash_mantine_components as dmc
from dash import Dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


def attach_callbacks(app: Dash):
    """"""

    @app.callback(
        Output("confirm-configure-hardware-delete", "displayed"),
        Input("button-configure-hardware-delete", "n_clicks"),
        prevent_initial_call=True,
    )
    def hardware_delete(_):
        """Open a confirmation dialog if the user attempts to delete a component"""

        return True

    @app.callback(
        Output("hardware-json", "data", allow_duplicate=True),
        Output("datatable-samples", "data", allow_duplicate=True),
        Output("notifications-hardware", "children", allow_duplicate=True),
        Input("confirm-configure-hardware-delete", "submit_n_clicks"),
        State("select-configure-hardware-id", "value"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def hardware_delete_confirm(_, hw_id: str, hardware_dict: dict, samples_list: list[dict]):
        """Delete a component and associated samples/sims"""

        notifications = []
        hw_del = hardware_dict[hw_id]

        # Delete the hardware ID and associated samples
        del hardware_dict[hw_id]
        samples_list = [s for s in samples_list if s["Hardware ID"] != hw_id]

        # Recheck rollups and convert to components if needed
        # Rollups converted to components should also have group cleared
        if hw_del["parent_id"]:
            hw_siblings = [
                hw for hw in hardware_dict.values() if hw["parent_id"] == hw_del["parent_id"]
            ]
            if not hw_siblings:
                hardware_dict[hw_del["parent_id"]]["is_component"] = True
                hardware_dict[hw_del["parent_id"]].update(
                    {
                        "valid": False,
                        "dim": "2D (Area)",
                        "area": "",
                        "volume": "",
                        "type": None,
                        "analogy": None,
                        "implied_id": None,
                        "spec": None,
                    }
                )
                hardware_dict[hw_del["parent_id"]]["group"] = None
                notifications.append(
                    dmc.Notification(
                        color="yellow",
                        action="show",
                        title="[Hardware] Warning",
                        autoClose=10000,
                        message=f"[{hw_del['parent_id']}] Element coerced from Rollup to Component following removal of '{hw_del['id']}'.",
                    )
                )

        # Update any hardware that was implied from the deleted component
        hw_implied = [hw for hw in hardware_dict.values() if hw["implied_id"] == hw_id]
        for hw_imp in hw_implied:
            hardware_dict[hw_imp["id"]].update({"valid": False, "implied_id": None})

        return hardware_dict, [s for s in samples_list if s["Hardware ID"] != hw_id], notifications

    @app.callback(
        Output("hardware-json", "data", allow_duplicate=True),
        Input("datatable-groups", "data"),
        State("hardware-json", "data"),
        prevent_initial_call=True,
    )
    def groups_delete_cascade(groups_list: list[dict], hardware_dict: dict):
        """Delete references to any groups that no longer exist"""

        # Can skip if all groups still exist
        groups_def = set([g["Group Tag"] for g in groups_list])
        groups_ref = set([hw["group"] for hw in hardware_dict.values() if hw["group"]])
        if groups_def == groups_ref:
            raise PreventUpdate

        # Otherwise clear any hanging group references
        groups_clear = groups_ref.difference(groups_def)
        for hw_id, hw in hardware_dict.items():
            if hw["group"] in groups_clear:
                hardware_dict[hw_id]["group"] = None

        return hardware_dict
