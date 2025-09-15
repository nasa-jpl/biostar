from functools import reduce

import dash_mantine_components as dmc
import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from dash import Dash, ctx
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from biostar.modules.data import (
    HARDWARE_METADATA_COLUMNS,
    POSTERIOR_MAP,
    PPEL_TABLE_METADATA_COLUMNS,
    SAMPLE_TABLE_METADATA_COLUMNS,
    SPEC_DENSITY_MAP,
    find_by_key,
)
from biostar.modules.display import BASE_GRAPH_FIG, BASE_GRAPH_LAYOUT, COLOR_SEQUENCE
from biostar.modules.parsing import (
    find_eligible_hardware_ids,
    find_implied_hardware,
    find_rollup_nested_component_ids,
    identify_valid_samples,
    reduce_deefdiff_edits,
    unpack_deepdiff_loc,
)
from biostar.modules.update import sim_component


def create_ppel_sort_key(hardware_dict: dict):
    """Create a sort key to order PPEL rows correctly"""

    def get_ancestry_path(hw_id):
        """Helper function to get the ancestry path from root to current node"""

        path = []
        current_id = hw_id

        while current_id:
            path.append(current_id)
            current_id = hardware_dict[current_id]["parent_id"]

        # Reverse to get root->leaf order
        return path[::-1]

    def sort_key(ppel_row):
        """
        Creates a tuple key for sorting that places children immediately after parents.
        Each element in the key tuple represents a level in the hierarchy.
        """

        hw_id = ppel_row["Hardware ID"]
        ancestry_path = get_ancestry_path(hw_id)

        # Create the sorting key as a tuple of positions at each level
        key = []
        for i, ancestor_id in enumerate(ancestry_path):
            # Find all siblings at this level (items with the same parent)
            parent_id = hardware_dict[ancestor_id]["parent_id"]
            siblings = [hw["id"] for hw in hardware_dict.values() if hw["parent_id"] == parent_id]
            # Sort siblings consistently
            siblings.sort()
            # Add the position in the siblings list to the key
            key.append(siblings.index(ancestor_id))

        return tuple(key)

    return sort_key


def assessment_text(pct: str | None):
    """Generate the appropriate text for hardware assessment result alert"""

    if pct is None:
        return "No target density provided for hardware assessment"
    return f"Target density satisfied for {round(pct * 100, 1)}% of simulations"


def sampled_component_results(
    hw: dict, samples_list: list[dict], sim: dict, density: float | int | None
):
    """Generate result elements for sampled components"""

    # Get density units first to include in fig annotations
    density_units = "spores / m²" if hw["dim"].startswith("2") else "spores / cm³"

    # Construct bioburden density figure
    analogy_draws = [] if hw["analogy"] == "-- Generic --" else [POSTERIOR_MAP[sim["link"]]]
    analogy_name = [] if hw["analogy"] == "-- Generic --" else ["Analogy"]
    lambda_draws = [sim["lambda"]] if sim["mode"] == "posterior" else []
    lambda_name = [hw["id"]] if sim["mode"] == "posterior" else []
    fig_lambda = ff.create_distplot(
        analogy_draws + lambda_draws,
        analogy_name + lambda_name,
        show_hist=False,
        colors=COLOR_SEQUENCE if hw["analogy"] != "-- Generic --" else COLOR_SEQUENCE[1:],
    )
    fig_lambda.update_layout(BASE_GRAPH_LAYOUT)
    fig_lambda.update_layout(
        title="Estimated Bioburden Density",
        xaxis=dict(title=f"Bioburden Density ({density_units})"),
        yaxis=dict(title="Probability Density", showexponent="all", exponentformat="e"),
    )
    fig_lambda.update_traces(
        hovertemplate="<b>Bioburden Density</b>: %{x:.3f}"
        + f" {density_units}"
        + "<br><b>Probability Density</b>: %{y:.6f}<extra></extra>",
        selector=dict(type="scatter", mode="lines"),
    )
    fig_lambda.update_traces(
        hovertemplate="<b>Bioburden Density</b>: %{x:.3f}" + f" {density_units}<extra></extra>",
        selector=dict(type="scatter", mode="markers"),
    )

    # Construct CFU figure
    fig_cfu = go.Figure(
        go.Histogram(
            x=sim["cfu"],
            marker_color=COLOR_SEQUENCE[0] if sim["mode"] == "prior" else COLOR_SEQUENCE[1],
            hovertemplate="<b>Bin Range</b>: %{x} CFUs<br><b>Frequency</b>: %{y}<extra></extra>",
        ),
        layout=BASE_GRAPH_LAYOUT,
    )
    fig_cfu.update_layout(
        title="Estimated Component CFU Count",
        xaxis=dict(title="CFU Count"),
        yaxis=dict(title="Frequency"),
    )

    # Determine percentage sampled
    area_vol_sampled_attr = "Sampled Area" if hw["dim"].startswith("2") else "Sampled Volume"
    area_vol_total_attr = "area" if hw["dim"].startswith("2") else "volume"
    area_vol_sampled = (
        0 if not samples_list else sum([s[area_vol_sampled_attr] for s in samples_list])
    )
    pct = round((area_vol_sampled / hw[area_vol_total_attr]) * 100, 2)
    area_vol_units = "m²" if hw["dim"].startswith("2") else "cm³"

    # Determine tgt density and assessment
    density_str = "--" if not density else f"{density} {density_units}"
    assessment_pct = (
        None if not density else sum(np.array(sim["lambda"]) < density) / len(sim["lambda"])
    )
    assessment_str = assessment_text(assessment_pct)

    # Construct rows for the percentile tables
    quantiles = [0.05, 0.5, 0.95]
    lambda_draws_used = lambda_draws if lambda_draws else POSTERIOR_MAP[sim["link"]]
    stats_lambda = [np.mean(lambda_draws_used)] + [
        x for x in np.quantile(lambda_draws_used, q=quantiles)
    ]
    stats_cfu = [np.mean(sim["cfu"])] + [x for x in np.quantile(sim["cfu"], q=quantiles)]
    stats_rows_lambda = dmc.TableTr([dmc.TableTd(round(x, 3)) for x in stats_lambda])
    stats_rows_cfu = dmc.TableTr([dmc.TableTd(round(x)) for x in stats_cfu])

    return (
        fig_lambda,
        fig_cfu,
        f"Component - Sampled (L{hw['level']})",
        f"{area_vol_sampled} {area_vol_units} of {hw[area_vol_total_attr]} {area_vol_units} ({pct}%)",
        density_str,
        assessment_str,
        stats_rows_lambda,
        stats_rows_cfu,
    )


