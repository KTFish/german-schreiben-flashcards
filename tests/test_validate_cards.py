"""Unit and integration tests for validate_cards.py in german-schreiben-flashcards."""

import json
from pathlib import Path
import pytest

from validate_cards import (
    check_anti_leakage,
    extract_semantic_heads,
    format_tsv_row,
    generate_guid,
    strip_german_inflection,
    validate_and_append_cards,
)


def test_strip_german_inflection():
    # Verb stems
    assert strip_german_inflection("betrachten") == "betracht"
    assert strip_german_inflection("widmen") == "widm"
    assert strip_german_inflection("stellen") == "stell"
    assert strip_german_inflection("folgen") == "folg"

    # Nouns & suffixes
    assert strip_german_inflection("Aufmerksamkeit") == "aufmerksam"
    assert strip_german_inflection("Folge") == "folg"
    assert strip_german_inflection("Folgen") == "folg"
    assert strip_german_inflection("Beweis") == "beweis"
    assert strip_german_inflection("Entscheidung") == "entscheid"


def test_extract_semantic_heads():
    # Exclude prepositions and auxiliaries
    heads1 = extract_semantic_heads("zur Folge haben")
    assert heads1 == ["Folge"]

    heads2 = extract_semantic_heads("in Betracht ziehen")
    assert heads2 == ["Betracht", "ziehen"]

    heads3 = extract_semantic_heads("unter Beweis stellen")
    assert heads3 == ["Beweis", "stellen"]

    # When all words are stop words, return all
    heads4 = extract_semantic_heads("sondern auch")
    assert heads4 == ["sondern", "auch"]


def test_anti_leakage_flagging_betrachten_for_betracht():
    # Flagging betrachten for in Betracht ziehen
    violations = check_anti_leakage(
        collocation="in Betracht ziehen",
        definition="Etwas genau betrachten und abwägen.",
    )
    assert len(violations) > 0
    assert any("betracht" in v[1] for v in violations)


def test_anti_leakage_flagging_folge_for_zur_folge_haben():
    # Flagging Folge for zur Folge haben
    violations = check_anti_leakage(
        collocation="zur Folge haben",
        definition="Dass etwas eine bestimmte Folge mit sich bringt.",
    )
    assert len(violations) > 0
    assert any("folg" in v[1] for v in violations)


def test_anti_leakage_ignoring_auxiliary_haben():
    # Auxiliary 'haben' in definition for 'zur Folge haben' must NOT be flagged
    violations = check_anti_leakage(
        collocation="zur Folge haben",
        definition="Als Konsequenz bewirken, dass etwas Bestimmtes geschieht und eine Wirkung hat.",
    )
    assert len(violations) == 0


def test_anti_leakage_clean_definitions():
    v1 = check_anti_leakage(
        collocation="Aufmerksamkeit widmen",
        definition="Sich intensiv auf eine bestimmte Sache oder Person konzentrieren.",
    )
    assert len(v1) == 0

    v2 = check_anti_leakage(
        collocation="unter Beweis stellen",
        definition="In der Praxis zeigen, dass man eine bestimmte Fähigkeit besitzt.",
    )
    assert len(v2) == 0


def test_guid_generation():
    guid1 = generate_guid("Aufmerksamkeit widmen", "Dem sollten wir Aufmerksamkeit widmen.")
    guid2 = generate_guid("Aufmerksamkeit widmen", "Dem sollten wir Aufmerksamkeit widmen.")
    assert len(guid1) == 16
    assert guid1 == guid2
    assert all(c in "0123456789abcdef" for c in guid1)


def test_format_tsv_row():
    card = {
        "guid": "f82b7c41a90e43d1",
        "definition": "Sich intensiv auf eine Sache konzentrieren.",
        "cloze_sentence": "Wir sollten dem Thema {{c1::Aufmerksamkeit widmen}}.",
        "collocation": "Aufmerksamkeit widmen",
        "valency": "[+ Dat | Funktionsverbgefüge]",
        "en": "to pay attention to",
        "pl": "poświęcić uwagę",
        "tags": ["german-schreiben", "schreiben::c1"],
    }
    row = format_tsv_row(card)
    parts = row.strip("\n").split("\t")
    assert len(parts) == 4
    assert parts[0] == "f82b7c41a90e43d1"
    assert '<div style="font-size:1.2em;color:#2e9d5c;margin-bottom:0.8em">' in parts[1]
    assert "{{c1::Aufmerksamkeit widmen}}" in parts[1]
    assert "<b>Aufmerksamkeit widmen</b>" in parts[2]
    assert '<span style="color:#888">[+ Dat | Funktionsverbgefüge]</span>' in parts[2]
    assert "EN: to pay attention to<br>PL: poświęcić uwagę" in parts[2]
    assert parts[3] == "german-schreiben schreiben::c1"


def test_validate_and_append_cards_success(tmp_path: Path):
    draft_file = tmp_path / "draft-cards.json"
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(
        "#separator:tab\n#html:true\n#guid column:1\n#notetype:Cloze\n#deck:german-generated::german-schreiben\n#tags column:4\n",
        encoding="utf-8",
    )

    cards = [
        {
            "guid": "f82b7c41a90e43d1",
            "definition": "Sich intensiv auf eine Sache konzentrieren.",
            "cloze_sentence": "Wir sollten dem Thema {{c1::Aufmerksamkeit widmen}}.",
            "collocation": "Aufmerksamkeit widmen",
            "valency": "[+ Dat]",
            "en": "to dedicate attention",
            "pl": "poświęcić uwagę",
            "tags": ["german-schreiben", "schreiben::c1"],
        }
    ]
    draft_file.write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")

    result = validate_and_append_cards(draft_file, deck_file)
    assert len(result) == 1

    content = deck_file.read_text(encoding="utf-8")
    assert "f82b7c41a90e43d1" in content
    assert "Aufmerksamkeit widmen" in content


def test_validate_and_append_cards_failure_on_leakage(tmp_path: Path):
    draft_file = tmp_path / "draft-cards.json"
    deck_file = tmp_path / "deck.txt"

    leaked_cards = [
        {
            "definition": "Etwas genau betrachten und abwägen.",  # leaks 'betracht'
            "cloze_sentence": "Wir müssen das {{c1::in Betracht ziehen}}.",
            "collocation": "in Betracht ziehen",
            "en": "to take into consideration",
            "pl": "brać pod uwagę",
        }
    ]
    draft_file.write_text(json.dumps(leaked_cards, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="Leaked semantic stem"):
        validate_and_append_cards(draft_file, deck_file)

    # Verify nothing was appended
    if deck_file.exists():
        assert "in Betracht ziehen" not in deck_file.read_text(encoding="utf-8")
