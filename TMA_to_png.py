import os
import numpy as np
import glob
from openslide import open_slide
import fire
import pandas as pd
from PIL import Image

from wsi_to_png import PngExtractor


class TMAPngExtractor(PngExtractor):
    """
    This Object extracts (patches of) an mrxs file to a png format.

    :param file_path: string
        path to the mrxs file with the TMA spots
    :param output_path: string
        path to the output folder. The output format is the same name as the mrxs file,
        with an appendix if multiple patches are extracted.
    :param coord_csv: string
        Path to the csv file. Expects this set of headers: "Centroid X (pixels)", "Centroid Y (pixels)", "Radius (pixels)" (in pixel values)
    :param level: int (optional)
        Level of the mrxs file that should be used for the conversion (default is 0).
    :param overwrite: overides exisiting output

    """

    def __init__(self, file_path: str, output_path: str, coord_csv: str, level: int = 0, overwrite: bool = False):
        # initiate properties from parent class
        super().__init__(file_path=file_path, output_path=output_path, level=level, overwrite=overwrite)
        # instantiate class parameters
        self.coord_csv = coord_csv

    # overwrite
    @property
    def coord_files(self):
        if self.coord_csv:
            return glob.glob(os.path.join(self.coord_csv, f'*{self.staining}.xml')) if os.path.isdir(
                self.coord_csv) else [self.coord_csv]
        else:
            return None

    # overwrite
    @property
    def files_to_process(self):
        # we only have one file to process
        if len(self.wsi_files) == 1:
            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            output_file_name = os.path.join(self.output_path,
                                            f'{filename}-level{self.level}-TMAid')
            # skip existing files, if overwrite = False
            if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
            else:
                return output_file_name, self.file_path, self.coord_csv

    # overwrite
    def process_files(self):
        # process the files with coordinates
        if os.path.isfile(self.file_path) and os.path.isfile(self.coord_csv):
            output_file_path_prefix, mrxs_path, coord_path = self.files_to_process
            wsi_img = open_slide(mrxs_path)
            coords = self.parse_csv(coord_path)
            # iterate over the patch-coordinates(s)
            for tma_id, coord in coords:
                output_file_path = f'{output_file_path_prefix}{tma_id}.png'
                # skip existing files, if overwrite = False
                if not self.overwrite and os.path.isfile(output_file_path):
                    print(f'File {output_file_path} already exists. Output saving is skipped. To overwrite add --overwrite.')
                else:
                    # extract the patch
                    png = self.extract_crop(wsi_img, coord)
                    # save the image
                    print(f'Saving image {output_file_path}')
                    Image.fromarray(png[:, :, :3]).save(output_file_path)

        else:
            # Something went wrong
            print('mrxs and/or csv file paths are invalid.')

    def parse_csv(self, coord_csv):
        # reads the csv file and retrieves the coordinates and the TMA spot index
        # coordinates have to be returned as [[top-left], [top-right], [bottom-right], [bottom-left]]
        csv = pd.read_csv(coord_csv, sep=';')
        inds_coords = [self._get_inds_coords(row) for index, row in csv.iterrows()]

        return [i for i in inds_coords if i]  # remove None entries

    @staticmethod
    def _get_inds_coords(csv_row):
        # coordinates have to be returned as [[bottom-left], [bottom-right], [top-right], [top-left]]
        # only get coordinates if there is an id
        if not np.isnan(csv_row['Core Unique ID']):
            c_x, c_y = csv_row['Centroid X (pixels)'], csv_row['Centroid Y (pixels)']
            radius = csv_row['Radius (pixels)']
            # fix this to make it [bl, br, tr, tl]
            coords = [[c_x - radius, c_y - radius], [c_x + radius, c_y - radius], [c_x + radius, c_y + radius], [c_x - radius, c_y + radius]]
            id = int(csv_row['Core Unique ID'])
            return id, coords


def extract_tma(file_path: str, coord_csv: str, output_path: str, level: int = 0, overwrite: bool = False):
    png_extractor = TMAPngExtractor(file_path=file_path, coord_csv=coord_csv, output_path=output_path, level=level,
                                    overwrite=overwrite)

    # process the files
    png_extractor.process_files()


if __name__ == '__main__':
    fire.Fire(extract_tma)