def implied_component_results(
    hw: dict, sim_self: dict, sim_implied: dict, density: int | float | None
):
    """Generate result elements for implied components"""

    # Get density units first to include in fig annotations
    area_vol_total_attr = "area" if hw["dim"].startswith("2") else "volume"
    area_vol_units = "m²" if hw["dim"].startswith("2") else "cm³"
    density_units = f"spores / {area_vol_units}"

    # Construct bioburden density figure
    lambda_draws = [sim_implied["lambda"]] if sim_implied["mode"] == "posterior" else []
    lambda_name = [hw["id"]] if sim_implied["mode"] == "posterior" else []
    fig_lambda = ff.create_distplot(
        [POSTERIOR_MAP[sim_implied["link"]]] + lambda_draws,
        ["Analogy"] + lambda_name,
        show_hist=False,
        colors=COLOR_SEQUENCE,
    )
    fig_lambda.update_layout(BASE_GRAPH_LAYOUT)
    fig_lambda.update_layout(
        title="Estimated Bioburden Density",
        xaxis=dict(title=f"Bioburden Density ({density_units})"),
        yaxis=dict(title="Probability Density", showexponent="all", exponentformat="e"),
    )
    fig_lambda.update_traces(
        hovertemplate="<b>Bioburden Density</b>: %{x:.3f}"
        + f" {density_units}"
        + "<br><b>Probability Density</b>: %{y:.6f}<extra></extra>",
        selector=dict(type="scatter", mode="lines"),
    )
    fig_lambda.update_traces(
        hovertemplate="<b>Bioburden Density</b>: %{x:.3f}" + f" {density_units}<extra></extra>",
        selector=dict(type="scatter", mode="markers"),
    )

    # Construct CFU figure
    fig_cfu = go.Figure(
        go.Histogram(
            x=sim_self["cfu"],
            marker_color=COLOR_SEQUENCE[0] if sim_implied["mode"] == "prior" else COLOR_SEQUENCE[1],
            hovertemplate="<b>Bin Range</b>: %{x} CFUs<br><b>Frequency</b>: %{y}<extra></extra>",
        ),
        layout=BASE_GRAPH_LAYOUT,
    )
    fig_cfu.update_layout(
        title="Estimated Component CFU Count",
        xaxis=dict(title="CFU Count"),
        yaxis=dict(title="Frequency"),
    )

    # Determine tgt density and assessment
    density_str = "--" if not density else f"{density} {density_units}"
    assessment_pct = (
        None
        if not density
        else sum(np.array(sim_implied["lambda"]) < density) / len(sim_implied["lambda"])
    )
    assessment_str = assessment_text(assessment_pct)

    # Construct rows for the percentile tables
    quantiles = [0.05, 0.5, 0.95]
    lambda_draws_used = lambda_draws if lambda_draws else POSTERIOR_MAP[sim_implied["link"]]
    stats_lambda = [np.mean(lambda_draws_used)] + [
        x for x in np.quantile(lambda_draws_used, q=quantiles)
    ]
    stats_cfu = [np.mean(sim_self["cfu"])] + [x for x in np.quantile(sim_self["cfu"], q=quantiles)]
    stats_rows_lambda = dmc.TableTr([dmc.TableTd(round(x, 3)) for x in stats_lambda])
    stats_rows_cfu = dmc.TableTr([dmc.TableTd(round(x)) for x in stats_cfu])

    return (
        fig_lambda,
        fig_cfu,
        f"Component - Implied (L{hw['level']})",
        f"0 {area_vol_units} of {hw[area_vol_total_attr]} {area_vol_units} (0.0%)",
        density_str,
        assessment_str,
        stats_rows_lambda,
        stats_rows_cfu,
    )


def spec_component_results(hw: dict, sim: dict, density: int | float | None):
    """Generate result elements for spec components"""

    # Get density units first to include in fig annotations
    area_vol_total_attr = "area" if hw["dim"].startswith("2") else "volume"
    area_vol_units = "m²" if hw["dim"].startswith("2") else "cm³"
    density_units = f"spores / {area_vol_units}"

    # Generate blank figures with annotations
    fig_lambda = go.Figure(BASE_GRAPH_FIG)
    fig_lambda.add_annotation(
        text=f"Figure not available: component is spec<br>Spec Bioburden Density: {sim['lambda']} {density_units}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=18, color="crimson"),
    )
    fig_cfu = go.Figure(BASE_GRAPH_FIG)
    fig_cfu.add_annotation(
        text=f"Figure not available: component is spec<br>Spec Component CFU Count: {sim['cfu']}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=18, color="crimson"),
    )

    # Determine tgt density and assessment
    density_str = "--" if not density else f"{density} {density_units}"
    if not density:
        assessment_str = assessment_text(None)
    else:
        assessment_str = (
            "Spec density is less than target density"
            if sim["lambda"] <= density
            else "Spec density is greater than target density"
        )

    # Construct rows for the percentile tables
    stats_rows_lambda = dmc.TableTr([dmc.TableTd(sim["lambda"]) for _ in range(4)])
    stats_rows_cfu = dmc.TableTr([dmc.TableTd(sim["cfu"]) for _ in range(4)])

    return (
        fig_lambda,
        fig_cfu,
        f"Component - Spec (L{hw['level']})",
        f"0 {area_vol_units} of {hw[area_vol_total_attr]} {area_vol_units} (0.0%)",
        density_str,
        assessment_str,
        stats_rows_lambda,
        stats_rows_cfu,
    )


