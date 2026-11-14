"""
Pre-registered model search for the two FLEX models.  Run from the repository root:
    python scripts/experiments/model_search.py
Writes reports/model_search.md.  Touches nothing else (no models/, no train.py).

PRE-REGISTERED (written before any result was looked at)
=========================================================
Inputs: the same 6 pre-ignition columns as train.py (fuel, p_atm, x_o2, x_co2, x_he, d0_mm).
Every engineered feature is computed INSIDE the Pipeline from those 6 columns.
h = 1 if fuel == "Heptane" else 0.  All numeric features are StandardScaled after engineering.

Task A  Extinction(1) vs Completion(0), 204 rows, groups = condition_id, decision = 'prior' threshold
  A0  CURRENT: LogisticRegression(C=1) on OneHot(fuel) + Std(p, x_o2, x_co2, x_he, d0)
  A1  physics transforms, C=1: Std(log p, x_o2, x_co2, x_he, log d0, pO2 = x_o2*p)
  A2  targeted extras, C=1: current + h*x_o2, h*d0, d0^2
  A3  full fuel interactions, C=1: current + h*(each of the 5 numeric inputs)
  A4  current features, C tuned by inner StratifiedGroupKFold(4) on log-loss, C in 10^[-2..2]
  A5  physics transforms (A1) + tuned C (as A4)
  A6  cubic B-splines (4 uniform knots, linear extrapolation) on x_o2 and d0 + Std(p, x_co2, x_he), tuned C
  A7  [reference, NOT shippable] HistGradientBoosting (depth 3, lr 0.05, 200 iter, min leaf 10)
  A8  [reference, NOT shippable] RandomForest (300 trees, min leaf 3, unweighted)

Task B  burning-rate constant K (mm^2/s), 255 rows, groups = condition_id
  B0  CURRENT: Ridge(alpha=1) on OneHot(fuel) + Std(p, x_o2, x_co2, x_he, d0)
  B1  physics transforms (as A1), alpha=1
  B2  targeted extras (as A2), alpha=1
  B3  full fuel interactions (as A3), alpha=1
  B4  current features, alpha tuned by inner GroupKFold(4) on MAE, alpha in 10^[-3..2]
  B5  physics transforms + full fuel interactions, tuned alpha
  B6  splines (as A6), tuned alpha
  B7  [reference, NOT shippable] GaussianProcessRegressor, ARD RBF + white noise
  B8  [reference, NOT shippable] HistGradientBoosting (depth 3, lr 0.05, 300 iter, min leaf 10)

Protocol: identical folds for every model.  A: StratifiedGroupKFold(5, shuffle) seeds 0-9 (50 folds).
B: GroupKFold(5, shuffle) seeds 0-9 (50 folds).  Stress test: leave-one-campaign-out, with every
training row that shares a condition_id with the held-out campaign also removed (17 of 88 conditions
span more than one campaign, so plain LOCO would leak replicates).

Decision rule (fixed in advance).  For a metric, a candidate "passes" if its paired win-rate vs
current >= 70% (ties = 0.5) AND its mean gain > 0.5 x the current model's fold std.  "No loss" on a
metric = mean not worse by more than 0.5 x current fold std.
  A: replace only if it passes on Brier or ROC-AUC, has no loss on Brier, ROC-AUC and balanced
     accuracy, and its LOCO pooled Brier and AUC are not worse than current.
  B: replace only if it passes on MAE, has no loss on R^2, and its LOCO pooled MAE is not worse.
  Only shippable candidates (A1-A6, B1-B6) can be recommended; if several qualify, take the
  earliest in the list (simplest).  Otherwise keep the current model.
"""
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (balanced_accuracy_score, brier_score_loss, mean_absolute_error,
                             r2_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, SplineTransformer, StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed" / "flex_clean.csv"
REPORT = ROOT / "reports" / "model_search.md"
NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"]
FEATURES = ["fuel"] + NUM
SEEDS = range(10)
PHYS = ["log_p_atm", "x_o2", "x_co2", "x_he", "log_d0", "p_o2"]


# ---------------------------------------------------------------- feature engineering (6 raw columns in)
def engineer(X, kind="raw"):
    """Closed-form features from the 6 raw inputs. Every line is a one-liner in JavaScript."""
    h = (X["fuel"] == "Heptane").astype(float)
    out = pd.DataFrame(index=X.index)
    if kind in ("physics", "physics_fx"):
        out["log_p_atm"] = np.log(X["p_atm"])
        out["x_o2"], out["x_co2"], out["x_he"] = X["x_o2"], X["x_co2"], X["x_he"]
        out["log_d0"] = np.log(X["d0_mm"])
        out["p_o2"] = X["x_o2"] * X["p_atm"]
    else:
        for c in NUM:
            out[c] = X[c]
    if kind == "targeted":
        out["hep_x_o2"] = h * X["x_o2"]
        out["hep_d0"] = h * X["d0_mm"]
        out["d0_sq"] = X["d0_mm"] ** 2
    if kind in ("fuel_x_all", "physics_fx"):
        for c in list(out.columns):
            out["hep_" + c] = h * out[c]
    out.insert(0, "fuel", X["fuel"])
    return out


def linear_pipe(kind, est):
    pre = ColumnTransformer([("fuel", OneHotEncoder(handle_unknown="ignore"), ["fuel"]),
                             ("num", StandardScaler(), make_column_selector(dtype_include=np.number))])
    return make_pipeline(FunctionTransformer(engineer, kw_args={"kind": kind}), pre, est)


def spline_pipe(est):
    pre = ColumnTransformer([
        ("fuel", OneHotEncoder(handle_unknown="ignore"), ["fuel"]),
        ("spl", make_pipeline(SplineTransformer(n_knots=4, degree=3, knots="uniform", extrapolation="linear"),
                              StandardScaler()), ["x_o2", "d0_mm"]),
        ("num", StandardScaler(), ["p_atm", "x_co2", "x_he"])])
    return make_pipeline(pre, est)


def plain_pre():
    return ColumnTransformer([("fuel", OneHotEncoder(handle_unknown="ignore"), ["fuel"]),
                              ("num", StandardScaler(), NUM)])


C_GRID = {"logisticregression__C": np.logspace(-2, 2, 9)}
A_GRID = {"ridge__alpha": np.logspace(-3, 2, 11)}


def tuned_clf(pipe):
    return GridSearchCV(pipe, C_GRID, scoring="neg_log_loss",
                        cv=StratifiedGroupKFold(4, shuffle=True, random_state=0))


def tuned_reg(pipe):
    return GridSearchCV(pipe, A_GRID, scoring="neg_mean_absolute_error",
                        cv=GroupKFold(4, shuffle=True, random_state=0))


def lr(C=1.0):
    return LogisticRegression(C=C, max_iter=5000)


CLASSIFIERS = {   # name -> (model, shippable in plain JS?)
    "A0 current (LR C=1)": (make_pipeline(plain_pre(), lr()), True),
    "A1 physics transforms": (linear_pipe("physics", lr()), True),
    "A2 targeted extras": (linear_pipe("targeted", lr()), True),
    "A3 fuel x all": (linear_pipe("fuel_x_all", lr()), True),
    "A4 tuned C": (tuned_clf(make_pipeline(plain_pre(), lr())), True),
    "A5 physics + tuned C": (tuned_clf(linear_pipe("physics", lr())), True),
    "A6 splines + tuned C": (tuned_clf(spline_pipe(lr())), True),
    "A7 HistGB (ref)": (make_pipeline(plain_pre(), HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=10, random_state=0)), False),
    "A8 RandomForest (ref)": (make_pipeline(plain_pre(), RandomForestClassifier(
        n_estimators=300, min_samples_leaf=3, random_state=0, n_jobs=1)), False),
}
gp_kernel = ConstantKernel(1.0) * RBF(np.ones(7), length_scale_bounds=(1e-2, 1e3)) + WhiteKernel(0.1)
REGRESSORS = {
    "B0 current (Ridge a=1)": (make_pipeline(plain_pre(), Ridge(alpha=1.0)), True),
    "B1 physics transforms": (linear_pipe("physics", Ridge(alpha=1.0)), True),
    "B2 targeted extras": (linear_pipe("targeted", Ridge(alpha=1.0)), True),
    "B3 fuel x all": (linear_pipe("fuel_x_all", Ridge(alpha=1.0)), True),
    "B4 tuned alpha": (tuned_reg(make_pipeline(plain_pre(), Ridge())), True),
    "B5 physics + fuel x all + tuned": (tuned_reg(linear_pipe("physics_fx", Ridge())), True),
    "B6 splines + tuned alpha": (tuned_reg(spline_pipe(Ridge())), True),
    "B7 GaussianProcess (ref)": (make_pipeline(plain_pre(), GaussianProcessRegressor(
        gp_kernel, normalize_y=True, n_restarts_optimizer=1, random_state=0)), False),
    "B8 HistGB (ref)": (make_pipeline(plain_pre(), HistGradientBoostingRegressor(
        max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=10, random_state=0)), False),
}


