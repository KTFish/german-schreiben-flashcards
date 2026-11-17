#!/usr/bin/env python3
"""Stage 1: Extraction & Deduplication for German Schreiben Flashcards.

Parses markdown essay notes for bold spans (**...** or __...__),
strips edge punctuation, extracts enclosing sentence context,
and performs dual-key deduplication against deck.txt.
"""

import argparse
import json
import re
import string
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def normalize_text(text: str) -> str:
    """Normalize text by stripping HTML tags, lowercasing, and collapsing whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower()
    text = re.sub(r"[^\w\säöüß]", " ", text)
    return " ".join(text.split())


def strip_edge_punctuation(text: str) -> str:
    """Strip extraneous edge punctuation and whitespace from a candidate phrase."""
    # Match edge punctuation: dots, commas, colons, quotes, dashes, etc.
    pattern = r"^[\s\.,;:!?»«„“”'\"`—–\-]+|[\s\.,;:!?»«„“”'\"`—–\-]+$"
    cleaned = re.sub(pattern, "", text)
    while re.search(pattern, cleaned):
        cleaned = re.sub(pattern, "", cleaned)
    return cleaned.strip()


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences handling common German abbreviations and punctuation."""
    # Normalize line breaks within paragraphs
    clean_text = re.sub(r"\r\n|\r", "\n", text)
    
    # Split paragraphs first
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean_text) if p.strip()]
    
    sentences = []
    # Protected common abbreviations
    abbr_pattern = r"\b(?:z\.B|d\.h|u\.a|usw|bzw|ca|dr|prof|etc)\."
    
    for para in paragraphs:
        # Replace newlines with spaces within a paragraph
        p_text = re.sub(r"\s+", " ", para)
        
        # Protect abbreviations by temporarily replacing their period with a placeholder
        def replace_abbr(match: re.Match) -> str:
            return match.group(0)[:-1] + "§DOT§"
        
        protected = re.sub(abbr_pattern, replace_abbr, p_text, flags=re.IGNORECASE)
        
        # Split on sentence boundaries: [.!?] followed by space and uppercase or end of text
        parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ»«„“\"])", protected)
        
        for part in parts:
            restored = part.replace("§DOT§", ".").strip()
            if restored:
                sentences.append(restored)
                
    return sentences


def extract_candidates_from_text(markdown_text: str) -> Tuple[List[Dict[str, Any]], int]:
    """Extract bold candidates from markdown text with enclosing raw sentence and span.
    
    Returns (candidates, sentence_count).
    """
    sentences = split_into_sentences(markdown_text)
    candidates = []
    
    for sentence in sentences:
        # Find all bold markers (**...** or __...__)
        bold_matches = list(re.finditer(r"(?:\*\*|__)(.*?)(?:\*\*|__)", sentence, flags=re.DOTALL))
        if not bold_matches:
            continue
            
        # Create a clean version of the sentence with markdown bold syntax stripped
        clean_sentence = re.sub(r"(?:\*\*|__)(.*?)(?:\*\*|__)", r"\1", sentence)
        clean_sentence = " ".join(clean_sentence.split())
        
        for match in bold_matches:
            raw_phrase = match.group(1)
            marked_phrase = strip_edge_punctuation(raw_phrase)
            if not marked_phrase:
                continue
                
            # Find the position of marked_phrase inside clean_sentence
            start_idx = clean_sentence.find(marked_phrase)
            if start_idx != -1:
                span = [start_idx, start_idx + len(marked_phrase)]
            else:
                span = [0, len(marked_phrase)]
                
            candidates.append({
                "raw_sentence": clean_sentence,
                "marked_phrase": marked_phrase,
                "span": span
            })
            
    return candidates, len(sentences)