def rollup_results(hw: dict, tgt_dim: str, sims_rollups: dict, density: int | float | None):
    """Generate result elements for rollup hardware"""

    # Get density units first to include in fig annotations
    area_vol_units = "m²" if tgt_dim.startswith("2") else "cm³"
    density_units = f"spores / {area_vol_units}"

    # Calculate result elements from rollup info
    rollup_info = sims_rollups[hw["id"]][0 if tgt_dim.startswith("2") else 1]
    lambda_draws = (
        np.array(rollup_info["lambda"])
        if isinstance(rollup_info["lambda"], list)
        else rollup_info["lambda"]
    )
    cfu_draws = (
        np.array(rollup_info["cfu"]) if isinstance(rollup_info["cfu"], list) else rollup_info["cfu"]
    )
    sampled_pct = round((rollup_info["sampled"] / rollup_info["total"]) * 100, 2)

    # Handle no uncertainty case (all children are spec)
    if isinstance(lambda_draws, float) or isinstance(lambda_draws, int):
        # Generate blank figures with annotations
        fig_lambda = go.Figure(BASE_GRAPH_FIG)
        fig_lambda.add_annotation(
            text=f"Figure not available: all children are spec<br>Spec Avg Bioburden Density: {round(lambda_draws, 3)} {density_units}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color="crimson"),
        )
        fig_cfu = go.Figure(BASE_GRAPH_FIG)
        fig_cfu.add_annotation(
            text=f"Figure not available: all children are spec<br>Spec Total CFU Count: {round(cfu_draws)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color="crimson"),
        )

        # Determine tgt density and assessment
        density_str = "--" if not density else f"{density} {density_units}"
        if not density:
            assessment_str = assessment_text(None)
        else:
            assessment_str = (
                "Spec density is less than target density"
                if lambda_draws <= density
                else "Spec density is greater than target density"
            )

        # Construct rows for percentile table
        stats_rows_lambda = dmc.TableTr([dmc.TableTd(round(lambda_draws, 3)) for _ in range(4)])
        stats_rows_cfu = dmc.TableTr([dmc.TableTd(round(cfu_draws)) for _ in range(4)])

    # Handle standard case (at least one sampled child)
    else:
        # Construct bioburden density figure
        fig_lambda = ff.create_distplot(
            [lambda_draws], [hw["id"]], show_hist=False, colors=COLOR_SEQUENCE[1:]
        )
        fig_lambda.update_layout(BASE_GRAPH_LAYOUT)
        fig_lambda.update_layout(
            title="Estimated Bioburden Density",
            xaxis=dict(title=f"Bioburden Density ({density_units})"),
            yaxis=dict(title="Probability Density", showexponent="all", exponentformat="e"),
        )
        fig_lambda.update_traces(
            hovertemplate="<b>Bioburden Density</b>: %{x:.3f}"
            + f" {density_units}"
            + "<br><b>Probability Density</b>: %{y:.6f}<extra></extra>",
            selector=dict(type="scatter", mode="lines"),
        )
        fig_lambda.update_traces(
            hovertemplate="<b>Bioburden Density</b>: %{x:.3f}" + f" {density_units}<extra></extra>",
            selector=dict(type="scatter", mode="markers"),
        )

        # Construct CFU figure
        fig_cfu = go.Figure(
            go.Histogram(
                x=cfu_draws,
                marker_color=COLOR_SEQUENCE[1],
                hovertemplate="<b>Bin Range</b>: %{x} CFUs<br><b>Frequency</b>: %{y}<extra></extra>",
            ),
            layout=BASE_GRAPH_LAYOUT,
        )
        fig_cfu.update_layout(
            title="Estimated Total CFU Count",
            xaxis=dict(title="CFU Count"),
            yaxis=dict(title="Frequency"),
        )

        # Determine tgt density and assessment
        density_str = "--" if not density else f"{density} {density_units}"
        assessment_pct = None if not density else sum(lambda_draws < density) / len(lambda_draws)
        assessment_str = assessment_text(assessment_pct)

        # Construct rows for percentile table
        quantiles = [0.05, 0.5, 0.95]
        stats_lambda = [np.mean(lambda_draws)] + [x for x in np.quantile(lambda_draws, q=quantiles)]
        stats_cfu = [np.mean(cfu_draws)] + [x for x in np.quantile(cfu_draws, q=quantiles)]
        stats_rows_lambda = dmc.TableTr([dmc.TableTd(round(x, 3)) for x in stats_lambda])
        stats_rows_cfu = dmc.TableTr([dmc.TableTd(round(x)) for x in stats_cfu])

    return (
        fig_lambda,
        fig_cfu,
        f"Rollup (L{hw['level']})",
        f"{rollup_info['sampled']} {area_vol_units} of {rollup_info['total']} {area_vol_units} ({sampled_pct}%)",
        density_str,
        assessment_str,
        stats_rows_lambda,
        stats_rows_cfu,
    )


def project_results(tgt_dim: str, sims_rollups: dict, density: int | float | None):
    """Generate result elements for project-level rollup"""

    # Get density units first to include in fig annotations
    area_vol_units = "m²" if tgt_dim.startswith("2") else "cm³"
    density_units = f"spores / {area_vol_units}"

    # Calculate result elements from rollup info
    rollup_info = sims_rollups["-- Project --"][0 if tgt_dim.startswith("2") else 1]
    lambda_draws = (
        np.array(rollup_info["lambda"])
        if isinstance(rollup_info["lambda"], list)
        else rollup_info["lambda"]
    )
    cfu_draws = (
        np.array(rollup_info["cfu"]) if isinstance(rollup_info["cfu"], list) else rollup_info["cfu"]
    )
    sampled_pct = round((rollup_info["sampled"] / rollup_info["total"]) * 100, 2)

    # Handle no uncertainty case (all children are spec)
    if isinstance(lambda_draws, float) or isinstance(lambda_draws, int):
        # Generate blank figures with annotations
        fig_lambda = go.Figure(BASE_GRAPH_FIG)
        fig_lambda.add_annotation(
            text=f"Figure not available: all children are spec<br>Spec Avg Bioburden Density: {round(lambda_draws, 3)} {density_units}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color="crimson"),
        )
        fig_cfu = go.Figure(BASE_GRAPH_FIG)
        fig_cfu.add_annotation(
            text=f"Figure not available: all children are spec<br>Spec Total CFU Count: {round(cfu_draws)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color="crimson"),
        )

        # Determine tgt density and assessment
        density_str = "--" if not density else f"{density} {density_units}"
        if not density:
            assessment_str = assessment_text(None)
        else:
            assessment_str = (
                "Spec density is less than target density"
                if lambda_draws <= density
                else "Spec density is greater than target density"
            )

        # Construct rows for percentile table
        stats_rows_lambda = dmc.TableTr([dmc.TableTd(round(lambda_draws, 3)) for _ in range(4)])
        stats_rows_cfu = dmc.TableTr([dmc.TableTd(round(cfu_draws)) for _ in range(4)])

    # Handle standard case (at least one sampled child)
    else:
        # Construct bioburden density figure
        fig_lambda = ff.create_distplot(
            [lambda_draws], ["Project"], show_hist=False, colors=COLOR_SEQUENCE[1:]
        )
        fig_lambda.update_layout(BASE_GRAPH_LAYOUT)
        fig_lambda.update_layout(
            title="Estimated Bioburden Density",
            xaxis=dict(title=f"Bioburden Density ({density_units})"),
            yaxis=dict(title="Probability Density", showexponent="all", exponentformat="e"),
        )
        fig_lambda.update_traces(
            hovertemplate="<b>Bioburden Density</b>: %{x:.3f}"
            + f" {density_units}"
            + "<br><b>Probability Density</b>: %{y:.6f}<extra></extra>",
            selector=dict(type="scatter", mode="lines"),
        )
        fig_lambda.update_traces(
            hovertemplate="<b>Bioburden Density</b>: %{x:.3f}" + f" {density_units}<extra></extra>",
            selector=dict(type="scatter", mode="markers"),
        )

        # Construct CFU figure
        fig_cfu = go.Figure(
            go.Histogram(
                x=cfu_draws,
                marker_color=COLOR_SEQUENCE[1],
                hovertemplate="<b>Bin Range</b>: %{x} CFUs<br><b>Frequency</b>: %{y}<extra></extra>",
            ),
            layout=BASE_GRAPH_LAYOUT,
        )
        fig_cfu.update_layout(
            title="Estimated Total CFU Count",
            xaxis=dict(title="CFU Count"),
            yaxis=dict(title="Frequency"),
        )

        # Determine tgt density and assessment
        density_str = "--" if not density else f"{density} {density_units}"
        assessment_pct = None if not density else sum(lambda_draws < density) / len(lambda_draws)
        assessment_str = assessment_text(assessment_pct)

        # Construct rows for percentile table
        quantiles = [0.05, 0.5, 0.95]
        stats_lambda = [np.mean(lambda_draws)] + [x for x in np.quantile(lambda_draws, q=quantiles)]
        stats_cfu = [np.mean(cfu_draws)] + [x for x in np.quantile(cfu_draws, q=quantiles)]
        stats_rows_lambda = dmc.TableTr([dmc.TableTd(round(x, 3)) for x in stats_lambda])
        stats_rows_cfu = dmc.TableTr([dmc.TableTd(round(x)) for x in stats_cfu])

    return (
        fig_lambda,
        fig_cfu,
        "Rollup (L1)",
        f"{rollup_info['sampled']} {area_vol_units} of {rollup_info['total']} {area_vol_units} ({sampled_pct}%)",
        density_str,
        assessment_str,
        stats_rows_lambda,
        stats_rows_cfu,
    )


