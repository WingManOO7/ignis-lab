"""Startup self-check (ignis/selfcheck.py): passes on the real repo; missing files, unloadable models and a
scikit-learn version mismatch give one clear message with the fixing command, never an exception."""
import shutil
from pathlib import Path

import pytest

from ignis import selfcheck
from ignis.selfcheck import REQUIRED, Problem, problem_message, run_checks

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_root(tmp_path):
    """A copy of the app's required files: real models, empty placeholders for the data files."""
    shutil.copytree(ROOT / "models", tmp_path / "models")
    for rel in REQUIRED:
        dest = tmp_path / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("placeholder", encoding="utf-8")
    return tmp_path


def test_real_repo_passes():
    assert run_checks() == []


def test_copy_with_everything_passes(fake_root):
    assert run_checks(fake_root) == []


@pytest.mark.parametrize("rel, fix", [("data/processed/flex_clean.csv", "python scripts/run_all.py"),
                                      ("data/docs_index/chunks.json", "python scripts/run_all.py --docs"),
                                      ("reports/cv_folds.csv", "python scripts/run_all.py"),
                                      ("models/k_interval.joblib", "python scripts/run_all.py")])
def test_missing_file_is_reported_with_its_fix(fake_root, rel, fix):
    (fake_root / rel).unlink()
    problems = run_checks(fake_root)
    assert [p.what for p in problems] == [f"Missing `{rel}`."]
    msg = problem_message(problems)
    assert rel in msg and f"`{fix}`" in msg and "cannot start: 1 problem " in msg


def test_sklearn_version_mismatch_is_reported():
    problems = run_checks(ROOT, sklearn_version="0.0.1")
    saved = {p.what.split("`")[1] for p in problems}
    assert {"models/extinction_clf.joblib", "models/k_reg.joblib"} <= saved      # both carry meta.sklearn_version
    assert all("but scikit-learn 0.0.1 is installed" in p.what for p in problems)
    msg = problem_message(problems)
    assert "pip install -r requirements.txt" in msg and "python scripts/run_all.py" in msg
    assert msg.count("pip install -r requirements.txt") == 1                     # each fix listed once


def test_unloadable_model_is_reported_not_raised(fake_root):
    (fake_root / "models" / "k_reg.joblib").write_bytes(b"not a pickle")
    problems = run_checks(fake_root)
    assert len(problems) == 1 and "`models/k_reg.joblib` could not be loaded" in problems[0].what


def test_check_never_raises(monkeypatch):
    def boom():
        raise RuntimeError("no sklearn")
    monkeypatch.setattr(selfcheck, "_installed_sklearn", boom)
    problems = run_checks(ROOT)
    assert len(problems) == 1 and "self-check itself failed" in problems[0].what


# ---------------------------------------------------------------- 3D lab assets (offline three.js, full-screen page)
def test_vendored_threejs_matches_the_pinned_hashes():
    import base64
    import hashlib
    from ignis.simulation import THREE_DIR, THREE_FILES, THREE_VERSION
    assert THREE_VERSION == "0.160.0" and (THREE_DIR / "LICENSE").read_text(encoding="utf-8").startswith("The MIT License")
    for rel, sri in THREE_FILES.items():
        data = (THREE_DIR / rel).read_bytes().replace(b"\r\n", b"\n")      # tolerate a CRLF checkout
        assert "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode() == sri, rel
    assert b"REVISION = '160'" in (THREE_DIR / "build/three.module.js").read_bytes()


def test_scene_imports_only_vendored_modules():
    import re
    from ignis.simulation import TEMPLATE, THREE_FILES
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'type="importmap"' not in html.split("<body>")[0]          # the loader writes the import map
    for name in re.findall(r'"(EffectComposer|RenderPass|UnrealBloomPass|OutputPass)"', html):
        assert f"examples/jsm/postprocessing/{name}.js" in THREE_FILES
    for spec in re.findall(r'import\("three/addons/([^"`]+)"\)', html):
        assert "examples/jsm/" + spec in THREE_FILES


def test_three_config_and_injection(models_cached):
    from ignis.simulation import THREE_CDN_URL, THREE_PLACEHOLDER, build_html, three_config, web_model_payload
    cfg = three_config(static_serving=True)
    assert cfg["local"] == "app/static/vendor/three-0.160.0/" and cfg["cdn"] == THREE_CDN_URL
    assert three_config(static_serving=False)["local"] is None                 # straight to the CDN
    html = build_html({"scenario": "x"}, web_model_payload(models_cached), three=cfg)
    assert THREE_PLACEHOLDER not in html and '"local": "app/static/vendor/three-0.160.0/"' in html
    assert "sha384-" in html and 'id="ignis-main"' in html


def test_voice_is_opt_in():
    from ignis.simulation import TEMPLATE
    html = TEMPLATE.read_text(encoding="utf-8")
    assert '>Voice off</button>' in html and 'voice: URLQ.get("voice") === "1"' in html


def test_fire_lab_page_is_written_once_and_offline_ready(models_cached, tmp_path):
    from ignis.simulation import FIRE_LAB_URL, ensure_fire_lab_page, fire_lab_url
    page = tmp_path / "static" / "fire_lab.html"
    assert ensure_fire_lab_page(models_cached, path=page) is True
    assert ensure_fire_lab_page(models_cached, path=page) is False          # up to date: no rewrite
    html = page.read_text(encoding="utf-8")
    assert '"local": "vendor/three-0.160.0/"' in html and "/*__IGNIS_" not in html
    url = fire_lab_url({"fuel": "Methanol", "x_o2": 0.3, "p_atm": 1.0, "d0_mm": 2.5, "x_co2": 0.2}, place="chamber")
    assert url.startswith(FIRE_LAB_URL + "?") and "fuel=Methanol" in url and "co2=0.200" in url and "he=" not in url


@pytest.fixture(scope="module")
def models_cached():
    from ignis.data import load_models
    return load_models()


def test_app_shows_one_error_and_stops(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(selfcheck, "run_checks", lambda: [Problem("Missing `reports/cv_folds.csv`.",
                                                                   "python scripts/run_all.py")])
    selfcheck.startup_problems.clear()
    try:
        at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
        assert not at.exception
        assert len(at.error) == 1 and "reports/cv_folds.csv" in at.error[0].value
        assert "python scripts/run_all.py" in at.error[0].value
        assert len(at.markdown) == 0 or all("Mission" not in m.value for m in at.markdown)   # no page ran
    finally:
        selfcheck.startup_problems.clear()
