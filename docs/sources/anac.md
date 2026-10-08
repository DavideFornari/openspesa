# ANAC open data portal: what we found

Checked on 2026-10-09 from a home connection in Italy.

## Access

- The portal (`dati.anticorruzione.it/opendata`) is CKAN, behind an F5 web application
  firewall (`server: volt-adc`).
- The firewall rejects non-browser user-agents (curl, Python-urllib, `OpenSpesa/0.1`).
  A full browser user-agent works, even with `OpenSpesa/0.1 (+repo URL)` appended.
- **A rejected request returns HTTP 200 with an HTML "Request Rejected" page**, not an
  error status. The ingester treats any `text/html` response as a failure.
- Downloads send `Last-Modified`, `Content-Length`, `Accept-Ranges: bytes` and
  `Access-Control-Allow-Origin: *`.
- CKAN API works: `/opendata/api/3/action/package_list`, `package_show?id=<dataset>`.

## License

Every dataset we checked (`cig-2025`, `cig`, `aggiudicatari`, `stazioni-appaltanti`) is
**CC-BY-SA-4.0**, not CC BY 4.0. See the open question in [TODO.md](../../TODO.md).

## CIG datasets

- One dataset per year, `cig-2007` … `cig-2025`, with monthly files in CSV, JSON and TTL.
- URL: `/opendata/download/dataset/cig-{year}/filesystem/cig_csv_{year}_{MM}.zip`
- The current year is in the `cig` dataset ("CIG aggiornamenti delta"): one file per
  month named `{YYYYMM01}-cig_csv.zip`, 150 MB to 1 GB **uncompressed**.
  Updates are monthly, not weekly.
- CKAN's `size` field is the uncompressed CSV size. January 2025: 92 MB CSV, 21 MB zip.
- Each dataset has a `*_logCsv.csv` listing row counts per file.

## CIG CSV format (cig_csv_2025_01)

- Zip with one file, `cig_csv_2025_01.csv`. UTF-8, no BOM, `;` delimiter, fields quoted
  with `"`. 112,879 rows.
- Dates are ISO (`2025-01-24`), amounts use a `.` decimal (`38754.65`), ISTAT codes keep
  leading zeros (`046015`). Some integer codes come out as floats (`7.0`).
- No winner columns: winners are in the separate `aggiudicatari` dataset.

61 columns, in file order:

```
cig, cig_accordo_quadro, numero_gara, oggetto_gara, importo_complessivo_gara,
n_lotti_componenti, oggetto_lotto, importo_lotto, oggetto_principale_contratto, stato,
settore, luogo_istat, provincia, data_pubblicazione, data_scadenza_offerta,
cod_tipo_scelta_contraente, tipo_scelta_contraente, cod_modalita_realizzazione,
modalita_realizzazione, codice_ausa, cf_amministrazione_appaltante,
denominazione_amministrazione_appaltante, sezione_regionale, id_centro_costo,
denominazione_centro_costo, anno_pubblicazione, mese_pubblicazione, cod_cpv,
descrizione_cpv, flag_prevalente, COD_MOTIVO_CANCELLAZIONE, MOTIVO_CANCELLAZIONE,
DATA_CANCELLAZIONE, DATA_ULTIMO_PERFEZIONAMENTO, COD_MODALITA_INDIZIONE_SPECIALI,
MODALITA_INDIZIONE_SPECIALI, COD_MODALITA_INDIZIONE_SERVIZI, MODALITA_INDIZIONE_SERVIZI,
DURATA_PREVISTA, COD_STRUMENTO_SVOLGIMENTO, STRUMENTO_SVOLGIMENTO, FLAG_URGENZA,
COD_MOTIVO_URGENZA, MOTIVO_URGENZA, FLAG_DELEGA, FUNZIONI_DELEGATE, CF_SA_DELEGANTE,
DENOMINAZIONE_SA_DELEGANTE, CF_SA_DELEGATA, DENOMINAZIONE_SA_DELEGATA, IMPORTO_SICUREZZA,
TIPO_APPALTO_RISERVATO, CUI_PROGRAMMA, FLAG_PREV_RIPETIZIONI, COD_IPOTESI_COLLEGAMENTO,
IPOTESI_COLLEGAMENTO, CIG_COLLEGAMENTO, COD_ESITO, ESITO, DATA_COMUNICAZIONE_ESITO,
FLAG_PNRR_PNC
```

Column names mix lowercase and UPPERCASE; bronze will lowercase them all.
