# CLMS Colourmaps and Legends

Colourmaps, legends, thumbnails, and collection descriptors for the Copernicus Land Monitoring Service (CLMS).

## Organization by datasetIdentifier

Resources are grouped by the CDSE OData `datasetIdentifier`, for example `ba_global_300m_daily_v4`. Keep the full identifier, including coverage, resolution, frequency, and version. Dates and layer names belong in asset filenames, not in a second dataset identifier when CDSE groups them into one dataset.

```text
datasets/<datasetIdentifier>/
    colourmaps/          GIS styles and colour tables
    data_descriptors/    Collection descriptors; original filenames retained
    legends/             Legend images
    thumbnails/          Dataset preview images
catalogue.json           Dataset identifiers, verification status, and asset paths
schemas/                 Versioned descriptor templates
docs/                    Specifications and migration records
scripts/                 Migration and validation tools
```

Only resource types that have files are present. A dataset can have multiple layers, styles, resolutions, or dated descriptor variants. Existing duplicate descriptors are preserved under `data_descriptors/variants/<original-folder>/`; no duplicate is automatically selected as authoritative.

The authoritative naming reference is the [CDSE CLMS documentation](https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CLMS.html#table-datasetidentifier). `catalogue.json` marks identifiers as `documented` when found in that documentation on 2026-10-28 and `provisional` otherwise. Provisional identifiers come from existing descriptor metadata or resource filenames and require confirmation. Documentation presence does not prove live catalogue availability.

A STAC Collection ID is a separate mapping. For example, CDSE publishes format-specific STAC collections such as `clms_ba_global_300m_daily_v4_cog`, whereas the datasetIdentifier is `ba_global_300m_daily_v4`. Do not substitute a STAC ID or an individual product ID for this repository's dataset key.

## Find a resource

Open a dataset folder or look it up in `catalogue.json`. Asset paths in the catalogue are relative to the repository root. Existing asset filenames and layer names are retained. Dataset-specific descriptors link to their relocated assets, including resources maintained under another dataset when those links already existed.

SLD is the preferred colourmap interchange format. Existing QML, CLR, LYR/LYRX, TXT and other formats remain available. Legacy TXT assets have been preserved.

## Contribute

1. Confirm the exact CDSE datasetIdentifier; use its spelling and case.
2. Add resources under the corresponding dataset folder and resource type.
3. Keep variable and date variants distinct in filenames.
4. Update collection descriptors and `catalogue.json` together.
5. Run `python3 scripts/validate_layout.py` with Python 3.10 or later. See the migration notes for the validator's current scope.

Descriptor templates remain under `schemas/data_descriptors/<version>/`. See [descriptor documentation](docs/Structure_description_of_the_proposed_json_scheme_for_CLMS_collections.adoc) and [thumbnail specifications](docs/CLMS_Thumbnail_Specifications.adoc).

## Migration and compatibility

This branch changes repository asset paths. External consumers must update their links before adopting the new layout. Old GitHub asset URLs do not automatically redirect. The [migration notes](docs/migration/README.md) include the complete old-to-new path map, provisional identifiers, baseline link problems, and validation results.

Historical indexes and root metadata are archived under `docs/migration/`; they are not current inventories. `catalogue.json` replaces those inventories with explicit dataset keys and portable paths.

## License

See [LICENSE](LICENSE).
