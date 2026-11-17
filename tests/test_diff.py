"""Unit and integration tests for diff.py in german-schreiben-flashcards."""

import json
from pathlib import Path
import pytest

from diff import (
    extract_candidates_from_text,
    is_duplicate,
    load_deck,
    normalize_text,
    run_diff,
    split_into_sentences,
    strip_edge_punctuation,
)


@pytest.fixture
def sample_essay_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_essay.md"


@pytest.fixture
def mock_deck_file(tmp_path: Path) -> Path:
    deck_path = tmp_path / "deck.txt"
    content = (
        "#separator:tab\n"
        "#html:true\n"
        "#guid column:1\n"
        "#notetype:Cloze\n"
        "#deck:german-generated::german-schreiben\n"
        "#tags column:4\n"
        "1111222233334444\t"
        '<div style="font-size:1.2em;color:#2e9d5c;margin-bottom:0.8em">Definition</div>'
        "<div>Doch ein weiterer Bereich, dem wir unsere {{c1::Aufmerksamkeit widmen}} sollten.</div>\t"
        "<b>Aufmerksamkeit widmen</b><br><span style=\"color:#888\">[+ Dat]</span>\t"
        "german-schreiben\n"
        "5555666677778888\t"
        '<div style="font-size:1.2em;color:#2e9d5c;margin-bottom:0.8em">Etwas berücksichtigen</div>'
        "<div>Wir müssen diesen Faktor {{c1::in Betracht ziehen}}.</div>\t"
        "<b>in Betracht ziehen</b>\t"
        "german-schreiben\n"
    )
    deck_path.write_text(content, encoding="utf-8")
    return deck_path


def test_strip_edge_punctuation():
    assert strip_edge_punctuation("Ernährung,") == "Ernährung"
    assert strip_edge_punctuation("»Aufmerksamkeit widmen«") == "Aufmerksamkeit widmen"
    assert (
        strip_edge_punctuation("diese Schwierigkeiten zu überwinden und die Vorteile zu nutzen.")
        == "diese Schwierigkeiten zu überwinden und die Vorteile zu nutzen"
    )
    assert strip_edge_punctuation("...deutlich kostengünstiger als...") == "deutlich kostengünstiger als"
    assert strip_edge_punctuation(" :;--Test--:; ") == "Test"


def test_sentence_splitting_with_abbreviations():
    text = (
        "Beispielsweise ist der Einsatz von Straßenbahnen deutlich kostengünstiger als der von PKWs. "
        "Straßenbahnen können viele Passagiere befördern. Das gilt z.B. für alle Großstädte."
    )
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert "PKWs." in sentences[0]
    assert "z.B." in sentences[2]


def test_extract_candidates_from_text():
    text = "Doch ein weiterer Bereich, **dem wir unsere Aufmerksamkeit widmen sollten**, ist der nachhaltige Verkehr."
    candidates, count = extract_candidates_from_text(text)
    assert count == 1
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["marked_phrase"] == "dem wir unsere Aufmerksamkeit widmen sollten"
    assert cand["raw_sentence"] == (
        "Doch ein weiterer Bereich, dem wir unsere Aufmerksamkeit widmen sollten, ist der nachhaltige Verkehr."
    )
    start, end = cand["span"]
    assert cand["raw_sentence"][start:end] == cand["marked_phrase"]


def test_extract_candidates_underscore_and_multiple():
    text = "Um die **Klimakrise** zu verhindern, sollten auch __Einzelpersonen__ handeln."
    candidates, count = extract_candidates_from_text(text)
    assert count == 1
    assert len(candidates) == 2
    assert candidates[0]["marked_phrase"] == "Klimakrise"
    assert candidates[1]["marked_phrase"] == "Einzelpersonen"
    assert candidates[0]["raw_sentence"] == "Um die Klimakrise zu verhindern, sollten auch Einzelpersonen handeln."
    assert candidates[1]["raw_sentence"] == "Um die Klimakrise zu verhindern, sollten auch Einzelpersonen handeln."


def test_load_deck(mock_deck_file: Path):
    existing_collocations, existing_sentence_collocations = load_deck(mock_deck_file)
    assert "aufmerksamkeit widmen" in existing_collocations
    assert "in betracht ziehen" in existing_collocations
    assert len(existing_sentence_collocations) == 2


def test_is_duplicate_rules(mock_deck_file: Path):
    existing_collocations, existing_sentence_collocations = load_deck(mock_deck_file)

    # 1. Exact collocation already in deck -> duplicate
    cand_dup1 = {
        "marked_phrase": "Aufmerksamkeit widmen",
        "raw_sentence": "In einem völlig anderen Satz wollen wir Aufmerksamkeit widmen.",
    }
    assert is_duplicate(cand_dup1, existing_collocations, existing_sentence_collocations) is True

    # 2. Distinct collocation from same carrier sentence -> not duplicate if collocation unseen
    cand_distinct = {
        "marked_phrase": "nachhaltige Mobilität",
        "raw_sentence": "Doch ein weiterer Bereich, dem wir unsere Aufmerksamkeit widmen sollten.",
    }
    assert is_duplicate(cand_distinct, existing_collocations, existing_sentence_collocations) is False

    # 3. Completely new unseen candidate -> not duplicate
    cand_new = {
        "marked_phrase": "zur Folge haben",
        "raw_sentence": "Dies wird unabsehbare Konsequenzen zur Folge haben.",
    }
    assert is_duplicate(cand_new, existing_collocations, existing_sentence_collocations) is False


def test_run_diff_e2e(sample_essay_path: Path, mock_deck_file: Path, tmp_path: Path, capsys):
    out_file = tmp_path / "unseen-candidates.json"
    summary = run_diff(
        notes_path=sample_essay_path,
        deck_path=mock_deck_file,
        out_path=out_file,
        verbose=True,
    )

    captured = capsys.readouterr().out
    assert "in essay:" in captured
    assert "candidate bold spans:" in captured
    assert "already in deck:" in captured
    assert "unseen:" in captured

    assert summary["candidate_spans"] > 0
    assert summary["unseen"] > 0
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == summary["unseen"]
    for item in data:
        assert "raw_sentence" in item
        assert "marked_phrase" in item
        assert "span" in item
        s, e = item["span"]
        assert item["raw_sentence"][s:e] == item["marked_phrase"]


def test_force_accepted_override(sample_essay_path: Path, mock_deck_file: Path, tmp_path: Path):
    out_file = tmp_path / "unseen.json"
    # Even if 'Aufmerksamkeit widmen' is in deck, force_accepted includes it
    summary = run_diff(
        notes_path=sample_essay_path,
        deck_path=mock_deck_file,
        out_path=out_file,
        force_accepted=["Aufmerksamkeit widmen"],
    )
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    phrases = [d["marked_phrase"] for d in data]
    # Check if phrase is present in unseen candidates
    assert any("Aufmerksamkeit widmen" in p for p in phrases)
