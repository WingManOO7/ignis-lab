"""Feature engineering shared by training and the saved models (must be importable for joblib to load them).

Fuel-specific slopes: each numeric input gets a heptane-only copy, so heptane and methanol can respond
differently to oxygen, pressure, diluents and droplet size. Chosen by the pre-registered model search in
scripts/experiments/model_search.py (reports/model_search.md). Mirrored exactly in
ignis/sim_assets/ignis_model.js (inputValue), checked by the parity test in tests/test_core.py."""
NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]
HEP = ["hep_" + c for c in NUM]


def add_fuel_interactions(X):
    """hep_<c> = <c> if fuel == 'Heptane' else 0."""
    X = X.copy()
    h = (X["fuel"] == "Heptane").astype(float)
    for c in NUM:
        X["hep_" + c] = h * X[c]
    return X