def attach_callbacks(app: Dash):
    """"""

    @app.callback(
        Output("sims-components-json", "data"),
        Input("hardware-diff", "data"),
        Input("samples-diff", "data"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        State("hardware-prev", "data"),
        State("samples-prev", "data"),
        State("sims-components-json", "data"),
    )
    def store_sims_components(
        hardware_diff: dict,
        samples_diff: dict,
        hardware_dict: dict,
        samples_list: list[dict],
        hardware_prev: dict,
        samples_prev: list[dict],
        current_sims: dict,
    ):
        """Update sampled component simulations when components or samples change"""

        # We can look at valid samples only for most cases
        samples_valid = identify_valid_samples(samples_list, hardware_dict)
        samples_list_valid = [s for s in samples_list if s["Sample ID"] in samples_valid]

        def is_eligible(hw):
            if hw is None:
                return False
            if hw["analogy"] != "-- Generic --":
                return hw["valid"]
            else:
                return hw["valid"] and bool(
                    [
                        s
                        for s in samples_list_valid
                        if s["Hardware ID"] == hw["id"] and s["PP Accountable"].lower() == "yes"
                    ]
                )

        # Case 1: change to components triggers the callback
        if "hardware-diff.data" in ctx.triggered_prop_ids:
            update = hardware_diff
            if not update:
                raise PreventUpdate

            # Case 2.1: handle batch import of hardware
            # Have to reserve any implied sims to last so linked sampled sim is available
            if (
                "values_changed" in update
                and len(list(update["values_changed"].keys())) == 1
                and list(update["values_changed"].keys())[0] == "root"
            ):
                current_sims = {"noop": False, "sims": {}}
                for hw in filter(
                    lambda hw: is_eligible(hw) and hw["type"] != "Unsampled - Implied",
                    hardware_dict.values(),
                ):
                    current_sims["sims"][hw["id"]] = sim_component(
                        hw, samples_list_valid, current_sims
                    )
                for hw in filter(
                    lambda hw: is_eligible(hw) and hw["type"] == "Unsampled - Implied",
                    hardware_dict.values(),
                ):
                    current_sims["sims"][hw["id"]] = sim_component(
                        hw, samples_list_valid, current_sims
                    )
                return current_sims

            # Case 2.2: single added hardware elem
            if "dictionary_item_added" in update and len(update["dictionary_item_added"]) == 1:
                added_loc = update["dictionary_item_added"][0]
                added_res = hardware_dict[unpack_deepdiff_loc(added_loc)[0]]
                implied_added = find_implied_hardware(added_res, hardware_dict)

                # Case 2.2.1: added hardware coerces a component to rollup
                if "values_changed" in update:
                    coerced_loc = list(update["values_changed"].keys())[0]
                    coerced_idx, _ = unpack_deepdiff_loc(coerced_loc)
                    coerced = hardware_prev[coerced_idx]
                    implied_coerced = find_implied_hardware(coerced, hardware_dict)
                    if is_eligible(coerced):
                        del current_sims["sims"][coerced["id"]]
                        for hw_imp in implied_coerced:
                            del current_sims["sims"][hw_imp["id"]]
                        current_sims["noop"] = False
                    if is_eligible(added_res):
                        current_sims["sims"][added_res["id"]] = sim_component(
                            added_res, samples_list_valid, current_sims
                        )
                        for hw_imp in implied_added:
                            current_sims["sims"][hw_imp["id"]] = sim_component(
                                hw_imp, samples_list_valid, current_sims
                            )
                        current_sims["noop"] = False
                    return current_sims

                # Case 2.2.2: added hardware does not coerce a component to rollup
                else:
                    if not is_eligible(added_res):
                        current_sims["noop"] = True
                        return current_sims
                    current_sims["sims"][added_res["id"]] = sim_component(
                        added_res, samples_list_valid, current_sims
                    )
                    for hw_imp in implied_added:
                        current_sims["sims"][hw_imp["id"]] = sim_component(
                            hw_imp, samples_list_valid, current_sims
                        )
                    current_sims["noop"] = False
                    return current_sims

            # Case 2.3: component(s) removed
            if "dictionary_item_removed" in update:
                removed_res_arr = [
                    hardware_prev[unpack_deepdiff_loc(removed_loc)[0]]
                    for removed_loc in update["dictionary_item_removed"]
                ]
                noop = True
                for removed_res in removed_res_arr:
                    if is_eligible(removed_res) or (
                        removed_res["id"] in current_sims["sims"] and not is_eligible(removed_res)
                    ):
                        noop = False
                        implied_removed = find_implied_hardware(removed_res, hardware_dict)
                        del current_sims["sims"][removed_res["id"]]
                        for hw_imp in implied_removed:
                            del current_sims["sims"][hw_imp["id"]]
                current_sims["noop"] = noop
                return current_sims

            # Case 2.4: existing component(s) edited
            if "values_changed" in update:
                # Extract the updates
                update_locs = list(update["values_changed"].keys())
                update_locs_unpacked = reduce(
                    reduce_deefdiff_edits, [unpack_deepdiff_loc(u) for u in update_locs], {}
                )

                # Can skip if just metadata updated in all cases
                if all(
                    [
                        x in HARDWARE_METADATA_COLUMNS
                        for x in sum(list(update_locs_unpacked.values()), [])
                    ]
                ):
                    raise PreventUpdate

                # Iterate through updated elements
                noops = []
                for update_idx, update_attrs in update_locs_unpacked.items():
                    # Easy skip if this sample only has metadata updates
                    if all([x in HARDWARE_METADATA_COLUMNS for x in update_attrs]):
                        noops.append(True)
                        continue

                    # Extract supplemental info
                    old = hardware_prev[update_idx]
                    new = hardware_dict[update_idx]

                    # No-op unless hardware was or is eligible
                    if any([is_eligible(old), is_eligible(new)]):
                        noops.append(False)
                        implied = find_implied_hardware(new, hardware_dict)
                        if not is_eligible(new):
                            del current_sims["sims"][old["id"]]
                            for hw_imp in implied:
                                del current_sims["sims"][hw_imp["id"]]
                        else:
                            current_sims["sims"][new["id"]] = sim_component(
                                new, samples_list_valid, current_sims
                            )
                            for hw_imp in implied:
                                current_sims["sims"][hw_imp["id"]] = sim_component(
                                    hw_imp, samples_list_valid, current_sims
                                )
                        continue

                    # If we get here it is a no-op
                    noops.append(True)

                # Handle no-op flag and return
                current_sims["noop"] = all(noops)
                return current_sims

        # Case 2: change to samples triggers the callback
        else:
            update = samples_diff
            if not update:
                raise PreventUpdate

            # Case 1.1: sample(s) added or removed (same procedure for both)
            if "iterable_item_added" in update or "iterable_item_removed" in update:
                # Extract the updated samples
                update_res = (
                    update["iterable_item_added"].values()
                    if "iterable_item_added" in update
                    else update["iterable_item_removed"].values()
                )
                updated_hw_ids = set([s["Hardware ID"] for s in update_res])

                # No-op if none of the added samples are valid
                if "iterable_item_added" in update and not any(
                    [s["Sample ID"] in samples_valid for s in update_res]
                ):
                    current_sims["noop"] = True
                    return current_sims

                # Loop over unique hardware elements that have been updated
                # Check no-op status for each component and re-simulate if needed
                noop = True
                for hw_id in updated_hw_ids:
                    hw = hardware_dict[hw_id]
                    implied = find_implied_hardware(hw, hardware_dict)
                    if is_eligible(hw) and any(
                        [
                            s["PP Accountable"].lower() == "yes"
                            for s in update_res
                            if s["Hardware ID"] == hw_id
                        ]
                    ):
                        noop = False
                        current_sims["sims"][hw["id"]] = sim_component(
                            hw, samples_list_valid, current_sims
                        )
                        for hw_imp in implied:
                            current_sims["sims"][hw_imp["id"]] = sim_component(
                                hw_imp, samples_list_valid, current_sims
                            )
                    elif hw["id"] in current_sims["sims"] and not is_eligible(hw):
                        noop = False
                        del current_sims["sims"][hw["id"]]

                # Handle no-op flag and return
                current_sims["noop"] = noop
                return current_sims

            # Case 1.2: sample is edited
            else:
                # Extract the updates
                update_locs = list(update["values_changed"].keys())
                update_locs_unpacked = reduce(
                    reduce_deefdiff_edits, [unpack_deepdiff_loc(u) for u in update_locs], {}
                )

                # Can skip if just metadata was updated in all cases
                if all(
                    [
                        x in SAMPLE_TABLE_METADATA_COLUMNS
                        for x in sum(list(update_locs_unpacked.values()), [])
                    ]
                ):
                    raise PreventUpdate

                # Iterate through updated samples
                noops = []
                for update_idx, update_attrs in update_locs_unpacked.items():
                    # Easy skip if this sample only has metadata updates
                    if all([x in SAMPLE_TABLE_METADATA_COLUMNS for x in update_attrs]):
                        noops.append(True)
                        continue

                    # Extract supplemental info
                    new = samples_list[update_idx]
                    old = find_by_key(samples_prev, "Sample ID", new["Sample ID"])
                    hw = hardware_dict[new["Hardware ID"]]
                    implied = find_implied_hardware(hw, hardware_dict)

                    # No-op in these cases:
                    # 1. Updated sample is for ineligible hardware
                    # 2. Updated sample was invalid before the update and still is
                    # 3. Updated sample was not PP accountable before the update and still isn't
                    if any(
                        [
                            not is_eligible(hw),
                            new["Sample ID"] not in samples_valid
                            and old["Sample ID"] not in samples_valid,
                            new["PP Accountable"].lower() != "yes"
                            and old["PP Accountable"].lower() != "yes",
                        ]
                    ):
                        noops.append(True)
                        continue

                    # Re-simulate component and update
                    current_sims["sims"][hw["id"]] = sim_component(hw, samples_list, current_sims)
                    for hw_imp in implied:
                        current_sims["sims"][hw_imp["id"]] = sim_component(
                            hw_imp, samples_list, current_sims
                        )
                    noops.append(False)

                # Handle no-op flag and return
                current_sims["noop"] = all(noops)
                return current_sims

        # If none of these apply raise an error
        raise Exception("Unsupported update situation encountered")

    @app.callback(
        Output("sims-rollups-json", "data"),
        Input("sims-components-json", "data"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        prevent_initial_call=True,
    )
    def store_sims_rollups(
        sims: dict,
        hardware_dict: dict,
        samples_list: list[dict],
    ):
        """Update rollup calculations when underlying component simulations change"""

        sims_rollups = {}
        empty_res = {"lambda": 0, "cfu": 0, "total": 0, "sampled": 0}
        samples_valid = identify_valid_samples(samples_list, hardware_dict)

        def handle_child(child):
            if child["is_component"]:
                hw = hardware_dict[child["id"]]
                if not hw["valid"] or (
                    hw["analogy"] == "-- Generic --"
                    and not bool(
                        [
                            s
                            for s in samples_list
                            if s["Hardware ID"] == hw["id"]
                            and s["PP Accountable"].lower() == "yes"
                            and s["Sample ID"] in samples_valid
                        ]
                    )
                ):
                    return (empty_res, empty_res)
                if hw["dim"].startswith("2"):
                    return (
                        {
                            "lambda": sims["sims"][child["id"]]["lambda"],
                            "cfu": sims["sims"][child["id"]]["cfu"],
                            "total": hw["area"],
                            "sampled": sum(
                                [
                                    s["Sampled Area"]
                                    for s in samples_list
                                    if (
                                        s["Hardware ID"] == hw["id"]
                                        and s["Sample ID"] in samples_valid
                                        and s["PP Accountable"].lower() == "yes"
                                    )
                                ]
                            ),
                        },
                        empty_res,
                    )
                else:
                    return (
                        empty_res,
                        {
                            "lambda": sims["sims"][child["id"]]["lambda"],
                            "cfu": sims["sims"][child["id"]]["cfu"],
                            "total": hw["volume"],
                            "sampled": sum(
                                [
                                    s["Sampled Volume"]
                                    for s in samples_list
                                    if (
                                        s["Hardware ID"] == hw["id"]
                                        and s["Sample ID"] in samples_valid
                                        and s["PP Accountable"].lower() == "yes"
                                    )
                                ]
                            ),
                        },
                    )
            return sims_rollups[child["id"]]

        def reduce_child_results(child_results):
            area_total = 0
            area_sampled = 0
            area_lambda = 0
            area_cfu = 0
            volume_total = 0
            volume_sampled = 0
            volume_lambda = 0
            volume_cfu = 0
            for res in child_results:
                area_total += res[0]["total"]
                area_sampled += res[0]["sampled"]
                area_lambda += res[0]["total"] * (
                    np.array(res[0]["lambda"])
                    if isinstance(res[0]["lambda"], list)
                    else res[0]["lambda"]
                )
                area_cfu += (
                    np.array(res[0]["cfu"]) if isinstance(res[0]["cfu"], list) else res[0]["cfu"]
                )
                volume_total += res[1]["total"]
                volume_sampled += res[1]["sampled"]
                volume_lambda += res[1]["total"] * (
                    np.array(res[1]["lambda"])
                    if isinstance(res[1]["lambda"], list)
                    else res[1]["lambda"]
                )
                volume_cfu += (
                    np.array(res[1]["cfu"]) if isinstance(res[1]["cfu"], list) else res[1]["cfu"]
                )
            if area_total:
                area_lambda /= area_total
            if volume_total:
                volume_lambda /= volume_total
            return (
                {
                    "lambda": area_lambda,
                    "cfu": area_cfu,
                    "total": round(area_total, 6),
                    "sampled": round(area_sampled, 6),
                },
                {
                    "lambda": volume_lambda,
                    "cfu": volume_cfu,
                    "total": round(volume_total, 6),
                    "sampled": round(volume_sampled, 6),
                },
            )

        # Can skip if the sims change didn't result in new values
        if sims["noop"]:
            raise PreventUpdate

        # Start at level 5 and build up iteratively to level 2
        # Can skip level 6 since guaranteed to be components
        for level in reversed(range(2, 6)):
            rollup_elems = [
                elem
                for elem in hardware_dict.values()
                if elem["level"] == level and not elem["is_component"]
            ]
            for elem in rollup_elems:
                child_results = [
                    handle_child(child)
                    for child in hardware_dict.values()
                    if child["parent_id"] == elem["id"]
                ]
                sims_rollups[elem["id"]] = reduce_child_results(child_results)

        # Calculate L1 (project level rollup)
        l2_results = [
            handle_child(elem) for elem in hardware_dict.values() if not elem["parent_id"]
        ]
        sims_rollups["-- Project --"] = reduce_child_results(l2_results)

        return sims_rollups

    @app.callback(
        Output("select-results-hardware-id", "data"),
        Input("hardware-json", "data"),
        Input("datatable-samples", "data"),
    )
    def target_hardware_options(hardware_dict: dict, samples_list: list[dict]):
        """Identify the allowed options for rolling up results"""

        # Only consider "valid" components or rollups with at least 1 valid child
        eligible_hardware_ids = find_eligible_hardware_ids(hardware_dict, samples_list)

        # Construct options with level groupings
        options = []
        for level in sorted(eligible_hardware_ids.keys()):
            options.append(
                {
                    "group": f"L{level}",
                    "items": [
                        {"value": elem_id, "label": elem_id}
                        for elem_id in eligible_hardware_ids[level]
                    ],
                }
            )

        return options

    @app.callback(
        Output("select-results-dim", "data"),
        Output("select-results-dim", "value"),
        Input("select-results-hardware-id", "value"),
        State("select-results-dim", "value"),
        State("hardware-json", "data"),
    )
    def target_dim_options(
        hardware_id: str,
        current_dim: str,
        hardware_dict: dict,
    ):
        """Identify which options should be available for target dimension"""

        # If hardware ID is blank then so must dim
        if not hardware_id:
            return [], None

        # If rollup need to identify unique dimensions of all valid children components
        if hardware_id == "-- Project --" or not hardware_dict[hardware_id]["is_component"]:
            comp_ids = find_rollup_nested_component_ids(hardware_id, hardware_dict)
            dims = sorted(
                set(
                    [
                        hw["dim"]
                        for hw in hardware_dict.values()
                        if hw["id"] in comp_ids and hw["valid"]
                    ]
                )
            )
            return list(dims), current_dim if current_dim in dims else dims[0]

        # Otherwise hardware is component and only single option (dim of component)
        else:
            hw = hardware_dict[hardware_id]
            if not hw["valid"]:
                return [], None
            dim = hw["dim"]
            return [{"label": dim, "value": dim}], dim

    @app.callback(
        Output("bioburden-results", "figure"),
        Output("cfu-results", "figure"),
        Output("results-alert-mode", "children"),
        Output("results-alert-pct", "children"),
        Output("results-alert-density", "children"),
        Output("results-alert-assessment", "children"),
        Output("bioburden-table", "children"),
        Output("cfu-table", "children"),
        Input("select-results-hardware-id", "value"),
        Input("select-results-dim", "value"),
        Input("sims-rollups-json", "data"),
        Input("sims-components-json", "data"),
        Input("project-diff", "data"),
        Input("groups-diff", "data"),
        State("datatable-samples", "data"),
        State("datatable-groups", "data"),
        State("hardware-json", "data"),
        State("project-json", "data"),
        prevent_initial_call=True,
    )
    def target_hardware_results(
        hw_id: str,
        hw_dim: str,
        sims_rollups: dict,
        sims_components: dict,
        project_diff: str,
        groups_diff: dict,
        samples_list: list[dict],
        groups_list: list[dict],
        hardware_dict: dict,
        project_dict: dict,
    ):
        """Render the result summary for a target piece of hardware"""

        must_update = False

        # Immediately return blank results if no hardware or dim selected, so we dont have to worry about this case
        if not hw_id or not hw_dim:
            return BASE_GRAPH_FIG, BASE_GRAPH_FIG, "--", "--", "--", assessment_text(None), [], []

        # Update cases: select-results-hardware-id, select-results-dim
        # - always update!
        if not must_update and (
            "select-results-hardware-id.value" in ctx.triggered_prop_ids
            or "select-results-dim.value" in ctx.triggered_prop_ids
        ):
            must_update = True

        # Update cases: sims-components-json, sims-rollups-json
        # - must update if component sims was not a no-op (for now, could be optimized further)
        if not must_update and (
            "sims-components-json.data" in ctx.triggered_prop_ids
            or "sims-rollups-json.data" in ctx.triggered_prop_ids
        ):
            must_update = not sims_components["noop"]

        # Update cases: project-diff
        # - project group is changed and target hardware is '-- Project --' keyword
        if not must_update and ("project-diff.data" in ctx.triggered_prop_ids):
            must_update = hw_id == "-- Project --"

        # Update cases: groups-diff
        # - edited group value used for selected hardware + dim
        # - deleted group used for selected hardware
        if not must_update and ("groups-diff.data" in ctx.triggered_prop_ids):
            if len(groups_diff) == 1 and "values_changed" in groups_diff:
                [changed_idx, changed_field] = unpack_deepdiff_loc(
                    list(groups_diff["values_changed"].keys())[0]
                )
                changed_tag = groups_list[changed_idx]["Group Tag"]
                if (hw_id == "-- Project --" and project_dict["group"] == changed_tag) or (
                    hw_id != "-- Project --" and hardware_dict[hw_id]["group"] == changed_tag
                ):
                    must_update = (
                        hw_dim == "2D (Area)" and changed_field == "Target Density (2D)"
                    ) or (hw_dim == "3D (Volume)" and changed_field == "Target Density (3D)")
            elif len(groups_diff) == 1 and "iterable_item_removed" in groups_diff:
                removed_tag = list(groups_diff["iterable_item_removed"].values())[0]["Group Tag"]
                must_update = (
                    hw_id == "-- Project --" and project_dict["group"] == removed_tag
                ) or (hw_id != "-- Project --" and hardware_dict[hw_id]["group"] == removed_tag)

        # Only continue if we must update
        if not must_update:
            raise PreventUpdate

        # Case 1: results for entire project
        if hw_id == "-- Project --":
            group = find_by_key(groups_list, "Group Tag", project_dict["group"])
            density = None if not group else group[f"Target Density ({hw_dim[0]}D)"]
            return project_results(hw_dim, sims_rollups, density)

        # Case 2: results for a rollup element
        elif not hardware_dict[hw_id]["is_component"]:
            rollup = hardware_dict[hw_id]
            group = find_by_key(groups_list, "Group Tag", rollup["group"])
            density = None if not group else group[f"Target Density ({hw_dim[0]}D)"]
            return rollup_results(hardware_dict[hw_id], hw_dim, sims_rollups, density)

        # Case 3: results for single component
        # Extract the component information including hardware element and group
        comp = hardware_dict[hw_id]
        group = find_by_key(groups_list, "Group Tag", comp["group"])
        density = None if not group else group[f"Target Density ({comp['dim'][0]}D)"]

        # Case 3.1: sampled component
        if comp["type"] == "Sampled":
            samples_valid = identify_valid_samples(samples_list, hardware_dict)
            samples_eligible = [
                s
                for s in samples_list
                if s["Hardware ID"] == hw_id
                and s["Sample ID"] in samples_valid
                and s["PP Accountable"].lower() == "yes"
            ]
            sim = sims_components["sims"][hw_id]
            return sampled_component_results(comp, samples_eligible, sim, density)

        # Case 3.2: implied component
        if comp["type"] == "Unsampled - Implied":
            sim_self = sims_components["sims"][hw_id]
            sim_implied = sims_components["sims"][sim_self["link"]]
            return implied_component_results(comp, sim_self, sim_implied, density)

        # Case 3.3: spec component
        if comp["type"] == "Unsampled - Spec":
            sim = sims_components["sims"][hw_id]
            return spec_component_results(comp, sim, density)

    @app.callback(
        Output("datatable-ppel", "hidden_columns"),
        Input("checklist-datatable-ppel-columns", "value"),
        State("datatable-ppel", "columns"),
        prevent_initial_call=True,
    )
    def ppel_table_cols(selected_cols: list[str], all_cols: list[dict]):
        """Show/hide columns in the PPEL table based on user checklist"""

        return [col["id"] for col in all_cols if col["id"] not in selected_cols]

    @app.callback(
        Output("datatable-ppel", "data"),
        Input("control-ppel-percentile", "value"),
        Input("hardware-diff", "data"),
        Input("samples-diff", "data"),
        Input("sims-components-json", "data"),
        Input("sims-rollups-json", "data"),
        Input("project-diff", "data"),
        Input("groups-diff", "data"),
        State("datatable-ppel", "data"),
        State("datatable-groups", "data"),
        State("hardware-json", "data"),
        State("datatable-samples", "data"),
        State("project-json", "data"),
        State("hardware-prev", "data"),
        State("samples-prev", "data"),
        prevent_initial_call=True,
    )
    def ppel_table_rows(
        percentile: str,
        hardware_diff: dict,
        samples_diff: dict,
        sims_components: dict,
        sims_rollups: dict,
        _: str,
        groups_diff: dict,
        current_ppel: list[dict],
        groups_list: list[dict],
        hardware_dict: dict,
        samples_list: list[dict],
        project_dict: dict,
        hardware_prev: dict,
        samples_prev: list[dict],
    ):
        """Populate the PPEL table with eligible hardware"""

        def is_eligible(hw):
            if hw is None:
                return False
            if hw["analogy"] != "-- Generic --":
                return hw["valid"]
            else:
                return hw["valid"] and bool(
                    [
                        s
                        for s in [
                            s
                            for s in samples_list
                            if s["Sample ID"] in identify_valid_samples(samples_list, hardware_dict)
                        ]
                        if s["Hardware ID"] == hw["id"] and s["PP Accountable"].lower() == "yes"
                    ]
                )

        def was_eligible(hw):
            if hw is None:
                return False
            if hw["analogy"] != "-- Generic --":
                return hw["valid"]
            else:
                return hw["valid"] and bool(
                    [
                        s
                        for s in [
                            s
                            for s in samples_prev
                            if s["Sample ID"] in identify_valid_samples(samples_prev, hardware_prev)
                        ]
                        if s["Hardware ID"] == hw["id"] and s["PP Accountable"].lower() == "yes"
                    ]
                )

        must_update = False

        # Update cases: control-ppel-percentile
        # - always update!
        if not must_update and ("control-ppel-percentile.value" in ctx.triggered_prop_ids):
            must_update = True

        # Update cases: hardware-diff
        # - always update on PPEL batch import
        # - a component gets edited, and it either was eligible or is eligible now (or both)
        # - a (previously) eligible component get deleted
        if not must_update and ("hardware-diff.data" in ctx.triggered_prop_ids):
            if (
                "values_changed" in hardware_diff
                and len(list(hardware_diff["values_changed"].keys())) == 1
                and list(hardware_diff["values_changed"].keys())[0] == "root"
            ):
                must_update = True
            elif len(hardware_diff) == 1 and "values_changed" in hardware_diff:
                [changed_id, _] = unpack_deepdiff_loc(
                    list(hardware_diff["values_changed"].keys())[0]
                )
                must_update = was_eligible(hardware_prev[changed_id]) or is_eligible(
                    hardware_dict[changed_id]
                )
            elif len(hardware_diff) == 1 and "dictionary_item_removed" in hardware_diff:
                [removed_id] = unpack_deepdiff_loc(hardware_diff["dictionary_item_removed"][0])
                must_update = was_eligible(hardware_prev[removed_id])

        # Update cases: samples-diff
        # - sample for an eligible component is edited
        # - sample for an eligible component is deleted
        if not must_update and ("samples-diff.data" in ctx.triggered_prop_ids):
            if len(samples_diff) == 1 and "values_changed" in samples_diff:
                update_locs = list(samples_diff["values_changed"])
                update_locs_unpacked = reduce(
                    reduce_deefdiff_edits, [unpack_deepdiff_loc(u) for u in update_locs], {}
                )
                if all(
                    [
                        x in SAMPLE_TABLE_METADATA_COLUMNS
                        for x in sum(update_locs_unpacked.values(), [])
                    ]
                ):
                    must_update = False
                else:
                    [changed_idx, _] = unpack_deepdiff_loc(
                        list(samples_diff["values_changed"].keys())[0]
                    )
                    changed_hw_id = samples_list[changed_idx]["Hardware ID"]
                    must_update = was_eligible(hardware_prev[changed_hw_id]) or is_eligible(
                        hardware_dict[changed_hw_id]
                    )
            elif len(samples_diff) == 1 and "iterable_item_removed" in samples_diff:
                sampled_hw_id = list(samples_diff["iterable_item_removed"].values())[0][
                    "Hardware ID"
                ]
                must_update = was_eligible(hardware_prev[sampled_hw_id])

        # Update cases: sims-components-json, sims-rollups-json
        # - must update if component sims was not a no-op (for now, could be optimized further)
        if not must_update and (
            "sims-components-json.data" in ctx.triggered_prop_ids
            or "sims-rollups-json.data" in ctx.triggered_prop_ids
        ):
            must_update = not sims_components["noop"]

        # Update cases: project-diff
        # - always update unless ppel is empty
        if not must_update and ("project-diff.data" in ctx.triggered_prop_ids):
            must_update = bool(current_ppel)

        # Update cases: groups-diff
        # - edited group applied to at least one hardware element
        # - deleted group applied to at least one hardware element
        if not must_update and ("groups_diff.data" in ctx.triggered_prop_ids):
            if len(groups_diff) == 1 and "values_changed" in groups_diff:
                [changed_idx, _] = unpack_deepdiff_loc(
                    list(groups_diff["values_changed"].keys())[0]
                )
                changed_tag = groups_list[changed_idx]["Group Tag"]
                must_update = (
                    any([hw["group"] == changed_tag for hw in hardware_dict.values()])
                    or project_dict["group"] == changed_tag
                ) and current_ppel
            elif len(groups_diff) == 1 and "iterable_item_removed" in groups_diff:
                removed_tag = list(groups_diff["iterable_item_removed"].values())[0]["Group Tag"]
                must_update = (
                    any([hw["group"] == removed_tag for hw in hardware_prev.values()])
                    and current_ppel
                )

        # Only continue if we must update
        if not must_update:
            raise PreventUpdate

        def summary_fn(val):
            return (
                np.mean(val)
                if percentile == "Mean"
                else np.quantile(val, q=(float(percentile[:-1]) / 100))
            )

        def hardware_to_row(level, hw_id):
            # Start with static row elements
            row = {
                "Hardware ID": project_dict["name"] if hw_id == "-- Project --" else hw_id,
                "Level": level,
            }

            # Case 1: project or rollup row
            if hw_id == "-- Project --" or not hardware_dict[hw_id]["is_component"]:
                if hw_id == "-- Project --":
                    group = find_by_key(groups_list, "Group Tag", project_dict["group"])
                    parent_id = None
                    metadata = {i: "" for i in PPEL_TABLE_METADATA_COLUMNS}
                else:
                    rollup = hardware_dict[hw_id]
                    group = find_by_key(groups_list, "Group Tag", rollup["group"])
                    parent_id = rollup["parent_id"]
                    metadata = {
                        "Handling Constraints": rollup["handling"],
                        "Ventilation": rollup["ventilation"],
                        "Material Composition": rollup["composition"],
                        "Cleaning Procedures (Fabrication)": rollup["cleaning_fab"],
                        "Cleaning Procedures (Pre-SI&T)": rollup["cleaning_pre"],
                        "Cleaning Procedures (SI&T)": rollup["cleaning_sit"],
                        "Bioburden Reduction (Fabrication)": rollup["reduction_fab"],
                        "Bioburden Reduction (Pre-SI&T)": rollup["reduction_pre"],
                        "Bioburden Reduction (SI&T)": rollup["reduction_sit"],
                        "Hardware Notes": rollup["notes"],
                    }
                rollup_info = sims_rollups[hw_id]
                has_areas = rollup_info[0]["total"] > 0
                has_volumes = rollup_info[1]["total"] > 0
                rollup_cols = {
                    "Parent ID": parent_id,
                    "Hardware Type": "Rollup",
                    "Dimensionality": None,
                    "Total Area": rollup_info[0]["total"] if has_areas else None,
                    "Total Volume": rollup_info[1]["total"] if has_volumes else None,
                    "Analogy": None,
                    "Sampled Area": rollup_info[0]["sampled"] if has_areas else None,
                    "Sampled Volume": rollup_info[1]["sampled"] if has_volumes else None,
                    "Origin": None,
                    "Spec Class": None,
                    "Spec Value": None,
                    "Grouping": group["Group Tag"] if group else None,
                    "Grouping Target Density (2D)": group["Target Density (2D)"] if group else None,
                    "Grouping Target Density (3D)": group["Target Density (3D)"] if group else None,
                    "CBE Bioburden Density (2D)": round(summary_fn(rollup_info[0]["lambda"]), 3)
                    if has_areas
                    else None,
                    "CBE Bioburden Density (3D)": round(summary_fn(rollup_info[1]["lambda"]), 3)
                    if has_volumes
                    else None,
                    "CBE Spore Bioburden (2D)": round(summary_fn(rollup_info[0]["cfu"]))
                    if has_areas
                    else None,
                    "CBE Spore Bioburden (3D)": round(summary_fn(rollup_info[1]["cfu"]))
                    if has_volumes
                    else None,
                }
                rollup_cols.update(metadata)
                row.update(rollup_cols)

            # Case 3: component row
            else:
                comp = hardware_dict[hw_id]
                group = find_by_key(groups_list, "Group Tag", comp["group"])
                sim = sims_components["sims"][hw_id]
                lambda_sim = (
                    sims_components["sims"][sim["link"]] if sim["mode"] == "implied" else sim
                )
                lambda_val = (
                    POSTERIOR_MAP[lambda_sim["link"]]
                    if lambda_sim["mode"] == "prior"
                    else lambda_sim["lambda"]
                )
                has_areas = comp["dim"].startswith("2")
                has_volumes = comp["dim"].startswith("3")
                component_cols = {
                    "Parent ID": comp["parent_id"],
                    "Hardware Type": comp["type"],
                    "Dimensionality": comp["dim"],
                    "Total Area": comp["area"] if has_areas else None,
                    "Total Volume": comp["volume"] if has_volumes else None,
                    "Analogy": comp["analogy"],
                    "Sampled Area": sum(
                        [s["Sampled Area"] for s in samples_list if s["Hardware ID"] == comp["id"]]
                    )
                    if has_areas
                    else None,
                    "Sampled Volume": sum(
                        [
                            s["Sampled Volume"]
                            for s in samples_list
                            if s["Hardware ID"] == comp["id"]
                        ]
                    )
                    if has_volumes
                    else None,
                    "Origin": comp["implied_id"] if comp["type"] == "Unsampled - Implied" else None,
                    "Spec Class": comp["spec"] if comp["type"] == "Unsampled - Spec" else None,
                    "Spec Value": SPEC_DENSITY_MAP[comp["dim"]][comp["spec"]]
                    if comp["type"] == "Unsampled - Spec"
                    else None,
                    "Grouping": group["Group Tag"] if group else None,
                    "Grouping Target Density (2D)": group["Target Density (2D)"] if group else None,
                    "Grouping Target Density (3D)": group["Target Density (3D)"] if group else None,
                    "CBE Bioburden Density (2D)": round(summary_fn(lambda_val), 3)
                    if has_areas
                    else None,
                    "CBE Bioburden Density (3D)": round(summary_fn(lambda_val), 3)
                    if has_volumes
                    else None,
                    "CBE Spore Bioburden (2D)": round(summary_fn(sim["cfu"]))
                    if has_areas
                    else None,
                    "CBE Spore Bioburden (3D)": round(summary_fn(sim["cfu"]))
                    if has_volumes
                    else None,
                    "Handling Constraints": comp["handling"],
                    "Ventilation": comp["ventilation"],
                    "Material Composition": comp["composition"],
                    "Cleaning Procedures (Fabrication)": comp["cleaning_fab"],
                    "Cleaning Procedures (Pre-SI&T)": comp["cleaning_pre"],
                    "Cleaning Procedures (SI&T)": comp["cleaning_sit"],
                    "Bioburden Reduction (Fabrication)": comp["reduction_fab"],
                    "Bioburden Reduction (Pre-SI&T)": comp["reduction_pre"],
                    "Bioburden Reduction (SI&T)": comp["reduction_sit"],
                    "Hardware Notes": comp["notes"],
                }
                row.update(component_cols)

            return row

        # Identify the eligible hardware elements (one row per element)
        rows = []
        eligible_hardware_ids = find_eligible_hardware_ids(hardware_dict, samples_list)
        if not eligible_hardware_ids:
            return []

        # Create a row for each one
        for level, hw_ids in eligible_hardware_ids.items():
            if level == 1:
                continue
            for hw_id in hw_ids:
                rows.append(hardware_to_row(level, hw_id))

        # Sort the rows and prepend with project level row
        return [hardware_to_row(1, "-- Project --")] + sorted(
            rows, key=create_ppel_sort_key(hardware_dict)
        )