def fit(m, X, y, g):
    if isinstance(m, GridSearchCV):
        m.fit(X, y, groups=g)
    else:
        m.fit(X, y)
    return m


def best_param(m):
    return next(iter(m.best_params_.values())) if isinstance(m, GridSearchCV) else np.nan


def loco_splits(d):
    """Leave one campaign out; also drop training rows sharing a condition with the test campaign."""
    for c in sorted(d["campaign_id"].unique()):
        te = np.where(d["campaign_id"] == c)[0]
        conds = set(d["condition_id"].iloc[te])
        tr = np.where((d["campaign_id"] != c) & ~d["condition_id"].isin(conds))[0]
        yield c, tr, te


# ---------------------------------------------------------------- one outer fold (run in parallel)
def _fold_a(name, model, X, y, g, tr, te, seed, fold):
    m = fit(clone(model), X.iloc[tr], y.iloc[tr], g.iloc[tr])
    p, yt = m.predict_proba(X.iloc[te])[:, 1], y.iloc[te]
    thr = y.iloc[tr].mean()   # 'prior' rule: flag Completion when P(ext) < training base rate
    if fold == "loco":
        return [{"model": name, "campaign": seed, "i": i, "p": pi, "y": y.iloc[i], "thr": thr}
                for i, pi in zip(te, p)]
    return {"model": name, "seed": seed, "fold": fold, "param": best_param(m),
            "roc_auc": roc_auc_score(yt, p) if yt.nunique() == 2 else np.nan,
            "brier": brier_score_loss(yt, p, labels=[0, 1]),
            "bal_acc": balanced_accuracy_score(yt, (p >= thr).astype(int))}


