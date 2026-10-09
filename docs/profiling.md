# Profiling: ANAC CIG data

Profiled on 2026-10-09: the monthly files for **January to March 2025** (`cig-2025`,
published 16 January 2026) and one monthly delta, **`20260901-cig_csv`** (dataset `cig`).
The tables come from [`scripts/profile_cig.py`](../scripts/profile_cig.py). To reproduce:

```bash
uv run python -m scripts.profile_cig data/raw/anac/cig-2025/cig_csv_2025_0[123].zip --delta data/raw/anac/cig/20260901-cig_csv.zip
```

## Summary

| # | Finding | Consequence |
|---|---|---|
| 1 | **Delta files contain changes as well as new records.** Of the September 2026 delta's 162,176 CIGs, 30% were first published before 2026 (back to 2007), and 4,917 also appear in Q1 2025. | The build must upsert by CIG. A delta can't simply be appended. |
| 2 | **Delta rows can lose information.** 745 CIGs that were `AGGIUDICATA` (awarded) with a date in Q1 2025 have no outcome (ESITO) in the delta. | "Latest row wins" would erase known outcomes. Decide per field in ADR-001. |
| 3 | **One CIG can have several rows**, one per CPV code (product category). `flag_prevalente = '1'` marks the main one: exactly one per CIG, except 6 CIGs that have none. | Filter on the main CPV before counting or summing, or totals are double-counted (1.4% to 4.2% extra rows). |
| 4 | **All 11-digit authority tax codes are valid**: 21,904 distinct, no lost leading zeros, no bad check digits. | Normalizing authority codes is easy. The onData zero-padding problem doesn't show up here. |
| 5 | **123 authorities have ANAC placeholder codes** (`CFAVCP-…`), mostly joint purchasing centres for several towns (*centrali uniche di committenza*), on 880 rows. | The authority key must accept them, or use `codice_ausa` (ANAC's own authority ID) instead. |
| 6 | **3 authorities are identified by a personal 16-character tax code** (classified `NON CLASSIFICATO`). | Natural-person detection must also run on the **authority** columns, not only on winners. |
| 7 | **A few huge amounts dominate the totals.** In Q1 2025 the top 10 lots hold €34.3 billion of €143 billion (24%), including a €5.2 billion cleaning contract for a small town, awarded directly. | Totals need plausibility flags, or a few data-entry errors will dominate every chart and indicator. |
| 8 | **`importo_complessivo_gara` is the whole tender's value, repeated on every lot.** 6,033 CIGs show a tender of at least €1 billion. | Never sum it. Sum `importo_lotto` over distinct CIGs. |
| 9 | **The format differs between file types.** The delta writes `mese_pubblicazione` as `02` (monthly files: `2`), changes the case of text values, and escapes quotes as `\"`. | Bronze must normalize these. The CSV reader must set `escape='\'` explicitly. |
| 10 | **Cancelled CIGs aren't published.** `stato` is always `ATTIVO`, and the cancellation columns are 100% null. | Removals can't be detected from this dataset. |

## Files and structure

| file | rows | CIGs | rows for secondary CPVs | first published | last published |
|---|---|---|---|---|---|
| cig_csv_2025_01 | 112,879 | 111,216 | 1,664 | 2025-01-01 | 2025-01-31 |
| cig_csv_2025_02 | 116,629 | 115,039 | 1,590 | 2025-02-01 | 2025-02-28 |
| cig_csv_2025_03 | 119,798 | 118,030 | 1,768 | 2025-03-01 | 2025-03-31 |
| 20260901-cig_csv | 168,977 | 162,176 | 6,806 | 2007-12-14 | 2026-09-01 |

- All four files have the same 61 columns, in the same order (listed in
  [sources/anac.md](sources/anac.md)).
- Monthly files are UTF-8 with no escaped quotes. The delta escapes them with a backslash
  (29 lines, for example `3\" Lotto 9`). DuckDB's auto-detection picks the wrong rule
  whenever a monthly file is read first.
- No malformed CIGs, ISTAT codes or dates. There are no U+FFFD replacement characters in
  the columns checked.

## Delta files

Publication years in the September 2026 delta (main CPV rows only):

| year | ≤2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| CIGs | 1,792 | 1,154 | 2,191 | 3,907 | 11,650 | 28,624 | 112,853 |

The first delta of the year, `20260401`, also covers the months before it: it holds all of
January to March 2026 (102,538, 126,344 and 136,703 CIGs on their main CPV), plus 2025
updates. There's no `cig-2026` yearly dataset yet, but no gap either.

For the 4,917 CIGs in both Q1 2025 and the delta, these fields differ most often:

| field | CIGs that differ | what changes |
|---|---|---|
| mese_pubblicazione | 4,917 | mostly format (`2` → `02`); 523 change month |
| MOTIVO_URGENZA | 2,045 | case only (`non applicabile` → `NON APPLICABILE`) |
| ESITO / COD_ESITO | 1,505 | outcome added (637 + 108), removed (745) |
| DATA_COMUNICAZIONE_ESITO | 1,104 | outcome date added or removed |
| CF_SA_DELEGANTE / name | 806 / 1,079 | delegating authority filled in or changed |
| data_pubblicazione | 563 | publication date moves, usually earlier |
| importo_lotto | 64 | amount corrected |
| cf_amministrazione_appaltante | 5 | authority changed |

Outcome (ESITO) in Q1 2025 vs the delta:

| monthly file | delta | CIGs |
|---|---|---|
| AGGIUDICATA | AGGIUDICATA | 3,205 |
| AGGIUDICATA | *(empty)* | **745** |
| *(empty)* | AGGIUDICATA | 637 |
| *(empty)* | *(empty)* | 189 |
| *(empty)* | no winner, tender closed | 101 |

ANAC doesn't document why outcomes disappear. Until we know, a value present in an older
file shouldn't be overwritten by an empty one (field-level coalesce). That rule goes into
ADR-001.

## Identifiers

| key | finding |
|---|---|
| `cig` | Always 10 uppercase alphanumerics. Unique per CIG once filtered on `flag_prevalente = '1'`. |
| `cod_cpv` | Usually `NNNNNNNN-N`. 11,000 to 23,000 rows per file have 8 digits without the check digit, mostly with no description (for example `33690000`, 16,259 rows). `99999999` means "main CPV not available" (1,815 rows). Normalize to the first 8 digits. |
| `luogo_istat` | Always 6 digits with leading zeros when present; 0.5% to 2% null. |
| `codice_ausa` | ANAC's authority ID, 10 digits, null on 0.1% of delta rows. |

Authority tax codes (distinct values across all four files):

| column | 11 digits, valid check | `CFAVCP-…` placeholder | 16 characters, personal pattern |
|---|---|---|---|
| cf_amministrazione_appaltante | 21,904 | 123 | 3 |
| CF_SA_DELEGANTE | 21,875 | 105 | 3 |
| CF_SA_DELEGATA | 610 | 135 | 0 |

No 11-digit code has a bad check digit, and none has fewer than 11 digits. The check digit
is validated by `pipeline/normalize/tax_codes.py`.

**Not in this dataset:** winners' tax codes, which is where natural persons (sole traders,
professionals) mostly appear. They're in `aggiudicatari`, which hasn't been profiled yet.

