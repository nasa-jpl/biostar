import json
import time

import dash_mantine_components as dmc
from dash import Dash
from dash.dependencies import Input, Output, State
from deepdiff import DeepDiff

from biostar.modules.data import EFFICIENCY_CONFIG
from biostar.modules.parsing import detect_sample_alerts, sample_eff_tag, unpack_deepdiff_loc


def attach_callbacks(app: Dash):
    """"""

    @app.callback(
        Output("groups-diff", "data"),
        Input("datatable-groups", "data"),
        State("groups-prev", "data"),
    )
    def groups_broadcast(groups_list: list[dict], groups_prev: list[dict]):
        """Update groups-diff tracker when a group is edited"""

        update = DeepDiff(
            groups_prev,
            groups_list,
            ignore_type_in_groups=[
                (None, str),
                (str, int),
                (str, float),
                (int, float),
                (None, float),
                (None, int),
            ],
            ignore_order=True,
        )

        return json.loads(update.to_json())

    @app.callback(
        Output("groups-prev", "data"),
        Input("groups-diff", "data"),
        State("datatable-groups", "data"),
    )
    def groups_increment(_, groups_list: list[dict]):
        """Update groups-prev tracker following a round of state updates"""

        return groups_list

    @app.callback(
        Output("hardware-diff", "data"),
        Input("hardware-json", "data"),
        State("hardware-prev", "data"),
    )
    def hardware_broadcast(hardware_dict: dict, hardware_prev: dict):
        """Update hardware-diff tracker when an element is edited"""

        # Identify update operation
        update = DeepDiff(
            hardware_prev,
            hardware_dict,
            ignore_type_in_groups=[
                (None, str),
                (str, int),
                (str, float),
                (int, float),
                (None, float),
                (None, int),
            ],
        )

        return json.loads(update.to_json())

    @app.callback(
        Output("hardware-prev", "data"),
        Input("hardware-diff", "data"),
        State("hardware-json", "data"),
    )
    def hardware_increment_diff(_, hardware_dict: dict):
        """Update hardware-prev tracker following a round of state updates"""

        time.sleep(0.5)

        return hardware_dict

    @app.callback(
        Output("hardware-prev", "data", allow_duplicate=True),
        Input("ppel-wipe-flag", "data"),
        State("hardware-json", "data"),
        prevent_initial_call=True,
    )
    def hardware_increment_wipe(_, hardware_dict: dict):
        """Update hardware-prev tracker following a round of state updates"""

        time.sleep(0.5)

        return hardware_dict

    @app.callback(
        Output("hardware-prev", "data", allow_duplicate=True),
        Input("ppel-import-flag", "data"),
        State("hardware-json", "data"),
        prevent_initial_call=True,
    )
    def hardware_increment_import(_, hardware_dict: dict):
        """Update hardware-prev tracker following a round of state updates"""

        time.sleep(0.5)

        return hardware_dict

    @app.callback(
        Output("samples-diff", "data"),
        Output("notifications-sample-change", "children"),
        Input("datatable-samples", "data"),
        State("samples-prev", "data"),
        State("hardware-json", "data"),
    )
    def samples_broadcast(samples_list: list[dict], samples_prev: list[dict], hardware_dict: dict):
        """Update samples-diff tracker when a sample is edited"""

        def gen_efficiency_warning(s):
            tag = sample_eff_tag(s)
            params = EFFICIENCY_CONFIG[tag]["params"]
            [device_used, device_type_used, processing_technique_used] = params.split(";")
            return f"[{s['Sample ID']}] The recovery efficiency associated with the selected pairing of sampling device and processing technique has not been formally validated. The recovery efficiency applied in the tool’s calculations (for this sample) is based on the {device_type_used} {device_used} and the {processing_technique_used} processing technique."

        # Identify update operation
        update = DeepDiff(
            samples_prev,
            samples_list,
            ignore_type_in_groups=[
                (None, str),
                (str, int),
                (str, float),
                (int, float),
                (None, float),
                (None, int),
            ],
            ignore_order=True,
        )

        # Initialize notifications and define the possible warning/error messages
        notifications = []
        message_map = {
            "area_vol": [
                "error",
                lambda s: f"[{s['Sample ID']}] Invalid area or volume (make sure 2D samples have positive areas and 3D samples have positive volumes)!",
            ],
            "categorical": [
                "error",
                lambda s: f"[{s['Sample ID']}] Could not parse provided 'Sampling Device', 'Sampling Device Type', or 'Processing Technique' into one of the allowed choices!",
            ],
            "efficiency": ["warning", gen_efficiency_warning],
            "fraction": [
                "error",
                lambda s: f"[{s['Sample ID']}] Invalid pour fraction (must be 0 < x <= 1)!",
            ],
            "cfu": [
                "error",
                lambda s: f"[{s['Sample ID']}] Invalid CFU count (must be a nonnegative integer)!",
            ],
        }

        # Case 1: added sample(s)
        if "iterable_item_added" in update:
            for s in update["iterable_item_added"].values():
                status = detect_sample_alerts(s, hardware_dict)
                if status in message_map:
                    [level, message_fn] = message_map[status]
                    notifications.append(
                        dmc.Notification(
                            color="yellow" if level == "warning" else "red",
                            action="show",
                            title=f"[Sample] {level.title()}",
                            autoClose=10000,
                            message=message_fn(s),
                        )
                    )

        # Case 2: edited sample
        if "values_changed" in update:
            update_loc = list(update["values_changed"].keys())[0]
            update_idx, _ = unpack_deepdiff_loc(update_loc)
            s = samples_list[update_idx]
            status = detect_sample_alerts(s, hardware_dict)
            if status in message_map:
                [level, message_fn] = message_map[status]
                notifications.append(
                    dmc.Notification(
                        color="yellow" if level == "warning" else "red",
                        action="show",
                        title=f"[Sample] {level.title()}",
                        autoClose=10000,
                        message=message_fn(s),
                    )
                )

        return json.loads(update.to_json()), notifications

    @app.callback(
        Output("samples-prev", "data"),
        Input("samples-diff", "data"),
        State("datatable-samples", "data"),
    )
    def samples_increment(_, samples_list: list[dict]):
        """Update hardware-prev tracker following a round of state updates"""

        return samples_list

    @app.callback(
        Output("project-diff", "data"),
        Input("project-json", "data"),
        State("project-prev", "data"),
    )
    def project_broadcast(project_dict: dict, project_prev: dict):
        """Update project-diff tracker when the project configuration is edited"""

        update = DeepDiff(
            project_prev,
            project_dict,
            ignore_type_in_groups=[
                (None, str),
                (str, int),
                (str, float),
                (int, float),
                (None, float),
                (None, int),
            ],
            ignore_order=True,
        )

        return json.loads(update.to_json())

    @app.callback(
        Output("project-prev", "data"),
        Input("project-diff", "data"),
        State("project-json", "data"),
    )
    def project_increment(_, project_dict: dict):
        """Update groups-prev tracker following a round of state updates"""

        return project_dict