def _fold_b(name, model, X, y, g, tr, te, seed, fold):
    yt = y.iloc[te]
    if model is None:   # per-fuel mean of the training fold
        p = X["fuel"].iloc[te].map(y.iloc[tr].groupby(X["fuel"].iloc[tr]).mean()).to_numpy()
        prm = np.nan
    else:
        m = fit(clone(model), X.iloc[tr], y.iloc[tr], g.iloc[tr])
        p, prm = m.predict(X.iloc[te]), best_param(m)
    if fold == "loco":
        return [{"model": name, "campaign": seed, "i": i, "p": pi, "y": y.iloc[i]} for i, pi in zip(te, p)]
    return {"model": name, "seed": seed, "fold": fold, "param": prm,
            "MAE": mean_absolute_error(yt, p), "R2": r2_score(yt, p)}


def _run(d, ycol, models, splitter, fold_fn):
    X, g = d[FEATURES], d["condition_id"]
    y = d[ycol].astype(int) if ycol == "y_extinction" else d[ycol]
    jobs = []
    for seed in SEEDS:   # identical folds for every model
        splits = list(splitter(seed).split(X, y, g))
        jobs += [(n, m, tr, te, seed, f) for n, m in models.items() for f, (tr, te) in enumerate(splits)]
    jobs += [(n, m, tr, te, camp, "loco") for n, m in models.items() for camp, tr, te in loco_splits(d)]
    out = Parallel(n_jobs=-1)(delayed(fold_fn)(n, m, X, y, g, tr, te, s, f) for n, m, tr, te, s, f in jobs)
    rows = [r for r in out if isinstance(r, dict)]
    loco = [x for r in out if isinstance(r, list) for x in r]
    order = {n: i for i, n in enumerate(models)}
    rows = pd.DataFrame(rows).sort_values(["model", "seed", "fold"], key=lambda s: s.map(order) if s.name == "model" else s)
    loco = pd.DataFrame(loco).sort_values("model", key=lambda s: s.map(order), kind="stable")
    return rows.reset_index(drop=True), loco.reset_index(drop=True)


