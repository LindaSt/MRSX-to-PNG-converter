import os
import numpy as np
import glob
import fire
import pandas as pd
from PIL import Image
import platform

# fix for windows
if platform.system() == 'Windows':
    print('INFO: Path to openslide ddl is manually added to the path.')
    openslide_path = r'C:\Users\ls19k424\Documents\openslide-win64-20171122\bin'
    os.environ['PATH'] = openslide_path + ";" + os.environ['PATH']
import openslide

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
    :param adjust_coord: default True. Adjusts the QuPath coordinates for the missing white border. (not necessary for ASAP extracted coordinates)
    """

    def __init__(self, file_path: str, output_path: str, coord_csv: str, level: int = 0, overwrite: bool = False, adjust_coord: bool = True):
        # initiate properties from parent class
        super().__init__(file_path=file_path, output_path=output_path, level=level, overwrite=overwrite)
        # instantiate class parameters
        self.adjust_coord = adjust_coord
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

    def _crop_wsi(self, wsi):
        # This function crops the white space around the WSI away, so that it fits together with the
        # coordinates extracted from QuPath. This is not necessary if the coordinates come from ASAP
        #incorrect_WSI = wsi.read_region((0, 0), self.level, wsi.level_dimensions[self.level])
        x, y = wsi.properties[openslide.PROPERTY_NAME_BOUNDS_X], wsi.properties[openslide.PROPERTY_NAME_BOUNDS_Y]
        dim = (int(int(x)), int(int(y)))
        w, h = wsi.properties[openslide.PROPERTY_NAME_BOUNDS_WIDTH], wsi.properties[
            openslide.PROPERTY_NAME_BOUNDS_HEIGHT]
        wh = (int(int(w) / 2 ** self.level), int(int(h) / 2 ** self.level))
        return wsi.read_region(location=dim, level=self.level, size=wh)

    # overwrite
    def process_files(self):
        # process the files with coordinates
        if os.path.isfile(self.file_path) and os.path.isfile(self.coord_csv):
            output_file_path_prefix, mrxs_path, coord_path = self.files_to_process
            assert os.path.isfile(mrxs_path)
            wsi_img = openslide.open_slide(mrxs_path)
            if self.adjust_coord:
                x, y = wsi_img.properties[openslide.PROPERTY_NAME_BOUNDS_X], wsi_img.properties[openslide.PROPERTY_NAME_BOUNDS_Y]
                coords = self.parse_csv(coord_path, adjust_x=int(x), adjust_y=int(y))
            else:
                coords = self.parse_csv(coord_path)
            # iterate over the patch-coordinates(s)
            for tma_id, coord in coords:
                output_file_path = f'{output_file_path_prefix}{tma_id}.png'
                # skip existing files, if overwrite = False
                if not self.overwrite and os.path.isfile(output_file_path):
                    print(f'File {output_file_path} already exists. Output saving is skipped. To overwrite add --overwrite.')
                else:
                    # extract the patch
                    # coord = [[12578.9619, 43432.1758], [15987.166, 43432.1758], [15987.166, 46571.3086], [12578.9619, 46571.3086]]
                    png = self.extract_crop(wsi_img, coord)
                    # save the image
                    print(f'Saving image {output_file_path}')
                    Image.fromarray(png[:, :, :3]).save(output_file_path)

        else:
            # Something went wrong
            print('mrxs and/or csv file paths are invalid.')

    def parse_csv(self, coord_csv, adjust_x=0, adjust_y=0):
        # reads the csv file and retrieves the coordinates and the TMA spot index
        # coordinates have to be returned as [tl, tr, br, bl] ((0,0) is top-left)
        csv = pd.read_csv(coord_csv, sep=';')
        inds_coords = [self._get_inds_coords(row, adjust_x, adjust_y) for index, row in csv.iterrows()]

        return [i for i in inds_coords if i]  # remove None entries

    def _get_inds_coords(self, csv_row, adjust_x=0, adjust_y=0):
        # coordinates have to be returned as [[top-left], [top-right], [bottom-right], [bottom-left]] ((0,0) is top-left)
        # only get coordinates if there is an id
        if not np.isnan(csv_row['Core Unique ID']):
            c_x, c_y = csv_row['Centroid X (pixels)'], csv_row['Centroid Y (pixels)']
            # adjust coordinates, if we work with QuPath-extracted coordinates

            radius = csv_row['Radius (pixels)']
            coords = [[c_x - radius + adjust_x, c_y - radius + adjust_y], [c_x + radius + adjust_x, c_y - radius + adjust_y],
                      [c_x + radius + adjust_x, c_y + radius + adjust_y], [c_x - radius + adjust_x, c_y + radius + adjust_y]]
            id = int(csv_row['Core Unique ID'])
            return id, coords


def extract_tma(file_path: str, coord_csv: str, output_path: str, level: int = 0, overwrite: bool = False, adjust_coord: bool = True):
    png_extractor = TMAPngExtractor(file_path=file_path, coord_csv=coord_csv, output_path=output_path, level=level,
                                    overwrite=overwrite, adjust_coord=adjust_coord)

    # process the files
    png_extractor.process_files()


if __name__ == '__main__':
    fire.Fire(extract_tma)
