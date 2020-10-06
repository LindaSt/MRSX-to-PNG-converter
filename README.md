# WSI-to-PNG Converter
This command line tool lets you converts either a single or a folder or whole slide images (mrxs, ndpi)
to a PNG.

It takes the following command line arguments:
- `file-path`: Path to the mrxs single file or folder of files.
- `output-path`: Path to the output folder. The output format is the same name as the mrxs file,
    with an appendix if multiple patches are extracted.
- `level`: Level of the mrxs file that should be used for the conversion (default is 0).
- `staining`: Staining identifier, that would be specified right before .mrxs (e.g. CD8) (optional, default is '')
- `override`: Default is False. If set to True, overrides patches with the same file name in the output folder.

Run as `python wsi_to_png.py [command line arguments]`.

# ASAP-to-PNG Converter
This command line tool lets you extract patches a single or a folder or whole slide images (mrxs, ndpi)
to a PNG based on rectangle annotations in a xml file (exported from ASAP).

It takes the following command line arguments:
- `file-path`: Path to the mrxs single file or folder of files.
- `output-path`: Path to the output folder. The output format is the same name as the mrxs file,
    with an appendix if multiple patches are extracted.
- `coord-path`: Path to the coordinate xml files (created with rectangle tool in ASAP) single file or folder of files
        If not provided, the full image is converted into a png.
- `coord-annotation-tag`: Name of the annotation group in the xml file (default is 'hotspot').
- `matched_files_excel`: Optional. If provided, then this file will be used to match the xmls to the mrxs file names (needs to contain
        a column called "WSI-names" and "XML-names"
- `staining`: Staining identifier, that would be specified right before .mrxs (e.g. CD8) (optional, default is '')
- `level`: Level of the mrxs file that should be used for the conversion (default is 0).
- `override`: Default is False. If set to True, overrides patches with the same file name in the output folder.

Run as `python asap_to_png.py [command line arguments]`.


# TMA-to-PNG-converter
This is a more specific implementation, which cuts out TMA spots and saves them as a PNG file based on coordinates and 
the radius in a csv file.

- `file-path`: Path to the mrxs file.
- `output-path`: Path to the output folder. The output format is the same name as the mrxs file,
    with an appendix if multiple patches are extracted.
- `coord_csv-path`: Path to the csv file. Expects this set of headers: "Centroid X (pixels)",
    "Centroid Y (pixels)", "Radius (pixels)" (in pixel values)
- `level`: Level of the mrxs file that should be used for the conversion (default is 0). Needs to match the level of the
       pixel coordinates.
- `staining`: Staining identifier, that would be specified right before .mrxs (e.g. CD8) (optional, default is '')
- `override`: Default is False. If set to True, overrides patches with the same file name in the output folder.
- `adjust_coord`: Default is True. Adjusts coordinates extracted with QuPath for the missing white border in MRXS files. 
        (Not necessary for ASAP extracted coordinates, or other file types).


Run as `python tma_to_png.py [command line arguments]`.


# Installation    
You can set up the conda environment by running `conda env create -f environment.yml` in this directory.
The tool the [OpenSlide](https://openslide.org/) Python API is used to to handle the whole slide image files.