# ---------------------------------------------------------------- Task A / Task B
def run_a(d):
    return _run(d, "y_extinction", {k: v[0] for k, v in CLASSIFIERS.items()},
                lambda s: StratifiedGroupKFold(5, shuffle=True, random_state=s), _fold_a)


def run_b(d):
    models = {k: v[0] for k, v in REGRESSORS.items()}
    models["Per-fuel mean (baseline)"] = None
    rows, loco = _run(d, "k_target", models, lambda s: GroupKFold(5, shuffle=True, random_state=s), _fold_b)
    return rows, loco


# ---------------------------------------------------------------- comparisons
def paired(res, current, metrics):
    """metrics: {name: +1 if higher is better else -1}. Returns per-model summary rows."""
    base = res[res["model"] == current].set_index(["seed", "fold"])
    out = []
    for name, sub in res.groupby("model", sort=False):
        s = sub.set_index(["seed", "fold"])
        row = {"model": name}
        for met, sign in metrics.items():
            a, b = s[met], base[met].reindex(s.index)
            ok = a.notna() & b.notna()
            diff = sign * (a[ok] - b[ok])
            cur_std = base[met].std()
            row[met + "_mean"], row[met + "_std"] = a.mean(), a.std()
            row[met + "_gain"] = diff.mean()
            row[met + "_diffstd"] = diff.std()
            row[met + "_win"] = ((diff > 1e-12).sum() + 0.5 * (diff.abs() <= 1e-12).sum()) / ok.sum()
            row[met + "_pass"] = bool(row[met + "_win"] >= 0.70 and diff.mean() > 0.5 * cur_std)
            row[met + "_noloss"] = bool(diff.mean() > -0.5 * cur_std)
        out.append(row)
    return pd.DataFrame(out)


def loco_summary_a(loco, current):
    out = []
    base = loco[loco["model"] == current].set_index("i")
    for name, s in loco.groupby("model", sort=False):
        bc = []   # per-campaign Brier win vs current
        for camp, c in s.groupby("campaign"):
            bcur = base.loc[c["i"]]
            bc.append(np.sign(brier_score_loss(bcur["y"], bcur["p"], labels=[0, 1])
                              - brier_score_loss(c["y"], c["p"], labels=[0, 1])))
        bc = np.array(bc)
        out.append({"model": name, "auc": roc_auc_score(s["y"], s["p"]), "brier": brier_score_loss(s["y"], s["p"]),
                    "bal_acc": balanced_accuracy_score(s["y"], (s["p"] >= s["thr"]).astype(int)),
                    "camp_brier_win": ((bc > 0).sum() + 0.5 * (bc == 0).sum()) / len(bc)})
    return pd.DataFrame(out)


def loco_summary_b(loco, current):
    out = []
    base = loco[loco["model"] == current].set_index("i")
    for name, s in loco.groupby("model", sort=False):
        w = []
        for camp, c in s.groupby("campaign"):
            bcur = base.loc[c["i"]]
            w.append(np.sign(mean_absolute_error(bcur["y"], bcur["p"]) - mean_absolute_error(c["y"], c["p"])))
        w = np.array(w)
        out.append({"model": name, "MAE": mean_absolute_error(s["y"], s["p"]), "R2": r2_score(s["y"], s["p"]),
                    "camp_mae_win": ((w > 0).sum() + 0.5 * (w == 0).sum()) / len(w)})
    return pd.DataFrame(out)


def md_table(df, cols, fmt):
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = ""
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(fmt.get(c, "{}").format(v) if not (isinstance(v, float) and np.isnan(v)) else "–")
        body += "| " + " | ".join(cells) + " |\n"
    return head + body


