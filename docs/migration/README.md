# datasetIdentifier restructuring

This migration starts from `vitkute/colourmaps-legends`, branch `restructure`, commit `cf363c304713fbf1a91d7921673497f213144b8a`. The implementation is proposed on `datasetidentifier-layout` for a draft PR targeting `restructure`.

## Mapping rules

- The grouping key is CDSE OData `datasetIdentifier`, not STAC Collection ID.
- `documented-dataset-identifiers.json` records identifiers extracted from the CDSE CLMS documentation's identifier table and OData query examples on 2026-10-28. Source: https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CLMS.html
- Prefer documented IDs matching descriptor metadata, descriptor filenames, and existing folder identifiers. Prefer the longest matching identifier so confidence layers remain separate when explicitly identified.
- Otherwise retain provisional IDs from descriptor names, dataset path suffixes, or filenames. Remove a terminal year/range from a provisional filename-derived ID when it follows the dataset version. A data path is evidence, not independent catalogue validation.
- Place resources by an explicit filename identifier, then descriptor references, then a folder with one dataset identity. A filename-derived provisional identity is the fallback. The full decision and evidence for every file appear in `path-map.json`.
- Preserve all original asset filenames. Keep conflicting descriptor names under `variants/<original-folder>/` rather than overwrite or discard them. Shared or unresolved ownership would use `shared/`; this migration has no remaining unassigned files.
- Do not edit `name`, `eodataPath`, units, scale, or other descriptor fields as part of this structural change. Inconsistent metadata remains visible for follow-up review.

The path map includes original SHA-256 checksums. Several old folder aliases resolve to one identifier, for example `lcfm-lcm_global_10m_yearly_v1` resolves to `lcm_global_10m_yearly_v1` based on descriptor metadata and the documented identifier. Year-specific Urban Atlas and grassland-change descriptors remain separate files within their dataset.

## What changed

Resources now live in `datasets/<datasetIdentifier>/<resource-type>/`. Descriptor repository links are rewritten to the new paths; full GitHub links point at raw assets on `vitkute/colourmaps-legends` branch `datasetidentifier-layout`, making the draft branch independently reviewable. Relative asset references remain relative to the repository root. S3 paths and unrelated external links are unchanged.

Old root-level index files and `metadata.json` are retained as historical snapshots under `legacy-indexes/` and `legacy-metadata.json`. They contained obsolete counts and placeholder metadata, so they are not used as current inventories. `catalogue.json` is the current inventory; its key is `datasetIdentifier` and each entry states whether its identifier was documented or provisional.

Directory-level examples in the original AsciiDoc specifications describe historical structures. The README and this document define the new repository layout; the original specifications are preserved for separate technical review.

## Verification

Run from the repository root:

```bash
python3 scripts/validate_layout.py
```

The validator needs the original commit available locally. CI uses full Git history. It verifies every mapped original checksum against that commit, confirms the presence and preservation of relocated files, accepts JSON changes only when they match the expected link rewrite, checks new repository links, and checks catalogue coverage. `validation-report.json` records the migration trial, including all pre-existing unresolved links. Baseline broken links are reported separately and do not fail preservation checks. Schema conformance, remote availability, embedded GIS references, and application rendering require separate checks.

This validator deliberately pins the migration baseline: later legitimate edits to migrated assets require a corresponding update to the preservation-check policy. It is a migration review gate, not a general permission to change the original checksums.

To reproduce the migration, use a separate clean checkout of the base commit, create a working branch, and copy `scripts/restructure_datasets.py` plus `docs/migration/documented-dataset-identifiers.json` into it. Run the script without arguments for a dry run, or with `--apply` to move files and write the catalogue. Copy the validator there to check the result. Never run the migration again on the migrated tree; the script rejects that case.

## Remaining review gates

- Confirm the provisional identifiers listed in `validation-report.json` against CDSE and decide which duplicate descriptors are authoritative. Provisional dataset folders are review candidates, not claims of published identifiers.
- Resolve or explicitly accept pre-existing unresolved references. No missing assets are fabricated.
- Coordinate external consumers before merging: original asset paths are removed by this direct migration. Preserve compatibility copies or publish a stable legacy snapshot if consumers cannot migrate together.
- Confirm the raw-link branch policy before deleting or renaming `datasetidentifier-layout`. When adopting a different permanent branch, update the link prefix and validation policy together.
- Validate descriptors against the correct maintainer-approved schemas. `information_template.json` files are not assumed to be executable JSON Schemas.
- Smoke-test global and European datasets in their consuming applications.

The draft PR does not merge or modify the original `restructure` branch. Roll back by closing the PR; after a merge, use a normal revert commit.
