"""Safety page history tabs: every fact carries a source, links go to real pages, the news source is marked."""
from pathlib import Path

from ignis.safety import EXTINGUISHERS, INCIDENTS, ISS_RESPONSE, ISS_RESPONSE_SRC, PRACTICE, SOURCES

ROOT = Path(__file__).resolve().parents[1]


def test_every_item_is_sourced():
    keys = set(ISS_RESPONSE_SRC)
    for item in EXTINGUISHERS + INCIDENTS + PRACTICE:
        assert item["src"], item
        keys |= set(item["src"])
    assert keys <= set(SOURCES), keys - set(SOURCES)
    assert all(url.startswith("https://") for _, url in SOURCES.values())
    assert set(SOURCES) <= keys, "unused source"


def test_items_are_complete_and_ordered():
    assert [i["year"] for i in INCIDENTS] == sorted(i["year"] for i in INCIDENTS)
    for inc in INCIDENTS:
        assert inc["what"] and inc["why"] and inc["changed"] and inc["link"] and inc["when"]
        if inc["explore"]:
            assert (ROOT / inc["explore"][0]).is_file()
    for ex in EXTINGUISHERS:
        assert all(ex[k] for k in ("name", "space", "earth", "how", "cabin"))
    assert len(ISS_RESPONSE) >= 5 and all(step and text for step, text in ISS_RESPONSE)


def test_non_nasa_news_is_labelled():
    assert SOURCES["elektron"][0].lower().startswith("news report")
    assert "news report" in next(i for i in INCIDENTS if i["src"] == ["elektron"])["when"]
