# Flashcard Styling Rules (German Schreiben)

Card model: **Cloze** (`#separator:tab`, `#html:true`, `#guid column:1`, `#notetype:Cloze`, `#deck:german-generated::german-schreiben`, `#tags column:4`).

## File Header

Every `deck.txt` file must include the `#deck:german-generated::german-schreiben` header directive so that Anki imports cards directly into the intended deck:

```text
#separator:tab
#html:true
#guid column:1
#notetype:Cloze
#deck:german-generated::german-schreiben
#tags column:4
```

> [!IMPORTANT]
> The `#deck:german-generated::german-schreiben` directive ensures cards are routed into the proper nested subdeck under the `german-generated` collection in Anki even if another deck is active in the user interface.

## Column Layout (.txt, Tab-Separated)

| Col | Field | Format / Template |
|---|---|---|
| **1** | **GUID** | Unique 16-hex character ID |
| **2** | **Text (Front)** | `<div style="font-size:1.2em;color:#2e9d5c;margin-bottom:0.8em">[A2/B1 Definition]</div><div>[Carrier sentence with {{c1::core collocation[::hint]}}]</div>` |
| **3** | **Extra (Back)** | `<b>[Collocation / Formula]</b><br><span style="color:#888">[Grammar & Valency]</span><br><span style="opacity:0.85">EN: [English translation]<br>PL: [Polish translation]</span>` |
| **4** | **Tags** | `german-schreiben schreiben::c1 [optional-topic-tag]` |

## Fixed Core Cloze Model

- Blank **only the core collocation** or governing verb-noun pairing (e.g. `dem wir unsere {{c1::Aufmerksamkeit widmen}} sollten`).
- Do NOT blank full 8-word subordinate clauses, and do NOT cloze isolated single words without context.
- Keep carrier sentence grammatically intact to provide natural scaffolding during review.

## Definition Quality & Zero Answer-Leakage Guardrails

### 1. Strict Answer Concealment (Anti-Leakage)
In Anki cloze deletion, the definition is displayed directly above the context sentence on the front of the card. The definition must **NEVER** reveal or hint at the missing cloze structure:
- **No target words:** Never include the target words from the collocation.
- **No base morphemes or stems of semantic heads:** Strictly prohibit base lemmas, stems, or cognate derivations of the semantic head (e.g. if the target is *in Betracht ziehen*, do NOT use *betrachten*; if the target is *zur Folge haben*, do NOT use *Folge* or *folgen*).
- **Auxiliary stoplist exception:** High-frequency functional auxiliaries (*haben, sein, werden, lassen*) and prepositions are allowed in definitions when constructing natural sentences (e.g. *haben* in *"eine Auswirkung haben"* is acceptable for *zur Folge haben*, whereas *Folge* is strictly prohibited).

### 2. Conciseness & Student-Friendly Register
- **Length:** Exactly 1 short sentence, between 6 and 14 words.
- **Language Level:** Plain, accessible German (A2/B1 CEFR vocabulary).
- **No Academic Meta-Language:** Avoid dictionary-style jargon such as *"Bezeichnung für..."* or circular descriptions.
- **Communicative Intent:** Explain the rhetorical or communicative function simply (e.g. *"Eine gegenteilige Meinung ausdrücken"*).

### 3. Approved Archetypes & Anti-Patterns

| Target Collocation | ❌ Bad / Leaked Definition (Do NOT use) | ✅ Accepted Concise Definition |
|---|---|---|
| **in Betracht ziehen** | *Etwas genau betrachten und abwägen.* (Leaked stem `betracht`) | *Etwas bei einer Überlegung oder Entscheidung berücksichtigen.* |
| **zur Folge haben** | *Dass etwas eine bestimmte Folge hat.* (Leaked head `Folge`) | *Als Konsequenz bewirken, dass etwas Bestimmtes geschieht.* |
| **Aufmerksamkeit widmen** | *Jemandem seine volle Aufmerksamkeit schenken.* (Leaked head `Aufmerksamkeit`) | *Sich intensiv auf eine bestimmte Sache oder Person konzentrieren.* |
| **unter Beweis stellen** | *Einen Beweis für etwas liefern.* (Leaked head `Beweis`) | *In der Praxis zeigen, dass man eine bestimmte Fähigkeit besitzt.* |

## Bilingual Phrase Anchors

- Card Back (Extra field) stores phrase-level equivalents in English (`EN:`) and Polish (`PL:`).
- Valency and register indicators (e.g. `[+ Dat | Funktionsverbgefüge]`, `[Konjunktion | gehoben]`) are formatted in `<span style="color:#888">`.
- Full-sentence translations are not used to avoid visual clutter and maintain rapid review speed.

## Example Row

```text
f82b7c41a90e43d1	<div style="font-size:1.2em;color:#2e9d5c;margin-bottom:0.8em">Sich intensiv auf eine bestimmte Sache oder Person konzentrieren.</div><div>Doch ein weiterer Bereich, dem wir unsere {{c1::Aufmerksamkeit widmen}} sollten, ist der nachhaltige Verkehr.</div>	<b>Aufmerksamkeit widmen</b><br><span style="color:#888">[+ Dat | Funktionsverbgefüge]</span><br><span style="opacity:0.85">EN: to pay attention to / dedicate attention to<br>PL: poświęcić uwagę</span>	german-schreiben schreiben::c1
```
