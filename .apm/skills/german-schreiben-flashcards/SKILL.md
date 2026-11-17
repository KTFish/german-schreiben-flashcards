---
name: german-schreiben-flashcards
description: Generate C1 German writing flashcards from essay drafts with topic-agnostic discourse filtering.
---

# German Schreiben Flashcards

Extract C1 discourse formulas, structural connectives, and collocations (*Redemittel*, *Funktionsverbgefüge*) from essay notes, filter out topic-specific vocabulary (*Themenwortschatz*), and generate high-yield Anki Cloze flashcards for `german-generated::german-schreiben`.

## Process

### 1. Create feature branch

In the target deck repository (e.g. `anki-deck-german-schreiben`), create a dedicated branch for the new essay additions:

```bash
git checkout -b feat/add-schreiben-<topic-slug>
```

### 2. Extract and diff candidates

Run `scripts/diff.py` to extract bolded phrases (`**...**` or `__...__`), strip boundary punctuation, isolate enclosing sentence contexts, and deduplicate against existing cards in `deck.txt`:

```bash
python scripts/diff.py --notes "<path/to/essay.md>" --deck-file "deck.txt" --out "unseen-candidates.json"
```

Options:
- `--notes`: Path to raw essay notes or draft markdown file. Required.
- `--deck-file`: Path to `deck.txt` in the deck repository. Required.
- `--out`: Path for intermediate output JSON (default: `unseen-candidates.json`).
- `--verbose`: Print candidate classification decisions to stdout.
- `--force-accepted`: Force include a phrase even if duplicate rule matches.

The script prints summary metrics to stdout:
`in essay: <count> | candidate bold spans: <count> | already in deck: <count> | unseen: <count>`
and outputs candidates to `unseen-candidates.json`.

### 3. Classify discourse and formulate cards

Read `references/styling-rules.md` for complete formatting, cloze deletion conventions, and strict anti-leakage rules.

For each entry in `unseen-candidates.json`:
1. **Apply Topic-Agnostic Reusability Filter:**
   - **Accept**: Universal discourse connectives, structural formulas, and academic collocations (*Redemittel*, *Funktionsverbgefüge*) that can be reused across any essay topic (e.g. *"Zusammenfassend lässt sich sagen, dass"*, *"Aufmerksamkeit widmen"*, *"in Betracht ziehen"*, *"Schwierigkeiten überwinden"*).
   - **Filter Out**: Domain-specific topical nouns (*Themenwortschatz*, such as *Klimaschutz*, *Ernährung*, *Landwirtschaft*, *Windkraftanlagen*).
2. **Fixed Core Cloze Generation:**
   - Blank only the core collocation or governing verb-noun pairing (e.g. `dem wir unsere {{c1::Aufmerksamkeit widmen}} sollten`), preserving the full grammatical scaffolding of the carrier sentence.
3. **Draft Student-Friendly (A2/B1) Definition:**
   - 1 short sentence (6–14 words).
   - Plain, accessible German describing the communicative or rhetorical purpose.
   - **Strict Zero-Leakage:** Strictly conceal the target collocation and any base morphemes, stems, or derivations of its semantic heads. Functional auxiliaries (*haben, sein, werden, lassen*) and prepositions are permitted.
4. **Bilingual Phrase Anchors & Grammar:**
   - Add concise phrase-level English (`en`) and Polish (`pl`) translations.
   - Specify valency or register (e.g. `[+ Dat | Funktionsverbgefüge]`).

Assemble the accepted cards into `draft-cards.json`:
```json
[
  {
    "guid": "f82b7c41a90e43d1",
    "definition": "Sich intensiv auf eine bestimmte Sache oder Person konzentrieren.",
    "cloze_sentence": "Doch ein weiterer Bereich, dem wir unsere {{c1::Aufmerksamkeit widmen}} sollten, ist der nachhaltige Verkehr.",
    "collocation": "Aufmerksamkeit widmen",
    "valency": "[+ Dat | Funktionsverbgefüge]",
    "en": "to pay attention to / dedicate attention to",
    "pl": "poświęcić uwagę",
    "tags": ["german-schreiben", "schreiben::c1"]
  }
]
```

### 4. Validate anti-leakage and append to deck

Run `scripts/validate_cards.py` to deterministically verify anti-leakage on semantic heads and append validated rows to `deck.txt`:

```bash
python scripts/validate_cards.py --input "draft-cards.json" --deck-file "deck.txt"
```

- If validation passes: exits code 0 and appends formatted TSV rows to `deck.txt`.
- If leakage is detected: exits code 1 with card indices and leaked morphemes so the agent can revise the offending definitions.
- Clean up intermediate files (`unseen-candidates.json`, `draft-cards.json`) once validation succeeds.

### 5. Commit and open Pull Request

Commit the updated `deck.txt` and open a PR for human review:

```bash
git add deck.txt
git commit -m "feat(cards): add new schreiben flashcards for <topic-slug>"
git push -u origin feat/add-schreiben-<topic-slug>
gh pr create --title "feat(cards): add schreiben flashcards for <topic-slug>" --body "Adds C1 Redemittel flashcards generated with german-schreiben-flashcards skill."
```

## Bundled Scripts

- `scripts/diff.py` — extracts bold spans from essay drafts, handles boundary punctuation stripping, and checks dual-key deduplication against `deck.txt`.
- `scripts/validate_cards.py` — verifies zero stem leakage on semantic heads using pure-Python regex inflection stripping, formats Anki Cloze TSV rows, and appends cards to `deck.txt`.