def load_deck(deck_file_path: Path) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """Parse existing deck.txt to extract collocations and (sentence, collocation) pairs.
    
    Returns:
        (existing_collocations, existing_sentence_collocations)
    """
    existing_collocations: Set[str] = set()
    existing_sentence_collocations: Set[Tuple[str, str]] = set()
    
    if not deck_file_path.exists():
        return existing_collocations, existing_sentence_collocations
        
    with open(deck_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
                
            front_html = parts[1]
            extra_html = parts[2]
            
            # Extract collocation from Extra (Column 3)
            # Typically <b>Collocation</b><br>...
            m_bold = re.search(r"<b>(.*?)</b>", extra_html, flags=re.IGNORECASE)
            colloc_text = m_bold.group(1) if m_bold else extra_html
            norm_colloc = normalize_text(colloc_text)
            if norm_colloc:
                existing_collocations.add(norm_colloc)
                
            # Extract carrier sentence from Front (Column 2)
            # Remove cloze brackets {{c1::word[::hint]}} -> word
            carrier = re.sub(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", r"\1", front_html)
            # Extract text from carrier div (typically second div in Front)
            carrier_divs = re.findall(r"<div[^>]*>(.*?)</div>", carrier, flags=re.DOTALL | re.IGNORECASE)
            carrier_text = carrier_divs[-1] if len(carrier_divs) >= 2 else carrier
            norm_sentence = normalize_text(carrier_text)
            
            if norm_sentence and norm_colloc:
                existing_sentence_collocations.add((norm_sentence, norm_colloc))
                
    return existing_collocations, existing_sentence_collocations


def is_duplicate(
    candidate: Dict[str, Any],
    existing_collocations: Set[str],
    existing_sentence_collocations: Set[Tuple[str, str]]
) -> bool:
    """Evaluate whether candidate is a duplicate using the dual-key deduplication rules."""
    norm_phrase = normalize_text(candidate["marked_phrase"])
    norm_sentence = normalize_text(candidate["raw_sentence"])
    
    # Dual-key rule:
    # 1. Exact Collocation already exists in deck.txt (Column 3)
    if norm_phrase in existing_collocations:
        return True
        
    # 2. Normalized Sentence AND Collocation both exist in deck.txt
    if (norm_sentence, norm_phrase) in existing_sentence_collocations:
        return True
        
    return False


def run_diff(
    notes_path: Path,
    deck_path: Path,
    out_path: Path,
    verbose: bool = False,
    force_accepted: List[str] = None
) -> Dict[str, int]:
    """Execute the extraction and deduplication diff pipeline."""
    force_set = {normalize_text(p) for p in (force_accepted or [])}
    
    if not notes_path.exists():
        raise FileNotFoundError(f"Notes file not found: {notes_path}")
        
    with open(notes_path, "r", encoding="utf-8") as f:
        notes_content = f.read()
        
    candidates, sentence_count = extract_candidates_from_text(notes_content)
    existing_collocations, existing_sentence_collocations = load_deck(deck_path)
    
    unseen_candidates = []
    already_in_deck_count = 0
    
    for cand in candidates:
        norm_p = normalize_text(cand["marked_phrase"])
        if norm_p in force_set:
            unseen_candidates.append(cand)
            if verbose:
                print(f"[FORCE_ACCEPTED] '{cand['marked_phrase']}'")
            continue
            
        if is_duplicate(cand, existing_collocations, existing_sentence_collocations):
            already_in_deck_count += 1
            if verbose:
                print(f"[DUPLICATE] '{cand['marked_phrase']}' already present in deck")
        else:
            unseen_candidates.append(cand)
            if verbose:
                print(f"[UNSEEN] '{cand['marked_phrase']}' in sentence: '{cand['raw_sentence']}'")
                
    # Write intermediate output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unseen_candidates, f, ensure_ascii=False, indent=2)
        
    summary = {
        "sentence_count": sentence_count,
        "candidate_spans": len(candidates),
        "already_in_deck": already_in_deck_count,
        "unseen": len(unseen_candidates)
    }
    
    # CLI piped summary output
    print(
        f"in essay: {summary['sentence_count']} | "
        f"candidate bold spans: {summary['candidate_spans']} | "
        f"already in deck: {summary['already_in_deck']} | "
        f"unseen: {summary['unseen']}"
    )
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Extract bold phrases from essay notes and diff against deck.txt."
    )
    parser.add_argument("--notes", required=True, help="Path to markdown essay notes")
    parser.add_argument("--deck-file", required=True, help="Path to target deck.txt")
    parser.add_argument(
        "--out", default="unseen-candidates.json", help="Path for output JSON"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print verbose candidate classifications"
    )
    parser.add_argument(
        "--force-accepted",
        action="append",
        default=[],
        help="Force include a phrase even if duplicate rule matches",
    )
    
    args = parser.parse_args()
    
    try:
        run_diff(
            notes_path=Path(args.notes),
            deck_path=Path(args.deck_file),
            out_path=Path(args.out),
            verbose=args.verbose,
            force_accepted=args.force_accepted,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
