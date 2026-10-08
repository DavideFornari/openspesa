---
license: cc-by-sa-4.0
language:
  - it
pretty_name: OpenSpesa raw mirror
tags:
  - public-procurement
  - italy
  - anac
---

# OpenSpesa raw mirror

Unmodified copies of the source files used by
[OpenSpesa](https://github.com/DavideFornari/openspesa), an open explorer of Italian public
procurement.

ANAC's portal blocks downloads from cloud servers, so files are downloaded from a home
connection and mirrored here. The OpenSpesa build reads them from here and checks each
file against the manifest.

## Contents

- `anac/<dataset>/<file>.zip`: files exactly as published on the
  [ANAC open data portal](https://dati.anticorruzione.it/opendata), in the portal's dataset
  folders (for example `anac/cig/20261001-cig_csv.zip`).
- `manifest.jsonl`: one line per download, with the source URL, local path, SHA-256, size,
  download time (UTC) and the server's `Last-Modified` header.

## Source and license

Source: ANAC, Autorità Nazionale Anticorruzione, open data portal
(https://dati.anticorruzione.it/opendata), licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). These copies are
redistributed unchanged under the same license.

This file is the dataset card; its source is `docs/datasets/raw.md` in the OpenSpesa repository.