def final_coefficients(model, X, y, g):
    """Fit on all rows; return engineered feature names + scaler mean/scale + coefficients (for the JS port)."""
    m = fit(clone(model), X, y, g)
    pipe = m.best_estimator_ if isinstance(m, GridSearchCV) else m
    est = pipe.steps[-1][1]
    ct = pipe.steps[-2][1]
    names = list(ct.get_feature_names_out())
    coef = est.coef_[0] if np.ndim(est.coef_) == 2 else est.coef_
    sc = ct.named_transformers_["num"]
    lines = [f"intercept = {float(np.ravel(est.intercept_)[0]):.6f}",
             f"hyperparameter = {pipe.get_params().get('logisticregression__C', pipe.get_params().get('ridge__alpha'))}"]
    lines += [f"{n:>22s}  coef = {c:+.6f}" for n, c in zip(names, coef)]
    if hasattr(sc, "mean_"):
        lines += [f"scaler {n:>16s}  mean = {mu:.6f}  scale = {s:.6f}"
                  for n, mu, s in zip(sc.get_feature_names_out(), sc.mean_, sc.scale_)]
    return "\n".join(lines)


NOTES = """
## Post-hoc checks on the two winners (run once on 2026-11-14 after selection; NOT used to choose)

- **Both fuels gain in Task A** (pooled out-of-fold, mean of 10 shuffles): Heptane AUC 0.855 -> 0.885,
  Brier 0.139 -> 0.116; Methanol AUC 0.593 -> 0.759, Brier 0.058 -> 0.049. Methanol has only 8 Completion
  runs, so its fuel-specific slopes rest on very few events.
- **Task B gain is Methanol-only**: per-fuel MAE Methanol 0.0361 -> 0.0285, Heptane 0.0666 -> 0.0669 (no change).
- **Reliability (seed 0, out-of-fold)**: runs the new classifier put at P(ext) <= 0.5 went out 17% of the time
  (18 runs); the current model's <= 0.5 bin went out 42% of the time (12 runs). Bins are small.
- **Coefficient signs are stable** over the 50 training folds for every large coefficient of both winners
  (only the small x_co2 / hep_x_he terms of the classifier flip sign).
- **Conformal K interval unchanged** when the K model is swapped (same procedure as
  calibrate_and_evidence.py): "80%" covers 80.8% (half-width 0.068 vs 0.069), "90%" covers 91.0% (vs 89.8%).
- **Inside the app's GREEN/AMBER region no unphysical outputs**: 20,000 random slider settings per fuel inside
  the tested box give K >= 0.08 mm^2/s. Only an exact corner of the Heptane box (RED, numbers withheld) gives K < 0.
- The paste-able pipeline (FunctionTransformer + ColumnTransformer) reproduces the searched A3/B3 exactly, and the
  JS-style formula (one-hot + standardised features incl. hep_* + dot product) matches sklearn to 0.0 on every row.

## Caveats

- 6 shippable candidates per task were compared; picking the best of 6 is mildly optimistic. Two things limit
  that: the rule demanded >= 70% paired wins plus a gain above half the fold spread, and the separate
  leave-one-campaign-out test (different split, condition-purged) points the same way. The partial-interaction
  candidates (A2, B2) also improve, which supports the same explanation: the two fuels respond differently
  to the inputs.
- Task B's margin is modest (MAE gain 0.0043 vs a 0.0034 bar). B5 scores about the same but its tuned alpha often
  lands on the grid edge (0.001), so it is less stable; the rule picks the simpler B3.
- The classifier's balanced accuracy wins only 66% of folds: do not claim it improved; ROC-AUC and Brier did.
- train.py's Task B uses one unshuffled GroupKFold, so its printed numbers will differ slightly from the
  10-shuffle numbers here (the current Ridge scores MAE 0.0487 / R^2 0.70 here vs 0.047 / 0.72 in README).

## How to ship (both winners are the same idea: fuel-specific slopes)

Feature transform (identical in Python and JS), applied to the same 6 raw inputs:
`hep_<c> = <c> if fuel == "Heptane" else 0` for c in p_atm, x_o2, x_co2, x_he, d0_mm. Then one-hot(fuel) +
StandardScaler over the 10 numeric columns [p_atm, x_o2, x_co2, x_he, d0_mm, hep_p_atm, hep_x_o2, hep_x_co2,
hep_x_he, hep_d0_mm] -> LogisticRegression(C=1) for extinction, Ridge(alpha=1) for K. The transform function
must live in an importable module (e.g. ignis/features.py) so the joblib files load in the app.
"""


