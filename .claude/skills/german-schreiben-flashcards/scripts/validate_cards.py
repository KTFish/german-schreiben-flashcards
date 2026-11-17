#!/usr/bin/env python3
"""Stage 3: Anti-Leakage Validation & TSV Assembly for German Schreiben Flashcards.

Validates cards in draft-cards.json against anti-leakage rules on semantic heads,
formats Cloze TSV rows, assigns deterministic 16-hex GUIDs, and appends valid
rows to deck.txt.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

STOPWORDS: Set[str] = {
    # High-frequency functional auxiliaries & modals
    "haben", "hat", "hatte", "gehabt", "hast", "habt", "hätte", "hätten",
    "sein", "ist", "war", "sind", "seid", "gewesen", "bin", "bist", "wäre", "wären",
    "werden", "wird", "wurde", "geworden", "werdet", "wirst", "würde", "würden",
    "lassen", "lässt", "ließ", "gelassen",
    "können", "kann", "konnte", "gekonnt", "könnte", "könnten",
    "müssen", "muss", "musste", "gemusst", "müsste", "müssten",
    "sollen", "soll", "sollte", "gesollt", "sollten",
    "wollen", "will", "wollte", "gewollt", "wollten",
    "dürfen", "darf", "durfte", "gedurft", "dürfte", "dürften",
    "mögen", "mag", "mochte", "gemocht", "möchte", "möchten",
    # Prepositions & contractions
    "in", "im", "ins", "an", "am", "ans", "auf", "aufs", "aus", "bei", "beim",
    "mit", "nach", "von", "vom", "zu", "zum", "zur", "über", "unter", "vor",
    "zwischen", "durch", "für", "fürs", "gegen", "ohne", "um", "ums", "wider",
    "ab", "außer", "neben", "hinter", "seit",
    # Articles & basic pronouns
    "der", "die", "das", "dem", "den", "des",
    "ein", "eine", "einer", "eines", "einem", "einen",
    "sich", "es", "er", "sie", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres",
    "unser", "unsere", "unserem", "unseren", "unserer", "unseres",
    "euer", "eure", "eurem", "euren", "eurer", "eures",
    "mein", "meine", "meinem", "meinen", "meiner", "meines",
    "dein", "deine", "deinem", "deinen", "deiner", "deines",
    "jemand", "jemandem", "jemanden", "niemand", "etwas",
    # Connectives, adverbs & particles
    "als", "wie", "dass", "da", "so", "aber", "oder", "und", "nicht", "nur", "auch", "sondern",
}


def strip_german_inflection(word: str) -> str:
    """Pure-Python regex inflection & derivation stripper for German words.
    
    Extracts base morpheme/stem while preserving semantic core.
    """
    w = word.lower().strip()
    if len(w) <= 3:
        return w
        
    # Remove leading ge- prefix from participles if length permits
    if w.startswith("ge") and len(w) > 4:
        # Avoid stripping if root begins with ge (e.g. gefahr, geld)
        if not re.match(r"^ge(?:fahr|danke|burt|duld|setz|winn|halt|richt|schicht|spräch)", w):
            w = w[2:]
            
    # Strip common derivational noun suffixes first
    w = re.sub(r"(?:keit|heit|schaft|ung|tum|ling|nis)$", "", w)
    
    # Strip inflectional verb and adjective endings:
    # Match standard 2-3 letter endings first
    w = re.sub(r"(?:end|est|en|em|er|es|et)$", "", w)
    # Strip single-char inflections if length permits
    if len(w) > 4:
        w = re.sub(r"(?:st|e)$", "", w)
    
    return w if len(w) >= 3 else word.lower().strip()


def extract_semantic_heads(phrase: str) -> List[str]:
    """Extract semantic head words from a collocation by filtering out stop words."""
    tokens = re.findall(r"[a-zA-ZäöüÄÖÜß]+", phrase)
    heads = [t for t in tokens if t.lower() not in STOPWORDS]
    # If all tokens were filtered (e.g. 'sondern auch'), retain all tokens
    return heads if heads else tokens


def check_anti_leakage(collocation: str, definition: str) -> List[Tuple[str, str, str]]:
    """Check if the definition leaks any stem or base morpheme of the collocation's semantic heads.
    
    Returns a list of violations: (head_word, leaked_stem, offending_def_word).
    """
    heads = extract_semantic_heads(collocation)
    def_tokens = re.findall(r"[a-zA-ZäöüÄÖÜß]+", definition)
    violations = []
    
    for head in heads:
        head_stem = strip_german_inflection(head)
        for d_token in def_tokens:
            d_word = d_token.lower()
            d_stem = strip_german_inflection(d_word)
            
            # If stem length >= 4, check substring containment
            if len(head_stem) >= 4:
                if (
                    head_stem in d_word
                    or head_stem in d_stem
                    or (len(d_stem) >= 4 and d_stem in head.lower())
                ):
                    violations.append((head, head_stem, d_token))
                    break
            # If stem length == 3, require exact match
            elif len(head_stem) == 3:
                if head_stem == d_word or head_stem == d_stem:
                    violations.append((head, head_stem, d_token))
                    break
                    
    return violations


def generate_guid(collocation: str, cloze_sentence: str) -> str:
    """Generate a deterministic 16-hex GUID."""
    payload = f"{collocation.strip()}::{cloze_sentence.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def format_tsv_row(card: Dict[str, Any]) -> str:
    """Format a single card dictionary into a tab-separated Anki Cloze row."""
    # Column 1: GUID (16 hex)
    guid = card.get("guid", "").strip()
    if not (len(guid) == 16 and all(c in "0123456789abcdefABCDEF" for c in guid)):
        guid = generate_guid(card["collocation"], card["cloze_sentence"])
        
    definition = card["definition"].strip().replace("\t", " ").replace("\n", "<br>")
    cloze_sentence = card["cloze_sentence"].strip().replace("\t", " ").replace("\n", "<br>")
    collocation = card["collocation"].strip().replace("\t", " ").replace("\n", "<br>")
    valency = card.get("valency", "").strip().replace("\t", " ").replace("\n", "<br>")
    en = card.get("en", "").strip().replace("\t", " ").replace("\n", "<br>")
    pl = card.get("pl", "").strip().replace("\t", " ").replace("\n", "<br>")
    
    tags_data = card.get("tags", ["german-schreiben", "schreiben::c1"])
    if isinstance(tags_data, list):
        tags_str = " ".join(t.strip() for t in tags_data if t.strip())
    else:
        tags_str = str(tags_data).strip()
    tags_str = tags_str.replace("\t", " ").replace("\n", " ")
    
    # Col 2: Front
    col2 = (
        f'<div style="font-size:1.2em;color:#2e9d5c;margin-bottom:0.8em">{definition}</div>'
        f'<div>{cloze_sentence}</div>'
    )
    
    # Col 3: Extra
    valency_markup = f'<br><span style="color:#888">{valency}</span>' if valency else ""
    col3 = (
        f'<b>{collocation}</b>{valency_markup}'
        f'<br><span style="opacity:0.85">EN: {en}<br>PL: {pl}</span>'
    )
    
    return f"{guid}\t{col2}\t{col3}\t{tags_str}\n"


def validate_and_append_cards(input_path: Path, deck_path: Path) -> List[Dict[str, Any]]:
    """Validate cards from input JSON and append valid TSV rows to deck.txt.
    
    Raises ValueError with details on validation errors.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input draft cards file not found: {input_path}")
        
    with open(input_path, "r", encoding="utf-8") as f:
        cards = json.load(f)
        
    if not isinstance(cards, list):
        raise ValueError("Input JSON must contain an array of card objects.")
        
    errors = []
    tsv_rows = []
    
    for idx, card in enumerate(cards):
        for field in ("definition", "cloze_sentence", "collocation"):
            if not card.get(field):
                errors.append(f"Card {idx}: Missing required field '{field}'.")
                
        cloze_sentence = card.get("cloze_sentence", "")
        if not re.search(r"\{\{c\d+::.*?\}\}", cloze_sentence):
            errors.append(f"Card {idx}: Cloze syntax missing in 'cloze_sentence': '{cloze_sentence}'.")
            
        collocation = card.get("collocation", "")
        definition = card.get("definition", "")
        
        # Anti-leakage verification
        leakage = check_anti_leakage(collocation, definition)
        if leakage:
            for head, stem, def_word in leakage:
                errors.append(
                    f"Card {idx} ('{collocation}'): Leaked semantic stem '{stem}' (from '{head}') "
                    f"via word '{def_word}' in definition: '{definition}'."
                )
                
        if not errors:
            tsv_rows.append(format_tsv_row(card))
            
    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(f"Card validation failed with {len(errors)} error(s):\n{error_msg}")
        
    # Append to deck.txt
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing content to check ending newline
    existing_content = ""
    if deck_path.exists():
        with open(deck_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
            
    with open(deck_path, "a", encoding="utf-8") as f:
        if existing_content and not existing_content.endswith("\n"):
            f.write("\n")
        for row in tsv_rows:
            f.write(row)
            
    return cards


def main():
    parser = argparse.ArgumentParser(
        description="Validate draft flashcards against anti-leakage rules and append to deck.txt."
    )
    parser.add_argument("--input", required=True, help="Path to draft-cards.json")
    parser.add_argument("--deck-file", required=True, help="Path to target deck.txt")
    
    args = parser.parse_args()
    
    try:
        cards = validate_and_append_cards(
            input_path=Path(args.input),
            deck_path=Path(args.deck_file)
        )
        print(f"Validated {len(cards)} card(s). Successfully appended to {args.deck_file}.")
        sys.exit(0)
    except Exception as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
