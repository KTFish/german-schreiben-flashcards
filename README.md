# German Schreiben Flashcards

Generate C1 German writing flashcards (*Redemittel*, structural formulas, and academic collocations) from essay notes with topic-agnostic discourse filtering.

<img alt="APM Version" src="https://img.shields.io/badge/apm-0.35.1-0078D4">
<img alt="GitHub Tag" src="https://img.shields.io/github/v/tag/KTFish/german-schreiben-flashcards">

> [!NOTE]
> **Canonical Package Architecture:** Authoring occurs in `.apm/skills/german-schreiben-flashcards/` as the single canonical source of truth, compiled to target agent environments (`.agents/`, `.claude/`, `.github/`) via `apm compile`.

## Installation

Install [APM](https://microsoft.github.io/apm/quickstart/#1-install-apm), then install this package into your dedicated deck repository:

```sh
apm install KTFish/german-schreiben-flashcards
```

## Deck Ecosystem

This package generates flashcards for the unified hierarchical Anki deck collection:

```
german-generated
├── german-kindle        (Reading highlights - kindle-flashcards)
└── german-schreiben     (Writing Redemittel - german-schreiben-flashcards)
```

Target storage repository: [`KTFish/anki-deck-german-schreiben`](https://github.com/KTFish/anki-deck-german-schreiben).

## Workflow

1. **Ingest Notes**: In your deck repository, provide your essay draft or notes (with target phrases bolded `**...**`).
2. **Deduplicate**: Run `scripts/diff.py` to strip edge punctuation and check against existing cards in `deck.txt`.
3. **Classify**: Filter out domain-specific topical nouns (*Themenwortschatz*) while retaining reusable discourse formulas and collocations (*Redemittel*).
4. **Formulate Cards**: Generate Cloze cards with fixed core blanks (`{{c1::collocation}}`), student-friendly A2/B1 definitions, and phrase-level English and Polish translations.
5. **Validate & Append**: Run `scripts/validate_cards.py` to enforce zero-leakage anti-leakage checks on semantic heads and append validated rows to `deck.txt`.
6. **Submit PR**: Open a pull request for human review and automated GitHub release tagging.

## Example

Ask your AI coding assistant:

> "Extract new C1 Redemittel from my essay draft `essay.md`, format them into flashcards, and open a PR."