## Categories (one row per CIG, all four files)

| procedure (`tipo_scelta_contraente`) | CIGs | % |
|---|---|---|
| AFFIDAMENTO DIRETTO (direct award) | 394,860 | 78.0 |
| PROCEDURA APERTA (open procedure) | 33,205 | 6.6 |
| PROCEDURA NEGOZIATA SENZA PREVIA PUBBLICAZIONE (negotiated, no prior notice) | 32,626 | 6.4 |
| PROCEDURA RISTRETTA (restricted procedure) | 10,575 | 2.1 |
| AFFIDAMENTO DIRETTO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE | 10,107 | 2.0 |
| all other values | 25,082 | 4.9 |

- `ND …` values (code `999`, for example `ND P2_19`, `ND AD2_25`) are procedures ANAC
  hasn't mapped to a name: 0.1% of rows. The suffix appears to reference an article of
  the 2023 procurement code.
- Contract type: services 45.7%, supplies 42.7%, works 11.6%.
- Sector: ordinary 98.3%, special (utilities) 1.7%.
- Outcome: awarded 86.5%, empty 12.6%, others under 1% (annulled, not awarded, no
  bids received).

## Amounts

| field | null | unparseable | zero | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|
| importo_lotto | 0 | 0 | 1,630 | €18,924 | €265,718 | €5.9 M | €7.4 bn |
| importo_complessivo_gara | 3 | 0 | 1,623 | €20,492 | €652,834 | €1.6 bn | €8.3 bn |

