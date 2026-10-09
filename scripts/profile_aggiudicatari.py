"""Profile an ANAC aggiudicatari (winners) file and print Markdown for docs/profiling.md.

Tax codes are only counted and shown as shapes (letters as A, digits as 9), never as values.

Usage:
  uv run python -m scripts.profile_aggiudicatari \
      data/raw/anac/aggiudicatari/20261001-aggiudicatari_csv.zip \
      --cig data/raw/anac/cig/20261001-cig_csv.zip
"""

import argparse

import duckdb

from pipeline.normalize.tax_codes import is_valid_cf, is_valid_piva
from scripts.profile_cig import extract, table


def code_kind(c: str) -> str:
    if is_valid_piva(c):
        return "11 digits, valid check"
    if c.isdigit() and len(c) == 11:
        return "11 digits, bad check"
    if c.isdigit() and len(c) < 11:
        return (
            "under 11 digits, valid once zero-padded"
            if is_valid_piva(c.zfill(11))
            else ("under 11 digits, invalid")
        )
    if c.startswith("IT") and is_valid_piva(c[2:]):
        return "IT + valid partita IVA"
    if is_valid_cf(c):
        return "16 chars, personal, valid check"
    if len(c) == 16 and c.isalnum() and c.isupper():
        return "16 chars, personal shape, bad check"
    return "other (foreign or malformed)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("zip", help="an aggiudicatari zip")
    parser.add_argument("--cig", help="the CIG zip of the same month, to measure join coverage")
    args = parser.parse_args()

    con = duckdb.connect()
    # Same quoting as the CIG deltas: quotes escaped as \"
    read = "delim=';', quote='\"', escape='\\', header=true, all_varchar=true"
    con.sql(f"create table agg as select * from read_csv('{extract(args.zip)}', {read})")
    codes = con.sql("select distinct codice_fiscale from agg where codice_fiscale is not null")
    rows = [[c, code_kind(c)] for (c,) in codes.fetchall()]
    con.sql("create table kinds (c varchar, kind varchar)")
    con.executemany("insert into kinds values (?, ?)", rows)
    con.sql("create table a as select * from agg left join kinds on agg.codice_fiscale = kinds.c")

    print("## Aggiudicatari")
    table(
        con,
        "Overview",
        """
        select count(*) as rows, count(distinct cig) as cigs,
          count(distinct id_aggiudicazione) as awards,
          count(distinct codice_fiscale) as distinct_codes,
          count(*) filter (where codice_fiscale is null) as null_code,
          count(*) filter (where ruolo is null) as null_role
        from agg""",
    )
    table(
        con,
        "Winner rows per CIG",
        """
        select case when n >= 5 then '5+' else n::varchar end as rows_per_cig, count(*) as cigs
        from (select cig, count(*) as n from agg group by cig) group by all order by 1""",
    )
    table(
        con,
        "Role (ruolo)",
        """
        select coalesce(ruolo, '(null)') as ruolo, count(*) as rows from agg
        group by all order by rows desc""",
    )
    table(
        con,
        "Entity type (tipo_soggetto)",
        """
        select coalesce(tipo_soggetto, '(null)') as tipo_soggetto, count(*) as rows from agg
        group by all order by rows desc""",
    )
    table(
        con,
        "Tax code kinds (distinct codes)",
        """
        select kind, count(*) as distinct_codes,
          round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
        from kinds group by all order by distinct_codes desc""",
    )
    table(
        con,
        "Entity type of personal codes (rows)",
        """
        select tipo_soggetto, count(*) as rows from a where kind like '16 chars%'
        group by all order by rows desc limit 8""",
    )
    table(
        con,
        "Most common shapes of other codes (distinct codes)",
        r"""
        select regexp_replace(regexp_replace(c, '[A-Za-z]', 'A', 'g'), '\d', '9', 'g') as shape,
          count(*) as distinct_codes
        from kinds where kind like 'other%' or kind like 'under 11 digits, invalid'
        group by all order by distinct_codes desc limit 12""",
    )
    table(
        con,
        "Names per tax code",
        """
        select case when n >= 3 then '3+' else n::varchar end as names, count(*) as codes
        from (select codice_fiscale, count(distinct denominazione) as n from agg
              where codice_fiscale is not null group by 1) group by all order by 1""",
    )
    table(
        con,
        "Joint ventures (CIGs with at least one MANDANTE)",
        """
        select count(*) as cigs, count(*) filter (where leads = 1) as one_lead,
          count(*) filter (where leads = 0) as no_lead,
          count(*) filter (where leads > 1) as many_leads
        from (select cig, count(*) filter (where ruolo = 'MANDATARIA') as leads from agg
              group by cig having count(*) filter (where ruolo = 'MANDANTE') > 0)""",
    )

    if args.cig:
        con.sql(f"""create table cig as select cig, ESITO
            from read_csv('{extract(args.cig)}', {read}) where flag_prevalente = '1'""")
        table(
            con,
            "Join to the CIG file of the same month",
            """
            select count(*) as winner_cigs, count(c.cig) as found_in_cig_file,
              round(100.0 * count(c.cig) / count(*), 1) as pct_found,
              count(*) filter (where c.cig is not null and c.ESITO is null) as found_but_no_outcome
            from (select distinct cig from agg) g left join cig c using (cig)""",
        )


if __name__ == "__main__":
    main()
