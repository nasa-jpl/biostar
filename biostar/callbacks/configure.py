import dash_mantine_components as dmc
from dash import Dash, ctx
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from biostar.modules.data import (
    ANALOGY_COMPONENTS_AREAS,
    ANALOGY_COMPONENTS_VOLUMES,
    ANALOGY_TREE_AREAS,
    ANALOGY_TREE_VOLUMES,
    EFFICIENCY_CONFIG,
    SAMPLING_DEVICE_TYPE_MAP,
    SPEC_DENSITY_MAP,
    SPEC_ISO_CLASSES,
    find_by_key,
)
from biostar.modules.parsing import sample_eff_tag


def attach_callbacks(app: Dash):
    """"""

    @app.callback(
        Output("select-configure-hardware-id", "value", allow_duplicate=True),
        Output("modal-configure-hardware", "opened", allow_duplicate=True),
        Input({"type": "button-configure-hardware", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def hardware_config_open_hier(n_clicks: list[int]):
        """Open the configure hardware modal and autofill hardware ID on card button click"""

        if len(ctx.inputs_list[0]) == 1:
            if not n_clicks or not n_clicks[0]:
                raise PreventUpdate
        elif len(ctx.inputs_list[0]) == len(ctx.triggered_prop_ids):
            raise PreventUpdate

        return ctx.triggered_id["index"], True

    @app.callback(
        Output("select-configure-hardware-id", "value", allow_duplicate=True),
        Output("modal-configure-hardware", "opened", allow_duplicate=True),
        Input("datatable-samples", "active_cell"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def hardware_config_open_table(active_cell: dict, samples_list: list[dict]):
        """Open the configure hardware modal and autofill hardware ID on hardware ID cell click"""

        if active_cell is None or active_cell["column_id"] != "Hardware ID":
            raise PreventUpdate

        hw_id = samples_list[active_cell["row"]]["Hardware ID"]

        return hw_id, True

    @app.callback(
        Output("modal-configure-hardware", "opened", allow_duplicate=True),
        Output("select-configure-hardware-id", "value", allow_duplicate=True),
        Input("button-configure-hardware-close", "n_clicks"),
        Input("confirm-configure-hardware-delete", "submit_n_clicks"),
        prevent_initial_call=True,
    )
    def hardware_config_close(*_):
        """Close the configure hardware modal and reset ID on close button click"""

        return False, None

    @app.callback(
        Output("select-configure-hardware-id", "data"),
        Input("hardware-json", "data"),
    )
    def hardware_config_target(hw_all: dict):
        """Update allowed options for configuration target when hardware changes"""

        return list(hw_all.keys())

    @app.callback(
        Output("select-hardware-dim", "label"),
        Output("select-hardware-type", "label"),
        Output("container-inputs-component", "style"),
        Output("select-hardware-dim", "disabled"),
        Output("select-hardware-type", "disabled"),
        Output("button-configure-hardware-delete", "disabled"),
        Output("select-hardware-group", "data", allow_duplicate=True),
        Output("select-hardware-group", "value"),
        Output("select-hardware-dim", "value"),
        Output("input-hardware-area-volume", "value"),
        Output("select-hardware-type", "value"),
        Output("select-hardware-analogy", "value", allow_duplicate=True),
        Output("select-hardware-implied-id", "value", allow_duplicate=True),
        Output("select-hardware-spec", "value", allow_duplicate=True),
        Output("input-hardware-handling", "value"),
        Output("input-hardware-ventilation", "value"),
        Output("input-hardware-composition", "value"),
        Output("input-hardware-cleaning-fab", "value"),
        Output("input-hardware-cleaning-pre", "value"),
        Output("input-hardware-cleaning-sit", "value"),
        Output("input-hardware-reduction-fab", "value"),
        Output("input-hardware-reduction-pre", "value"),
        Output("input-hardware-reduction-sit", "value"),
        Output("input-hardware-notes", "value"),
        Input("select-configure-hardware-id", "value"),
        State("datatable-groups", "data"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def hardware_config_state_id(
        hw_id: str, groups_list: list[dict], hardware_dict: dict, samples_list: list[dict]
    ):
        """Update state (values, options, visibility) of inputs based on selected hardware ID"""

        labels = ["Component Dimensionality", "Component Type"]
        styles = [{"display": "none"}]
        disableds = [False, False, True]
        data = [[]]
        values = [None, None, "", None, None, None, None, "", "", "", "", "", "", "", "", "", ""]

        if not hw_id or hw_id not in hardware_dict:
            return labels + styles + disableds + data + values

        hw = hardware_dict[hw_id]
        styles = [{"display": "none"}] if not hw["is_component"] else [{}]
        disableds[2] = not hw["is_component"]

        if find_by_key(samples_list, "Hardware ID", hw_id):
            labels[0] = dmc.Flex(
                justify="start",
                align="center",
                gap=4,
                children=[
                    "Component Dimensionality",
                    dmc.Tooltip(
                        DashIconify(
                            icon="material-symbols-light:indeterminate-question-box-rounded",
                            width=20,
                        ),
                        label="This input is locked since the selected hardware has recorded samples in the database!",
                        boxWrapperProps={"style": {"display": "flex"}},
                    ),
                ],
            )
            labels[1] = dmc.Flex(
                justify="start",
                align="center",
                gap=4,
                children=[
                    "Component Type",
                    dmc.Tooltip(
                        DashIconify(
                            icon="material-symbols-light:indeterminate-question-box-rounded",
                            width=20,
                        ),
                        label="This input is locked since the selected hardware has recorded samples in the database!",
                        boxWrapperProps={"style": {"display": "flex"}},
                    ),
                ],
            )
            disableds[0] = True
            disableds[1] = True

        data = [
            [
                g["Group Tag"]
                for g in list(filter(lambda g: g[f"Target Density ({hw['dim'][0]}D)"], groups_list))
            ]
            if hw["is_component"]
            else [g["Group Tag"] for g in groups_list]
        ]

        values = [
            hw["group"],
            hw["dim"],
            hw["area"] if hw["dim"].startswith("2") else hw["volume"],
            hw["type"],
            hw["analogy"],
            hw["implied_id"],
            hw["spec"],
            hw["handling"],
            hw["ventilation"],
            hw["composition"],
            hw["cleaning_fab"],
            hw["cleaning_pre"],
            hw["cleaning_sit"],
            hw["reduction_fab"],
            hw["reduction_pre"],
            hw["reduction_sit"],
            hw["notes"],
        ]

        return labels + styles + disableds + data + values

    @app.callback(
        Output("container-inputs-sampled", "style"),
        Output("container-inputs-implied", "style"),
        Output("container-inputs-spec", "style"),
        Output("input-hardware-area-volume", "label"),
        Output("select-hardware-group", "data", allow_duplicate=True),
        Output("select-hardware-analogy", "data"),
        Output("tree-hardware-analogy", "data"),
        Output("select-hardware-implied-id", "data"),
        Output("select-hardware-spec", "data"),
        Output("select-hardware-analogy", "value", allow_duplicate=True),
        Output("select-hardware-implied-id", "value", allow_duplicate=True),
        Output("select-hardware-spec", "value", allow_duplicate=True),
        Input("select-hardware-type", "value"),
        Input("select-hardware-dim", "value"),
        State("select-configure-hardware-id", "value"),
        State("datatable-groups", "data"),
        State("hardware-json", "data"),
        prevent_initial_call=True,
    )
    def hardware_config_state_type_dim(
        hw_type: str, hw_dim: str, hw_id: str, groups_list: list[dict], hardware_dict: dict
    ):
        """Update state (values, options, visibility) of inputs based on selected type and dim"""

        type_idx_map = {
            "Sampled": 0,
            "Unsampled - Implied": 1,
            "Unsampled - Spec": 2,
        }
        type_attr_map = {
            "Sampled": "analogy",
            "Unsampled - Implied": "implied_id",
            "Unsampled - Spec": "spec",
        }

        # Define default styles and values
        styles = [{"display": "none"}] * 3
        labels = (
            ["Total Area (m²)"] if not hw_dim or hw_dim.startswith("2") else ["Total Volume (cm³)"]
        )
        data = [[], [], [], [], SPEC_ISO_CLASSES["2D (Area)"]]
        values = [None] * 3

        # Provide group options regardless of type
        if hw_id:
            data[0] = (
                [g["Group Tag"] for g in groups_list if g[f"Target Density ({hw_dim[0]}D)"]]
                if hardware_dict[hw_id]["is_component"]
                else [g["Group Tag"] for g in groups_list]
            )

        # Handle blank type
        if not hw_type:
            return styles + labels + data + values

        # Determine relevant styles
        styles[type_idx_map[hw_type]] = {}

        # Determine relevant input options
        if hw_type == "Sampled":
            data[1] = ["-- Generic --"] + (
                ANALOGY_COMPONENTS_AREAS if hw_dim.startswith("2") else ANALOGY_COMPONENTS_VOLUMES
            )
            data[2] = ANALOGY_TREE_AREAS if hw_dim.startswith("2") else ANALOGY_TREE_VOLUMES
        elif hw_type == "Unsampled - Implied":
            data[3] = [
                hw["id"]
                for hw in hardware_dict.values()
                if hw["valid"] and hw["type"] == "Sampled" and hw["dim"] == hw_dim
            ]
        elif hw_type == "Unsampled - Spec":
            data[4] = SPEC_ISO_CLASSES[hw_dim]

        # Identify relevant input values
        if hw_id and hardware_dict[hw_id]["dim"] == hw_dim:
            values[type_idx_map[hw_type]] = hardware_dict[hw_id][type_attr_map[hw_type]]

        return styles + labels + data + values

    @app.callback(
        Output("input-hardware-group-density-2d", "value"),
        Output("input-hardware-group-density-3d", "value"),
        Input("select-hardware-group", "value"),
        State("datatable-groups", "data"),
        prevent_initial_call=True,
    )
    def hardware_config_group_density(hw_group: str, groups_list: list[dict]):
        """Autofill spec density based on selected spec class"""

        # If target group not selected ensure density is blank too
        if not hw_group:
            return "", ""

        # Extract the group object and determine correct density label
        group = find_by_key(groups_list, "Group Tag", hw_group)
        density_2d = group["Target Density (2D)"]
        density_3d = group["Target Density (3D)"]

        return density_2d if density_2d else "", density_3d if density_3d else ""

    @app.callback(
        Output("input-hardware-spec-density", "value"),
        Input("select-hardware-spec", "value"),
        State("select-hardware-dim", "value"),
        prevent_initial_call=True,
    )
    def hardware_config_autofill_spec(hw_spec: str, hw_dim: str):
        """Autofill spec density based on selected spec class"""

        if not hw_spec:
            return ""

        return SPEC_DENSITY_MAP[hw_dim][hw_spec]

    @app.callback(
        Output("hardware-json", "data", allow_duplicate=True),
        Input("button-configure-hardware-apply", "n_clicks"),
        State("hardware-json", "data"),
        State("select-configure-hardware-id", "value"),
        State("select-hardware-group", "value"),
        State("select-hardware-dim", "value"),
        State("input-hardware-area-volume", "value"),
        State("select-hardware-type", "value"),
        State("select-hardware-analogy", "value"),
        State("select-hardware-implied-id", "value"),
        State("select-hardware-spec", "value"),
        State("input-hardware-handling", "value"),
        State("input-hardware-ventilation", "value"),
        State("input-hardware-composition", "value"),
        State("input-hardware-cleaning-fab", "value"),
        State("input-hardware-cleaning-pre", "value"),
        State("input-hardware-cleaning-sit", "value"),
        State("input-hardware-reduction-fab", "value"),
        State("input-hardware-reduction-pre", "value"),
        State("input-hardware-reduction-sit", "value"),
        State("input-hardware-notes", "value"),
        prevent_initial_call=True,
    )
    def hardware_config_apply(
        _,
        hardware_dict: dict,
        hw_id: str,
        hw_group: str,
        hw_dim: str,
        hw_area_vol: int | float,
        hw_type: str,
        hw_analogy: str,
        hw_implied_id: str,
        hw_spec: str,
        hw_handling: str,
        hw_ventilation: str,
        hw_composition: str,
        hw_cleaning_fab: str,
        hw_cleaning_pre: str,
        hw_cleaning_sit: str,
        hw_reduction_fab: int | float,
        hw_reduction_pre: int | float,
        hw_reduction_sit: int | float,
        hw_notes: str,
    ):
        """Apply changes to hardware storage"""

        # Patch the entry with the current configuration values
        hardware_dict[hw_id].update(
            {
                "group": hw_group,
                "dim": hw_dim,
                "area": hw_area_vol if hw_dim.startswith("2") else "",
                "volume": hw_area_vol if hw_dim.startswith("3") else "",
                "type": hw_type,
                "analogy": hw_analogy,
                "implied_id": hw_implied_id,
                "spec": hw_spec,
                "handling": hw_handling,
                "ventilation": hw_ventilation,
                "composition": hw_composition,
                "cleaning_fab": hw_cleaning_fab,
                "cleaning_pre": hw_cleaning_pre,
                "cleaning_sit": hw_cleaning_sit,
                "reduction_fab": hw_reduction_fab,
                "reduction_pre": hw_reduction_pre,
                "reduction_sit": hw_reduction_sit,
                "notes": hw_notes,
            }
        )

        # Re-check valididity for components
        valid = all([hw_dim, hw_area_vol, hw_type])
        if valid and hardware_dict[hw_id]["is_component"]:
            if hw_type == "Sampled":
                valid = bool(hw_analogy)
            elif hw_type == "Unsampled - Implied":
                valid = bool(hw_implied_id)
            elif hw_type == "Unsampled - Spec":
                valid = bool(hw_spec)
        hardware_dict[hw_id]["valid"] = valid

        return hardware_dict

    @app.callback(
        Output("select-configure-sample-id", "value", allow_duplicate=True),
        Output("select-configure-sample-hardware-id", "value", allow_duplicate=True),
        Output("modal-configure-sample", "opened", allow_duplicate=True),
        Input("datatable-samples", "active_cell"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def sample_config_open(active_cell: dict, samples_list: list[dict]):
        """Open the configure hardware modal and autofill hardware ID on hardware ID cell click"""

        if active_cell is None or active_cell["column_id"] != "Sample ID":
            raise PreventUpdate

        sample = samples_list[active_cell["row"]]
        sample_id = sample["Sample ID"]
        hw_id = sample["Hardware ID"]

        return sample_id, hw_id, True

    @app.callback(
        Output("modal-configure-sample", "opened", allow_duplicate=True),
        Output("select-configure-sample-id", "value", allow_duplicate=True),
        Output("select-configure-sample-hardware-id", "value", allow_duplicate=True),
        Input("button-configure-sample-close", "n_clicks"),
        prevent_initial_call=True,
    )
    def sample_config_close(_):
        """Close the configure sample modal and reset ID on close button click"""

        return False, None, None

    @app.callback(
        Output("select-configure-sample-id", "data"),
        Output("select-configure-sample-hardware-id", "data"),
        Input("hardware-json", "data"),
        Input("datatable-samples", "data"),
    )
    def sample_config_target(hw_dict: dict, samples_list: list[dict]):
        """Update allowed options for configuration target IDs when hardware changes"""

        sample_options = [s["Sample ID"] for s in samples_list]
        hw_options = list(hw_dict.keys())

        return sample_options, hw_options

    @app.callback(
        Output("input-configure-sample-area-volume", "label"),
        Output("select-configure-sample-accountable", "value"),
        Output("select-configure-sample-device", "value"),
        Output("select-configure-sample-device-type", "value"),
        Output("select-configure-sample-technique", "value"),
        Output("input-configure-sample-fraction", "value", allow_duplicate=True),
        Output("input-configure-sample-area-volume", "value"),
        Output("input-configure-sample-cfu", "value"),
        Output("input-configure-sample-assay-name", "value"),
        Output("input-configure-sample-assay-date", "value"),
        Output("input-configure-sample-pp-cert", "value"),
        Output("select-configure-sample-control", "value"),
        Output("input-configure-sample-notes", "value"),
        Input("select-configure-sample-id", "value"),
        State("select-configure-sample-hardware-id", "value"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def sample_config_state_id(
        sample_id: str, hw_id: str, hardware_dict: dict, samples_list: list[dict]
    ):
        """Update state (values, options, visibility) of inputs based on selected hardware ID"""

        labels = ["Sampled Area (m²)"]

        values = [
            "Yes",
            "Swab",
            "Puritan Cotton",
            "NASA Standard",
            1,
            None,
            None,
            "",
            "",
            "",
            "No",
            "",
        ]
        if not (sample_id and hw_id) or hw_id not in hardware_dict:
            return labels + values

        hw = hardware_dict[hw_id]
        if hw["dim"].startswith("3"):
            labels[0] = "Sampled Volume (cm³)"

        sample = find_by_key(samples_list, "Sample ID", sample_id)

        values = [
            sample["PP Accountable"],
            sample["Sampling Device"],
            sample["Sampling Device Type"],
            sample["Processing Technique"],
            sample["Pour Fraction"],
            sample["Sampled Volume"] if hw["dim"].startswith("3") else sample["Sampled Area"],
            sample["CFU"],
            sample["Assay Name"],
            sample["Assay Date"],
            sample["PP Cert #"],
            sample["Control Type"],
            sample["Sampling Notes"],
        ]

        return labels + values

    @app.callback(
        Output("button-configure-sample-apply", "disabled"),
        Input("select-configure-sample-id", "value"),
        Input("select-configure-sample-hardware-id", "value"),
        Input("input-configure-sample-assay-date", "value"),
        Input("select-configure-sample-accountable", "value"),
        Input("select-configure-sample-device", "value"),
        Input("select-configure-sample-device-type", "value"),
        Input("select-configure-sample-technique", "value"),
        Input("input-configure-sample-fraction", "value"),
        Input("input-configure-sample-area-volume", "value"),
        Input("input-configure-sample-cfu", "value"),
    )
    def sample_config_toggle_button(*args):
        """Enable/disable the apply changes button depending on if required inputs are supplied"""

        non_cfu_valid = all(args[:-1])
        cfu_valid = args[-1] is not None

        return not (non_cfu_valid and cfu_valid)

    @app.callback(
        Output("select-configure-sample-device-type", "data"),
        Input("select-configure-sample-device", "value"),
        prevent_initial_call=True,
    )
    def sample_config_options_device_type(sample_device: str):
        """Update the sampling device type options when user toggles swab vs wipe"""

        if not sample_device or sample_device not in SAMPLING_DEVICE_TYPE_MAP:
            return []

        return [{"label": opt, "value": opt} for opt in SAMPLING_DEVICE_TYPE_MAP[sample_device]]

    @app.callback(
        Output("input-configure-sample-fraction", "value", allow_duplicate=True),
        Input("select-configure-sample-id", "value"),
        Input("select-configure-sample-device", "value"),
        Input("select-configure-sample-device-type", "value"),
        Input("select-configure-sample-technique", "value"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def sample_config_autofill_fraction(
        samp_id: str,
        samp_device: str,
        samp_device_type: str,
        samp_technique: str,
        samples_list: list[dict],
    ):
        """Supply a default pour fraction based on the device, type, and technique"""

        if "select-configure-sample-id.value" in ctx.triggered_prop_ids:
            samp = find_by_key(samples_list, "Sample ID", samp_id)
            return samp["Pour Fraction"] if samp else ""

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
        Output("datatable-samples", "data", allow_duplicate=True),
        Input("button-configure-sample-apply", "n_clicks"),
        State("select-configure-sample-id", "value"),
        State("select-configure-sample-hardware-id", "value"),
        State("select-configure-sample-accountable", "value"),
        State("select-configure-sample-device", "value"),
        State("select-configure-sample-device-type", "value"),
        State("select-configure-sample-technique", "value"),
        State("input-configure-sample-fraction", "value"),
        State("input-configure-sample-area-volume", "value"),
        State("input-configure-sample-cfu", "value"),
        State("input-configure-sample-assay-name", "value"),
        State("input-configure-sample-assay-date", "value"),
        State("input-configure-sample-pp-cert", "value"),
        State("select-configure-sample-control", "value"),
        State("input-configure-sample-notes", "value"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def sample_config_apply(
        _,
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
        hardware_dict: dict,
        samples_list: list[dict],
    ):
        """Apply changes to sample storage"""

        hw = hardware_dict[samp_hw_id]

        sample_idx = [i for i, s in enumerate(samples_list) if s["Sample ID"] == samp_id][0]
        samples_list[sample_idx].update(
            {
                "PP Accountable": samp_accountable,
                "Sampling Device": samp_device,
                "Sampling Device Type": samp_device_type,
                "Processing Technique": samp_technique,
                "Pour Fraction": samp_fraction,
                ("Sampled Area" if hw["dim"].startswith("2") else "Sampled Volume"): samp_area_vol,
                "CFU": samp_cfu,
                "Assay Name": samp_assay_name,
                "Assay Date": samp_assay_date,
                "PP Cert #": samp_pp_cert,
                "Control Type": samp_control,
                "Sampling Notes": samp_notes,
            }
        )

        return samples_list

    @app.callback(
        Output("modal-configure-project", "opened"),
        Input("button-configure-project", "n_clicks"),
        prevent_initial_call=True,
    )
    def project_config_open(_):
        """Open the project configuration modal"""

        return True

    @app.callback(
        Output("modal-configure-project", "opened", allow_duplicate=True),
        Input("button-configure-project-close", "n_clicks"),
        prevent_initial_call=True,
    )
    def project_config_close(_):
        """Close the configure project modal"""

        return False

    @app.callback(
        Output("button-configure-project-apply", "disabled"),
        Input("input-project-name", "value"),
    )
    def project_config_toggle_button(name: str):
        """Enable/disable the apply changes button depending on if required inputs are supplied"""

        return not name

    @app.callback(
        Output("select-project-group", "data"),
        Input("datatable-groups", "data"),
        prevent_initial_call=True,
    )
    def project_config_options_group(groups_list: list[dict]):
        """Identify the valid options for target group of projects"""

        if not groups_list:
            return []

        return [g["Group Tag"] for g in groups_list]

    @app.callback(
        Output("input-project-name", "value"),
        Output("select-project-group", "value"),
        Input("project-diff", "data"),
        State("project-json", "data"),
    )
    def project_config_state(_, project_dict: dict):
        """Fill project configuration state when project-json changes (e.g. on PPEL upload)"""

        return project_dict["name"], project_dict["group"]

    @app.callback(
        Output("input-project-density-2d", "value"),
        Output("input-project-density-3d", "value"),
        Input("select-project-group", "value"),
        State("datatable-groups", "data"),
        prevent_initial_call=True,
    )
    def project_config_autofill_density(group_tag: str, groups_list: list[dict]):
        """Autofill the target density for rollup hardware based on group choice"""

        # If target group not selected ensure density is blank too
        if not group_tag:
            return "", ""

        # Extract the group object and return each density
        group = find_by_key(groups_list, "Group Tag", group_tag)
        return group["Target Density (2D)"], group["Target Density (3D)"]

    @app.callback(
        Output("project-json", "data"),
        Input("button-configure-project-apply", "n_clicks"),
        State("input-project-name", "value"),
        State("select-project-group", "value"),
        prvent_initial_call=True,
    )
    def project_config_apply(_, project_name: str, project_group: str):
        """Apply changes to project storage"""

        return {
            "name": project_name,
            "group": project_group,
        }