Q1 2025 only, main CPV rows:

| | lots | total | lots > €140k | lots > €1 M | lots > €100 M | value in lots > €100 M |
|---|---|---|---|---|---|---|
| direct award | 277,420 | €62.0 bn | 13,451 | 2,796 | 43 | €38.9 bn |
| everything else | 66,864 | €81.0 bn | 23,597 | 6,601 | 142 | €32.6 bn |

- Half of all lots are under €19,000. The distribution is extremely skewed.
- **Some big direct awards are probably data-entry errors**, for example €5.2 bn to clean
  a small town's buildings, or €4.7 bn awarded by a local health authority. Others are
  real, such as a €7.4 bn project-finance concession in Rome. We can't tell them apart
  from this dataset alone.
- **Exceeding a threshold isn't proof of a breach.** 13,451 direct awards are above
  €140,000, but framework call-offs, in-house awards and legal exemptions also show up as
  "direct". Any indicator built on this needs the exemption rules and neutral wording.
- `importo_lotto` is the estimated value at award time, not the amount paid.

## Notable null rates (main CPV rows)

| column | monthly files | delta | note |
|---|---|---|---|
| ESITO, DATA_COMUNICAZIONE_ESITO | 10% to 12% | 15% to 17% | outcome often not yet reported |
| cig_accordo_quadro | 76% to 78% | 76% | set for call-offs under framework agreements |
| CF_SA_DELEGANTE | 4.6% to 5.2% | 6.0% | |
| IMPORTO_SICUREZZA | 67% to 68% | 55% | |
| DURATA_PREVISTA | 96% to 97% | 90% | duration rarely reported |
| COD_MOTIVO_CANCELLAZIONE, DATA_CANCELLAZIONE | 100% | 100% | cancelled CIGs aren't published |
| FLAG_PNRR_PNC | 0% | 2.2% | PNRR flag, useful for later linking |

Core fields (CIG, authority, amounts, procedure, dates, CPV) are never null; the authority
fields are null on only 0.1% of delta rows. The script prints the full table for all 61
columns.

## Consequences

**For ADR-001 (storage and hosting):**
- Silver needs an upsert by CIG with field-level coalesce (finding 2), rather than
  append-only monthly partitions.
- Each fact table must keep one row per CIG (main CPV), with CPVs in a bridge table.

**For ADR-002 (keys and natural persons):**
- The authority key is the 11-digit tax code, with `CFAVCP-` placeholders allowed, or
  `codice_ausa`. Choose one.
- Natural-person detection must cover the authority and delegation columns too
  (finding 6).
- Winners need `aggiudicatari` profiled first.

**For Phase 1 (bronze/silver):**
- Normalize month numbers, text case and CPV codes.
- Set `escape='\'` when reading CSVs.
- Add plausibility flags on amounts (for example a direct award over €100 M, or a lot
  above its tender total) before computing any totals or indicators.

## Not checked

- `aggiudicatari` (winners), `partecipanti` (bidders), `stazioni-appaltanti`
  (authorities). Needed before ADR-002 is final.
- A month from before 2024, to see the schema change under the 2023 procurement code.
- The other six 2026 delta files. One delta was profiled; the other six are assumed to
  behave the same.
- Whether a delta also repeats CIGs from earlier deltas (overlap between deltas).
