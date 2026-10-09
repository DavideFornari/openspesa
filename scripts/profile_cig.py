"""Profile ANAC CIG CSV files and print the results as Markdown (source for docs/profiling.md).

Usage:
  uv run python -m scripts.profile_cig data/raw/anac/cig-2025/cig_csv_2025_0[123].zip \
      --delta data/raw/anac/cig/20260901-cig_csv.zip > data/work/profile.md
"""

import argparse
import zipfile
from pathlib import Path

import duckdb

from pipeline.normalize.tax_codes import is_valid_piva

WORK = Path("data/work")
CODE_COLUMNS = ["cf_amministrazione_appaltante", "CF_SA_DELEGANTE", "CF_SA_DELEGATA"]


def extract(zip_path: str) -> str:
    with zipfile.ZipFile(zip_path) as z:
        [name] = z.namelist()
        if not (WORK / name).exists():
            z.extract(name, WORK)
    return (WORK / name).as_posix()


def table(con, title: str, sql: str) -> None:
    rel = con.sql(sql)
    print(f"\n### {title}\n")
    print("| " + " | ".join(rel.columns) + " |")
    print("|" + "---|" * len(rel.columns))
    for row in rel.fetchall():
        cells = [f"{v:,}" if isinstance(v, int) else ("" if v is None else str(v)) for v in row]
        print("| " + " | ".join(cells) + " |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("zips", nargs="+", help="monthly CIG zips")
    parser.add_argument("--delta", help="a delta zip to compare with the monthly files")
    args = parser.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    files = [extract(z) for z in args.zips + ([args.delta] if args.delta else [])]
    con = duckdb.connect()
    # Delta files escape quotes as \" while monthly files have none, so set it explicitly.
    con.sql(f"""create table cig as
        select * exclude (filename), parse_filename(filename, true) as src
        from read_csv({files}, delim=';', quote='"', escape='\\', header=true,
                      all_varchar=true, filename=true)""")
    columns = [c for c in con.sql("select * from cig limit 0").columns if c != "src"]
    codes = {
        c
        for col in CODE_COLUMNS
        for (c,) in con.sql(f"select distinct {col} from cig where {col} is not null").fetchall()
    }
    con.sql("create table valid_codes (c varchar)")
    con.executemany("insert into valid_codes values (?)", [[c] for c in codes if is_valid_piva(c)])

    print("## Files")
    table(
        con,
        "Rows and CIGs",
        """
        select src as file, count(*) as rows, count(distinct cig) as cigs,
          count(*) filter (where flag_prevalente <> '1') as secondary_cpv_rows,
          min(data_pubblicazione) as first_published, max(data_pubblicazione) as last_published
        from cig group by all order by 1""",
    )
    table(
        con,
        "Format checks",
        """
        select src as file,
          count(*) filter (where not regexp_full_match(cig, '[0-9A-Z]{10}')) as bad_cig,
          count(*) filter (where not regexp_full_match(cod_cpv, '\\d{8}-\\d')) as bad_cpv,
          count(*) filter (where not regexp_full_match(luogo_istat, '\\d{6}')) as bad_istat,
          count(*) filter (where luogo_istat is null) as null_istat,
          count(*) filter (where try_cast(data_pubblicazione as date) is null) as bad_date,
          count(*) filter (where cast(cig as varchar) like '%' || chr(65533) || '%'
            or oggetto_lotto like '%' || chr(65533) || '%'
            or TIPO_APPALTO_RISERVATO like '%' || chr(65533) || '%') as replacement_chars
        from cig group by all order by 1""",
    )

    nulls = ", ".join(
        f'round(100.0 * count(*) filter (where "{c}" is null) / count(*), 1) as "{c}"'
        for c in columns
    )
    prev = "from cig where flag_prevalente = '1'"  # one row per CIG: its main CPV
    rel = con.sql(f"select src, {nulls} {prev} group by src order by src")
    srcs, rows = rel.columns[1:], rel.fetchall()
    print("\n## Null rates (% of rows, one row per CIG)\n")
    print("| column | " + " | ".join(r[0] for r in rows) + " |")
    print("|---|" + "---|" * len(rows))
    for i, c in enumerate(srcs, start=1):
        print(f"| {c} | " + " | ".join(str(r[i]) for r in rows) + " |")

    print("\n## Categories (one row per CIG, all files)")
    categories = ["tipo_scelta_contraente", "oggetto_principale_contratto", "settore", "stato"]
    for col in [*categories, "ESITO"]:
        table(
            con,
            col,
            f"""
            select coalesce({col}, '(null)') as value, count(*) as n,
              round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
            {prev} group by all order by n desc limit 15""",
        )

    print("\n## Amounts (euros, one row per CIG, all files)")
    for col in ["importo_lotto", "importo_complessivo_gara"]:
        table(
            con,
            col,
            f"""
            with v as (select try_cast({col} as double) as x, {col} as raw {prev})
            select count(*) filter (where raw is null) as null,
              count(*) filter (where raw is not null and x is null) as unparseable,
              count(*) filter (where x = 0) as zero, count(*) filter (where x < 0) as negative,
              round(quantile_cont(x, 0.5)) as p50, round(quantile_cont(x, 0.9)) as p90,
              round(quantile_cont(x, 0.99)) as p99, round(max(x)) as max,
              count(*) filter (where x >= 1e9) as ge_1_billion
            from v""",
        )

    print("\n## Tax codes (distinct values, all files)")
    for col in CODE_COLUMNS:
        table(
            con,
            col,
            f"""
            with v as (select distinct {col} as c from cig where {col} is not null)
            select case
                when c in (select c from valid_codes) then '11 digits, valid check'
                when regexp_full_match(c, '\\d{{11}}') then '11 digits, bad check'
                when regexp_full_match(c, '\\d{{1,10}}') then 'under 11 digits'
                when regexp_full_match(c, '[A-Z]{{6}}\\d{{2}}[A-Z]\\d{{2}}[A-Z]\\d{{3}}[A-Z]')
                  then '16 chars, personal pattern'
                else 'other' end as kind,
              count(*) as distinct_codes,
              -- never print a natural person's tax code
              any_value(case when regexp_full_match(c, '[A-Z0-9]{{16}}') then '(hidden)' else c end)
                as example
            from v group by all order by distinct_codes desc""",
        )

    if args.delta:
        delta = Path(args.delta).stem
        con.sql(f"create table d as select * {prev} and src = '{delta}'")
        con.sql(f"create table m as select * {prev} and src <> '{delta}'")
        print(f"\n## Delta {delta}")
        table(
            con,
            "Publication year of delta rows",
            """
            select anno_pubblicazione as year, count(*) as n from d group by all order by 1""",
        )
        diffs = ", ".join(
            f'count(*) filter (where d."{c}" is distinct from m."{c}") as "{c}"' for c in columns
        )
        rel = con.sql(f"select count(*) as cigs_in_both, {diffs} from d join m using (cig)")
        r = rel.fetchone()
        print(f"\n### Fields that differ for the {r[0]:,} CIGs also in the monthly files\n")
        print("| column | CIGs with a different value |\n|---|---|")
        for c, n in sorted(zip(rel.columns[1:], r[1:], strict=True), key=lambda x: -x[1]):
            if n:
                print(f"| {c} | {n:,} |")
        table(
            con,
            "ESITO: monthly file vs delta",
            """
            select m.ESITO as monthly, d.ESITO as delta, count(*) as n
            from d join m using (cig) group by all order by n desc limit 8""",
        )


if __name__ == "__main__":
    main()
