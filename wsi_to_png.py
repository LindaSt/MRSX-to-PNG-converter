import os
import numpy as np
import glob
from openslide import open_slide
import fire
import xml.etree.ElementTree as ET
from PIL import Image


class PngExtractor:
    """
    This Object extracts a whole mrxs file to a png format.

    :param file_path: string
        path to the mrxs single file or folder of files.
    :param output_path: string
        path to the output folder. The output format is the same name as the mrxs file,
        with an appendix if multiple patches are extracted.
    :param staining: Staining identifier, that would be specified right before .mrxs (e.g. CD8) (optional)
    :param level: int (optional)
        Level of the mrxs file that should be used for the conversion (default is 0).
    :param overwrite: overides exisiting extracted patches (default is False)

    """

    def __init__(self, file_path: str, output_path: str, staining: str = '', level: int = 0, overwrite: bool = False):
        # initiate the mandatory elements
        self.file_path = file_path
        self.output_path = output_path
        # instantiate optional parameters
        self.staining = staining
        self.level = level
        self.overwrite = overwrite

    @property
    def output_path(self):
        return self._output_path

    @output_path.setter
    def output_path(self, output_path):
        # make the output folder if it does not exist
        if not os.path.isdir(output_path):
            os.makedirs(output_path)
        self._output_path = output_path

    @property
    def wsi_files(self):
        if os.path.isfile(self.file_path):
            files = [self.file_path]
        else:
            files = glob.glob(os.path.join(self.file_path, f'*{self.staining}.mrxs')).extend(glob.glob(os.path.join(self.file_path, f'*{self.staining}.ndpi')))
        return files

    @property
    def files_to_process(self):
        # we only have one file to process
        if len(self.wsi_files) == 1:
            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            output_file_name = os.path.join(self.output_path, f'{filename}-level{self.level}')
            # skip existing files, if overwrite = False
            if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
            else:
                return [(output_file_name, self.file_path)]

        # we have multiple files to process
        else:
            files_to_process = []
            for wsi_path in self.wsi_files:
                filename = os.path.splitext(os.path.basename(wsi_path))[0]
                output_file_name = os.path.join(self.output_path, f'{filename}-level{self.level}')
                # skip existing files, if overwrite = False
                if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                    print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
                    continue
                files_to_process.append((output_file_name, wsi_path))

            return files_to_process

    def process_files(self):
        # process the full image
        if os.path.isfile(self.file_path) or os.path.isdir(self.file_path):
            for output_file_path, wsi_path in self.files_to_process:
                assert os.path.isfile(wsi_path)
                wsi_img = open_slide(wsi_path)
                # extract the patch
                png = self.extract_crop(wsi_img)
                # save the image
                print(f'Saving image {output_file_path}.png')
                Image.fromarray(png[:, :, :3]).save(f'{output_file_path}.png')

        else:
            # Something went wrong
            print('mrxs paths are invalid.')

    def extract_crop(self, wsi_img, coord=None):
        # coordinates have to be in format [tl, tr, br, bl] ((0,0) is top-left)
        # crop the region of interest from the mrxs file on the specified level
        # get the level and the dimensions
        id_level = np.argmax(np.array(wsi_img.level_downsamples) == self.level)
        dims = wsi_img.level_dimensions[id_level]

        if coord:
            top_left_coord = [int(i) for i in coord[0]]
            width = coord[2][0] - coord[0][0]
            height = coord[2][1] - coord[0][1]
            size = (int(width), int(height))
            # make sure the dimension we want to crop are within the image dimensions
            assert coord[3][0] <= dims[0] and coord[3][1] <= dims[1]
        else:
            # if no coordinates are specified, the whole image is exported
            top_left_coord = [0, 0]
            size = dims

        # extract the region of interest
        img = wsi_img.read_region(top_left_coord, id_level, size)

        # Convert to img
        img = np.array(img)
        img[img[:, :, 3] != 255] = 255
        return img


def extract_whole_slide(file_path: str, output_path: str, staining: str = '', level: int = 0, overwrite: bool = False):
    png_extractor = PngExtractor(file_path=file_path, output_path=output_path, staining=staining,
                                 level=level, overwrite=overwrite)

    # process the files
    png_extractor.process_files()


if __name__ == '__main__':
    fire.Fire(extract_whole_slide)
