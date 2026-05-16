def apply_filters(
    exercises: list[dict],
    muscles: list[str],
    equipment: list[str],
    difficulties: list[str],
) -> list[dict]:
    result = exercises
    if muscles:
        muscle_set = set(muscles)
        result = [e for e in result if muscle_set & set(e.get("primary_muscles", []))]
    if equipment:
        equip_set = set(equipment)
        result = [e for e in result if e.get("equipment") in equip_set]
    if difficulties:
        diff_set = set(difficulties)
        result = [e for e in result if e.get("difficulty") in diff_set]
    return result
