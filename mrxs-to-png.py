import os
import numpy as np
import glob
from openslide import open_slide
import fire
import xml.etree.ElementTree as ET
from PIL import Image


class PngExtractor:

    def __init__(self, file_path: str, output_path: str, coord_path: str = None, staining: str = '',
                 coord_annotation_tag: str = 'hotspot', level: int = 0, overwrite: bool = False):
        """
        This Object extracts (patches of) an mrxs file to a png format.

        :param file_path: string
            path to the mrxs single file or folder of files.
        :param output_path: string
            path to the output folder. The output format is the same name as the mrxs file,
            with an appendix if multiple patches are extracted.
        :param coord_path: string (optional)
            Path to the coordinate xml files (created with ASAP) single file or folder of files
            If not provided, the full image is converted into a png.
        :param staining: Staining identifier, that would be specified right before .mrxs (e.g. CD8) (optional)
        :param coord_annotation_tag: string (optional)
            Name of the annotation group in the xml file (default is 'hotspot').
        :param level: int (optional)
            Level of the mrxs file that should be used for the conversion (default is 0).
        :param overwrite: overides exisiting extracted patches (default is False)

        """
        # initiate the mandatory elements
        self.file_path = file_path
        self.output_path = output_path
        # instantiate optional parameters
        self.coord_path = coord_path
        if not self.coord_path:
            print('No coordinates xml file specified, extracting full image(s).')
        self.staining = staining
        self.coord_annotation_tag = coord_annotation_tag
        self.level = level
        self.overwrite = overwrite

        self.process_files()

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
        return glob.glob(os.path.join(self.file_path, f'*{self.staining}.mrxs')) if os.path.isdir(self.file_path) else [
            self.file_path]

    @property
    def coord_files(self):
        if self.coord_path:
            return glob.glob(os.path.join(self.coord_path, f'*{self.staining}.xml')) if os.path.isdir(
                self.coord_path) else [self.coord_path]
        else:
            return None

    @property
    def files_to_process_patch(self):
        # we only have one file to process
        if len(self.wsi_files) == 1:
            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            output_file_name = os.path.join(self.output_path,
                                            f'{filename}-level{self.level}-{self.coord_annotation_tag}')
            # skip existing files, if overwrite = False
            if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
            else:
                return [(output_file_name, self.file_path, self.coord_path)]

        # we have multiple files to process
        else:
            # create a list of the paired mrxs and coordinate files
            # only take files that have a corresponding coordinates file
            files_to_process = []
            for wsi_path in self.wsi_files:
                filename = os.path.splitext(os.path.basename(wsi_path))[0]
                output_file_name = os.path.join(self.output_path,
                                                f'{filename}-level{self.level}-{self.coord_annotation_tag}')
                # skip existing files, if overwrite = False
                if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                    print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
                    continue

                checked = []
                for coord_file in self.coord_files:
                    if filename in coord_file:
                        checked.append(coord_file)
                if len(checked) != 1:
                    print(
                        f'File {filename}.mrxs does not have a / too many corresponding xml file/s. File will be skipped.')
                else:
                    files_to_process.append((output_file_name, wsi_path, checked.pop()))

            return files_to_process

    @property
    def files_to_process_whole(self):
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
        # process the files with coordinates
        if self.coord_path and ((os.path.isdir(self.file_path) and os.path.isdir(self.coord_path)) or (
                os.path.isfile(self.file_path) and os.path.isfile(self.coord_path))):

            for output_file_path, mrxs_path, coord_path in self.files_to_process_patch:
                wsi_img = open_slide(mrxs_path)
                coords = self.parse_xml(coord_path)
                # iterate over the patch-coordinates(s)
                for i, coord in enumerate(coords):
                    appendix = f'-{i}' if len(coords) > 1 else ''
                    output_file_path = f'{output_file_path}{appendix}.png'
                    # skip existing files, if overwrite = False
                    if not self.overwrite and os.path.isfile(output_file_path):
                        print(f'File {output_file_path} already exists. Output saving is skipped. To overwrite add --overwrite.')
                    else:
                        # extract the patch
                        png = self.extract_crop(wsi_img, coord)
                        # save the image
                        print(f'Saving image {output_file_path}')
                        Image.fromarray(png[:, :, :3]).save(output_file_path)

        # process the full image
        elif os.path.isfile(self.file_path) or os.path.isdir(self.file_path):
            for output_file_path, wsi_path in self.files_to_process_whole:
                wsi_img = open_slide(wsi_path)
                # extract the patch
                png = self.extract_crop(wsi_img)
                # save the image
                print(f'Saving image {output_file_path}.png')
                Image.fromarray(png[:, :, :3]).save(f'{output_file_path}.png')

        else:
            # Something went wrong
            print('mrxs (and xml files, if specified) paths are invalid.')

    def parse_xml(self, file_path):
        # reads the xml files and retrieves the coordinates of all elements with the coord_annotation_tag
        tree = ET.parse(file_path)
        root = tree.getroot()

        groups = [self.coord_annotation_tag]
        annotations_elements = {g: [] for g in groups}

        for i in root.iter('Annotation'):
            annotations_elements[i.attrib['PartOfGroup']].append(i)

        annotations = {g: [] for g in groups}
        for group, element_list in annotations_elements.items():
            for element in element_list:
                if element.attrib['Type'] == 'Dot':
                    annotations[group].append(
                        [[float(i.attrib['X']), float(i.attrib['Y'])] for i in element.iter('Coordinate')][0])
                else:
                    annotations[group].append(
                        [[float(i.attrib['X']), float(i.attrib['Y'])] for i in element.iter('Coordinate')])

        return annotations[self.coord_annotation_tag]

    def extract_crop(self, wsi_img, coord=None):
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


if __name__ == '__main__':
    fire.Fire(PngExtractor)
