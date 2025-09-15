import re

from biostar.modules.data import (
    EFFICIENCY_CONFIG,
    resolve_sample_categorical,
)


def unpack_deepdiff_loc(path_str: str):
    """Unpacks a deepdiff path string like "root['foo']['bar']" into a list of keys/indices"""

    # Match either ['key'] or [index]
    pattern = r"\['([^']+)'\]|\[(\d+)\]"
    matches = re.findall(pattern, path_str)

    # Process matches and convert to appropriate types
    result = []
    for string_key, numeric_index in matches:
        if string_key:
            result.append(string_key)
        else:
            result.append(int(numeric_index))

    return result


def reduce_deefdiff_edits(acc: dict, val: tuple):
    """Reducer function to parse/consolidate edited attributes by idx"""

    if val[0] in acc:
        acc[val[0]].append(val[1])
    else:
        acc[val[0]] = [val[1]]
    return acc


def sample_eff_tag(sample: dict):
    """Generate the recovery efficiency tag for given sample (concatenation of categoricals)"""

    return ";".join(
        [
            resolve_sample_categorical(sample[f])
            for f in ["Sampling Device", "Sampling Device Type", "Processing Technique"]
        ]
    )


def detect_sample_alerts(sample: dict, hardware_dict: dict):
    """Identify any alertable cases for the given sample, based on current state"""

    # Raise an exception if provided sample has incorrect keys
    # This should never occur
    sample_keys = [
        "Sample ID",
        "Hardware ID",
        "PP Accountable",
        "Sampled Area",
        "Sampled Volume",
        "Sampling Device",
        "Sampling Device Type",
        "Processing Technique",
        "Pour Fraction",
        "CFU",
        "Assay Name",
        "Assay Date",
        "PP Cert #",
        "Control Type",
        "Sampling Notes",
    ]
    if not isinstance(sample, dict) or set(sample.keys()) != set(sample_keys):
        raise Exception("Invalid format for provided sample, this likely indicates a bug!")

    # Valid area/volume provided (depending on dimension)
    dim = hardware_dict[sample["Hardware ID"]]["dim"]
    area_vol_tgt = "Sampled Area" if dim.startswith("2") else "Sampled Volume"
    if not (isinstance(sample[area_vol_tgt], (float, int)) and sample[area_vol_tgt] > 0):
        return "area_vol"

    # Valid categoricals provided (device, device type, processing technique)
    eff_tag = sample_eff_tag(sample)
    if eff_tag not in EFFICIENCY_CONFIG:
        return "categorical"

    # Flag non-validated recovery effiency combination for warning to user
    if isinstance(EFFICIENCY_CONFIG[eff_tag]["params"], str):
        return "efficiency"

    # Valid pour fraction provided (0 < int/float <= 1)
    if not (isinstance(sample["Pour Fraction"], (float, int)) and 0 < sample["Pour Fraction"] <= 1):
        return "fraction"

    # Valid CFU provided (int >= 0)
    if not (isinstance(sample["CFU"], int) and sample["CFU"] >= 0):
        return "cfu"

    return ""


def identify_valid_samples(samples_list: list, hardware_dict: dict):
    """Identify which of the provided samples are 'valid' based on the given hardware dict state"""

    allowed_errors = ["", "efficiency"]

    return [
        s["Sample ID"]
        for s in samples_list
        if detect_sample_alerts(s, hardware_dict) in allowed_errors
    ]


def find_implied_hardware(hw_tgt: dict, hardware_dict: dict):
    """Find any hardware that are implied from the given ID"""

    # To save time return empty list if this hardware is not sampled component
    if not hw_tgt["valid"] or hw_tgt["type"] != "Sampled":
        return []

    return [
        hw
        for hw in hardware_dict.values()
        if hw["valid"] and hw["type"] == "Unsampled - Implied" and hw["implied_id"] == hw_tgt["id"]
    ]


def find_rollup_nested_component_ids(rollup_id: str, hardware_dict: dict):
    """Identify the leaf nodes (components) associated with a piece of rollup hardware"""

    # If rollup ID is the project level keyword just return all components
    if rollup_id == "-- Project --":
        return [hw_id for hw_id, hw in hardware_dict.items() if hw["is_component"]]

    component_ids = set()

    def dfs(current_id):
        current_elem = hardware_dict[current_id]
        if current_elem["is_component"]:
            component_ids.add(current_elem["id"])
            return
        for child_id in [
            hw_id for hw_id, hw in hardware_dict.items() if hw["parent_id"] == current_id
        ]:
            dfs(child_id)

    dfs(rollup_id)

    return component_ids


def find_eligible_hardware_ids(hardware_dict: dict, samples_list: list[dict]):
    """Identify hardware elems that are valid components or rollups with 1+ valid child"""

    samples_valid = identify_valid_samples(samples_list, hardware_dict)

    eligible_hardware_ids = {}
    for hw in hardware_dict.values():
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
            continue
        while True:
            if hw["level"] not in eligible_hardware_ids:
                eligible_hardware_ids[hw["level"]] = set([hw["id"]])
            else:
                eligible_hardware_ids[hw["level"]].add(hw["id"])
            if hw["parent_id"]:
                hw = hardware_dict[hw["parent_id"]]
            else:
                eligible_hardware_ids[1] = set(["-- Project --"])
                break

    return eligible_hardware_ids
