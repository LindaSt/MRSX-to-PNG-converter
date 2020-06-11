# MRSX-to-PNG-converter
This command line tool lets you convert (patches of) mrxs files to png files.

It takes the following command line arguments:
- `file_path`: Path to the mrxs single file or folder of files.
- `output-path`: Path to the output folder. The output format is the same name as the mrxs file,
    with an appendix if multiple patches are extracted.
- `coord-path`: Path to the coordinate xml files (created with ASAP) single file or folder of files
        If not provided, the full image is converted into a png.
- `coord-annotation-tag`: Name of the annotation group in the xml file (default is 'hotspot').
- `level`: Level of the mrxs file that should be used for the conversion (default is 0).
        
You can set up the conda environment by running `conda env create -f environment.yml` in this directory.
The tool the [OpenSlide](https://openslide.org/) Python API to handle the mrxs files.