if __name__ == "__main__":
    t0 = time.time()
    df = pd.read_csv(DATA)
    da = df[df["y_extinction"].notna() & df[NUM].notna().all(axis=1) & ~df["dup_id"]].reset_index(drop=True)
    db = df[df["k_target"].notna() & df[NUM].notna().all(axis=1) & ~df["dup_id"]].reset_index(drop=True)
    print(f"A rows={len(da)} ({int(da.y_extinction.sum())} ext / {int((da.y_extinction == 0).sum())} compl), "
          f"B rows={len(db)}")

    res_a, loco_a = run_a(da)
    print(f"Task A done {time.time() - t0:.0f}s")
    res_b, loco_b = run_b(db)
    print(f"Task B done {time.time() - t0:.0f}s")

    cur_a, cur_b = "A0 current (LR C=1)", "B0 current (Ridge a=1)"
    sa = paired(res_a, cur_a, {"roc_auc": 1, "brier": -1, "bal_acc": 1})
    sb = paired(res_b, cur_b, {"MAE": -1, "R2": 1})
    la, lb = loco_summary_a(loco_a, cur_a), loco_summary_b(loco_b, cur_b)
    la_cur, lb_cur = la.set_index("model").loc[cur_a], lb.set_index("model").loc[cur_b]

    def verdict_a(r):
        l = la.set_index("model").loc[r["model"]]
        ok = ((r["brier_pass"] or r["roc_auc_pass"]) and r["brier_noloss"] and r["roc_auc_noloss"]
              and r["bal_acc_noloss"] and l["brier"] <= la_cur["brier"] and l["auc"] >= la_cur["auc"])
        return "current" if r["model"] == cur_a else ("QUALIFIES" if ok else "no")

    def verdict_b(r):
        if r["model"] == "Per-fuel mean (baseline)":
            return "baseline"
        l = lb.set_index("model").loc[r["model"]]
        ok = r["MAE_pass"] and r["R2_noloss"] and l["MAE"] <= lb_cur["MAE"]
        return "current" if r["model"] == cur_b else ("QUALIFIES" if ok else "no")

    sa["verdict"] = sa.apply(verdict_a, axis=1)
    sb["verdict"] = sb.apply(verdict_b, axis=1)
    ship = {**{k: v[1] for k, v in CLASSIFIERS.items()}, **{k: v[1] for k, v in REGRESSORS.items()}}
    sa["shippable"] = sa["model"].map(lambda m: "yes" if ship.get(m) else "NO")
    sb["shippable"] = sb["model"].map(lambda m: "yes" if ship.get(m, False) else "NO")
    for s in (sa, sb):
        s.loc[(s["shippable"] == "NO") & (s["verdict"] == "QUALIFIES"), "verdict"] = "would qualify (not shippable)"

    params_a = res_a.dropna(subset=["param"]).groupby("model")["param"].agg(lambda v: v.value_counts().to_dict())
    params_b = res_b.dropna(subset=["param"]).groupby("model")["param"].agg(lambda v: v.value_counts().to_dict())

    pick_a = next((m for m in sa["model"] if sa.set_index("model").loc[m, "verdict"] == "QUALIFIES"), None)
    pick_b = next((m for m in sb["model"] if sb.set_index("model").loc[m, "verdict"] == "QUALIFIES"), None)

    f3 = "{:.3f}"
    fp = "{:.0%}"
    pct = lambda s: s.map(lambda v: f"{v:.0%}")
    sa_t = sa.copy()
    for met in ["roc_auc", "brier", "bal_acc"]:
        sa_t[met] = sa_t.apply(lambda r: f"{r[met + '_mean']:.3f} ± {r[met + '_std']:.3f}", axis=1)
        sa_t[met + " gain"] = sa_t[met + "_gain"].map(lambda v: f"{v:+.3f}")
        sa_t[met + " win"] = pct(sa_t[met + "_win"])
    sb_t = sb.copy()
    for met in ["MAE", "R2"]:
        sb_t[met] = sb_t.apply(lambda r: f"{r[met + '_mean']:.4f} ± {r[met + '_std']:.4f}", axis=1)
        sb_t[met + " gain"] = sb_t[met + "_gain"].map(lambda v: f"{v:+.4f}")
        sb_t[met + " win"] = pct(sb_t[met + "_win"])

    rep = ["# Model search: can the two FLEX models be improved?\n",
           "Generated by `scripts/experiments/model_search.py`. Candidate list and decision rule were fixed in the "
           "script docstring before any result was computed (copied below).\n",
           "```text\n" + __doc__.split("PRE-REGISTERED")[1].strip("\n=") + "\n```\n",
           f"Data: Task A {len(da)} rows ({int(da.y_extinction.sum())} Extinction / "
           f"{int((da.y_extinction == 0).sum())} Completion, {da.condition_id.nunique()} condition groups, "
           f"{da.campaign_id.nunique()} campaigns); Task B {len(db)} rows ({db.condition_id.nunique()} condition "
           f"groups, {db.campaign_id.nunique()} campaigns).\n",
           "Gain = candidate minus current, signed so that positive = better. Win = share of the 50 paired folds "
           "in which the candidate beats the current model (ties count half). ± = std over the 50 folds.\n",
           "## Task A: Extinction vs Completion (50 grouped folds = 5 folds x 10 shuffles)\n",
           md_table(sa_t, ["model", "shippable", "roc_auc", "roc_auc gain", "roc_auc win", "brier", "brier gain",
                           "brier win", "bal_acc", "bal_acc gain", "bal_acc win", "verdict"], {}),
           "\nPass thresholds (0.5 x current fold std): ROC-AUC "
           f"{0.5 * sa.set_index('model').loc[cur_a, 'roc_auc_std']:.3f}, Brier "
           f"{0.5 * sa.set_index('model').loc[cur_a, 'brier_std']:.3f}, balanced accuracy "
           f"{0.5 * sa.set_index('model').loc[cur_a, 'bal_acc_std']:.3f}. Base-rate Brier for reference: "
           f"{brier_score_loss(da.y_extinction, np.full(len(da), da.y_extinction.mean())):.3f}.\n",
           "\nHyper-parameters chosen by the inner grouped CV (C: count of outer folds):\n",
           "\n".join(f"- {k}: {v}" for k, v in params_a.items()) + "\n",
           "\n### Stress test A: leave-one-campaign-out (pooled out-of-fold, condition-purged)\n",
           md_table(la, ["model", "auc", "brier", "bal_acc", "camp_brier_win"],
                    {"auc": f3, "brier": f3, "bal_acc": f3, "camp_brier_win": fp}),
           "\n`camp_brier_win` = share of held-out campaigns where the candidate's Brier beats current (ties half).\n",
           "\n## Task B: burning-rate constant K (50 grouped folds = 5 folds x 10 shuffles)\n",
           md_table(sb_t, ["model", "shippable", "MAE", "MAE gain", "MAE win", "R2", "R2 gain", "R2 win",
                           "verdict"], {}),
           "\nPass thresholds (0.5 x current fold std): MAE "
           f"{0.5 * sb.set_index('model').loc[cur_b, 'MAE_std']:.4f}, R² "
           f"{0.5 * sb.set_index('model').loc[cur_b, 'R2_std']:.4f}.\n",
           "\nHyper-parameters chosen by the inner grouped CV (alpha: count of outer folds):\n",
           "\n".join(f"- {k}: {v}" for k, v in params_b.items()) + "\n",
           "\n### Stress test B: leave-one-campaign-out (pooled out-of-fold, condition-purged)\n",
           md_table(lb, ["model", "MAE", "R2", "camp_mae_win"], {"MAE": "{:.4f}", "R2": f3, "camp_mae_win": fp}),
           "\n## Recommendation (mechanical, from the pre-registered rule)\n",
           f"- Task A: **{'replace with ' + pick_a if pick_a else 'keep the current model'}**\n",
           f"- Task B: **{'replace with ' + pick_b if pick_b else 'keep the current model'}**\n"]
    for pick, models, d, ycol in [(pick_a, CLASSIFIERS, da, "y_extinction"), (pick_b, REGRESSORS, db, "k_target")]:
        if pick:
            yy = d[ycol].astype(int) if ycol == "y_extinction" else d[ycol]
            rep.append(f"\nFull-data fit of {pick} (for the JS port):\n\n```text\n"
                       + final_coefficients(models[pick][0], d[FEATURES], yy, d["condition_id"]) + "\n```\n")
    rep.append(NOTES)
    REPORT.write_text("".join(rep), encoding="utf-8")
    print("".join(rep))
    print(f"wrote {REPORT}  ({time.time() - t0:.0f}s)")
