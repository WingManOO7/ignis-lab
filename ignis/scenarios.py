"""Crew-habitat atmospheres used across the app (single source of truth).
key: (label, O2 mole fraction, pressure in atm, where the numbers come from)"""

SCENARIOS = {
    "iss": ("ISS cabin (14.7 psia, 21% O2)", 0.21, 1.00, "ISS normal atmosphere"),
    "lunar": ("Lunar habitat per challenge brief (<=10.2 psi, >=30% O2)", 0.30, 0.69, "challenge brief"),
    "exploration": ("Exploration atmosphere (8.2 psia, 34% O2)", 0.34, 0.56, "NASA exploration atmosphere"),
}

# A real test counts as "near" a scenario if its pressure is within +/-P_TOL atm and its
# oxygen is at least the scenario's (more O2 = harder fire-safety case, so it still informs it).
P_TOL, O2_TOL = 0.10, 0.01


def near_mask(o2_series, p_series, o2_target, p_target):
    return (o2_series >= o2_target - O2_TOL) & ((p_series - p_target).abs() <= P_TOL)
