import dash_mantine_components as dmc
from dash import Dash
from dash.dependencies import Input, Output, State

from biostar.modules.data import EFFICIENCY_CONFIG, SAMPLING_DEVICE_TYPE_MAP
from biostar.modules.parsing import sample_eff_tag


def attach_callbacks(app: Dash):
    """"""

    @app.callback(
        Output("button-record-group", "disabled"),
        Input("input-group-tag", "value"),
        Input("input-group-density-2d", "value"),
        Input("input-group-density-3d", "value"),
    )
    def group_toggle_button(tag: str, density_2d: int | float, density_3d: int | float):
        """Enable/disable the add target group button depending on if required inputs are supplied"""

        return not (tag and (density_2d or density_3d))

    @app.callback(
        Output("datatable-groups", "data", allow_duplicate=True),
        Output("notifications-group", "children"),
        Output("input-group-tag", "value"),
        Output("input-group-density-2d", "value"),
        Output("input-group-density-3d", "value"),
        Input("button-record-group", "n_clicks"),
        State("datatable-groups", "data"),
        State("input-group-tag", "value"),
        State("input-group-density-2d", "value"),
        State("input-group-density-3d", "value"),
        prevent_initial_call=True,
    )
    def group_record(
        _,
        groups_list: list[dict],
        group_tag: str,
        group_density_2d: int | float,
        group_density_3d: int | float,
    ):
        """Add a new group tag with associated target densities"""

        # If a group under this tag already exists prevent the update and alert user
        if group_tag in [g["Group Tag"] for g in groups_list]:
            notification = dmc.Notification(
                color="red",
                action="show",
                title="[Group] Error",
                autoClose=10000,
                message=f"[{group_tag}] A group with this tag already exists!",
            )
            return groups_list, notification, "", "", ""

        # Construct the new group
        groups_list += [
            {
                "Group Tag": group_tag,
                "Target Density (2D)": group_density_2d if group_density_2d else None,
                "Target Density (3D)": group_density_3d if group_density_3d else None,
            }
        ]

        return groups_list, [], "", "", ""

    @app.callback(
        Output("select-hardware-parent-id", "data"),
        Input("hardware-json", "data"),
        Input("datatable-samples", "data"),
    )
    def hardware_options_parent(hardware_dict: dict, samples_list: list[dict]):
        """Identify the valid options for parent hardware (any L2-L5 hardware not configured as component)"""

        sampled_hardware = [s["Hardware ID"] for s in samples_list]
        hardware = [
            hw["id"]
            for hw in hardware_dict.values()
            if hw["level"] <= 5 and hw["id"] not in sampled_hardware
        ]
        return [{"label": opt, "value": opt} for opt in hardware]

    @app.callback(
        Output("button-record-hardware", "disabled"),
        Input("input-hardware-id", "value"),
    )
    def hardware_toggle_button(
        hardware_id: str,
    ):
        """Enable/disable the add hardware button depending on if required inputs are supplied"""

        return not bool(hardware_id)

    @app.callback(
        Output("hardware-json", "data", allow_duplicate=True),
        Output("notifications-hardware", "children", allow_duplicate=True),
        Input("button-record-hardware", "n_clicks"),
        State("hardware-json", "data"),
        State("input-hardware-id", "value"),
        State("select-hardware-parent-id", "value"),
        prevent_initial_call=True,
    )
    def hardware_record(
        _,
        hardware_dict: dict,
        hw_id: str,
        hw_parent_id: str,
    ):
        """Add a new hardware to the session storage and identify components (leaf nodes)"""

        # If a group under this tag already exists prevent the update and alert user
        if hw_id in hardware_dict:
            notification = dmc.Notification(
                color="red",
                action="show",
                title="[Hardware] Error",
                autoClose=10000,
                message=f"[{hw_id}] A hardware element with this ID already exists!",
            )
            return hardware_dict, notification

        # Determine level of the new component
        level = (
            2
            if not hw_parent_id
            else next(filter(lambda hw: hw["id"] == hw_parent_id, hardware_dict.values()))["level"]
            + 1
        )

        # Construct the new row
        hardware_dict[hw_id] = {
            "id": hw_id,
            "parent_id": hw_parent_id,
            "level": level,
            "group": None,
            "is_component": True,
            "valid": False,
            "dim": "2D (Area)",
            "area": "",
            "volume": "",
            "type": None,
            "analogy": None,
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

        # Identify which hardware elements are components (leaf nodes)
        parents = set()
        for hw in hardware_dict.values():
            parent_id = hw.get("parent_id")
            if parent_id is not None:
                parents.add(parent_id)
        leaves = set(hardware_dict.keys()).difference(parents)

        # Mark hardware as components if needed
        # If hardware was a component and now is not then make sure to clear all component inputs
        notifications = []
        for hw_id_other in hardware_dict:
            was_component = hardware_dict[hw_id_other]["is_component"]
            is_component = hw_id_other in leaves
            hardware_dict[hw_id_other]["is_component"] = is_component
            if was_component and not is_component:
                hardware_dict[hw_id_other].update(
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
                notifications.append(
                    dmc.Notification(
                        color="yellow",
                        action="show",
                        title="[Hardware] Warning",
                        autoClose=10000,
                        message=f"[{hw_id_other}] Element coerced from Component to Rollup following addition of '{hw_id}'.",
                    )
                )

        return hardware_dict, notifications

    @app.callback(
        Output("select-sample-hardware-id", "data"),
        Input("hardware-json", "data"),
    )
    def sample_options_hardware(hardware_dict: dict):
        """Identify the available component ID options for samples"""

        eligible_hw = [
            hw for hw in hardware_dict.values() if hw["valid"] and hw["type"] == "Sampled"
        ]
        levels = sorted(set([hw["level"] for hw in eligible_hw]))

        options = []
        for level in levels:
            options.append(
                {
                    "group": f"L{level}",
                    "items": [
                        {"value": hw["id"], "label": hw["id"]}
                        for hw in filter(lambda hw: hw["level"] == level, eligible_hw)
                    ],
                }
            )

        return options

    @app.callback(
        Output("select-sample-device-type", "data"),
        Input("select-sample-device", "value"),
        prevent_initial_call=True,
    )
    def sample_options_device_type(samp_device: str):
        """Update the sampling device type options when user toggles swab vs wipe"""

        if not samp_device or samp_device not in SAMPLING_DEVICE_TYPE_MAP:
            return []

        return [{"label": opt, "value": opt} for opt in SAMPLING_DEVICE_TYPE_MAP[samp_device]]

    @app.callback(
        Output("input-sample-fraction", "value"),
        Input("select-sample-device", "value"),
        Input("select-sample-device-type", "value"),
        Input("select-sample-technique", "value"),
        prevent_initial_call=True,
    )
    def sample_autofill_fraction(samp_device: str, samp_device_type: str, samp_technique: str):
        """Supply a default pour fraction based on the device, type, and technique"""

        tag = sample_eff_tag(
            {
                "Sampling Device": samp_device,
                "Sampling Device Type": samp_device_type,
                "Processing Technique": samp_technique,
            }
        )
        if tag not in EFFICIENCY_CONFIG:
            return 1

        return EFFICIENCY_CONFIG[tag]["default_fraction"]

    @app.callback(
        Output("input-sample-area-volume", "label"),
        Input("select-sample-hardware-id", "value"),
        State("hardware-json", "data"),
        prevent_initial_call=True,
    )
    def sample_label_area_vol(hw_id: str, hardware_dict: dict):
        """Display the correct area/volume label depending on hardware element"""

        base = "Sampled Area (m²)"
        if not hw_id:
            return base

        hw = hardware_dict[hw_id]

        return base if hw["dim"].startswith("2") else "Sampled Volume (cm³)"

    @app.callback(
        Output("button-record-sample", "disabled"),
        Input("input-sample-id", "value"),
        Input("select-sample-hardware-id", "value"),
        Input("select-sample-accountable", "value"),
        Input("select-sample-device", "value"),
        Input("select-sample-device-type", "value"),
        Input("select-sample-technique", "value"),
        Input("input-sample-fraction", "value"),
        Input("input-sample-area-volume", "value"),
        Input("input-sample-cfu", "value"),
        prevent_initial_call=True,
    )
    def sample_toggle_button(*args):
        """Enable/disable the add sample button depending on if required inputs are supplied"""

        non_cfu_valid = all(args[:-1])
        cfu_valid = args[-1] is not None

        return not (non_cfu_valid and cfu_valid)

    @app.callback(
        Output("datatable-samples", "data", allow_duplicate=True),
        Output("notifications-sample-add", "children"),
        Input("button-record-sample", "n_clicks"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        State("input-sample-id", "value"),
        State("select-sample-hardware-id", "value"),
        State("select-sample-accountable", "value"),
        State("select-sample-device", "value"),
        State("select-sample-device-type", "value"),
        State("select-sample-technique", "value"),
        State("input-sample-fraction", "value"),
        State("input-sample-area-volume", "value"),
        State("input-sample-cfu", "value"),
        State("input-sample-assay-name", "value"),
        State("input-sample-assay-date", "value"),
        State("input-sample-pp-cert", "value"),
        State("select-sample-control", "value"),
        State("input-sample-notes", "value"),
        prevent_initial_call=True,
    )
    def sample_record(
        _,
        hardware_dict: dict,
        samples_list: list[dict],
        samp_id: str,
        samp_hw_id: str,
        samp_accountable: str,
        samp_device: str,
        samp_device_type: str,
        samp_technique: str,
        samp_fraction: int | float,
        samp_area_vol: int | float,
        samp_cfu: int,
        samp_assay_name: str,
        samp_assay_date: str,
        samp_pp_cert: str,
        samp_control: str,
        samp_notes: str,
    ):
        """Add a new sample to table storage"""

        # If a sample under this tag already exists prevent the update and alert user
        existing_samples = [s["Sample ID"] for s in samples_list]
        if samp_id in existing_samples:
            notification = dmc.Notification(
                color="red",
                action="show",
                title="[Sample] Error",
                autoClose=10000,
                message=f"[{samp_id}] A sample with this ID already exists!",
            )
            return samples_list, notification

        # Get the associated component, hardware, and group info
        hw = hardware_dict[samp_hw_id]

        # Construct the new row
        row = {
            "Sample ID": samp_id,
            "Hardware ID": hw["id"],
            "PP Accountable": samp_accountable,
            "Sampled Area": samp_area_vol if hw["dim"].startswith("2") else None,
            "Sampled Volume": samp_area_vol if hw["dim"].startswith("3") else None,
            "Sampling Device": samp_device,
            "Sampling Device Type": samp_device_type,
            "Processing Technique": samp_technique,
            "Pour Fraction": samp_fraction,
            "CFU": samp_cfu,
            "Assay Name": samp_assay_name,
            "Assay Date": samp_assay_date,
            "PP Cert #": samp_pp_cert,
            "Control Type": samp_control,
            "Sampling Notes": samp_notes,
        }

        return samples_list + [row], []
