import os
import pandas as pd
import glob
import fire
import xml.etree.ElementTree as ET
from PIL import Image

import platform

# fix for windows
if platform.system() == 'Windows':
    print('INFO: Path to openslide ddl is manually added to the path.')
    openslide_path = r'C:\Users\ls19k424\Documents\openslide-win64-20171122\bin'
    os.environ['PATH'] = openslide_path + ";" + os.environ['PATH']
import openslide

from wsi_to_png import PngExtractor


class AsapPngExtractor(PngExtractor):
    """
    This Object extracts (patches of) an mrxs file to a png format.

    :param file_path: string
        path to the mrxs single file or folder of files.
    :param output_path: string
        path to the output folder. The output format is the same name as the mrxs file,
        with an appendix if multiple patches are extracted.
    :param coord_path: string
        Path to the coordinate xml files (created with ASAP) single file or folder of files
        If not provided, the full image is converted into a png.
    :param coord_annotation_tag: string (optional)
        Name of the annotation group in the xml file (default is 'hotspot').
    :param matched_files_excel: str
        Optional. If provided, then this file will be used to match the xmls to the mrxs file names (needs to contain
        a column called "WSI-names" and "XML-names"
    :param staining: Staining identifier, that would be specified right before .mrxs (e.g. CD8) (optional, default is '')
    :param level: int (optional)
        Level of the mrxs file that should be used for the conversion (default is 0).
    :param overwrite: overides exisiting extracted patches (default is False)
    """

    def __init__(self, file_path: str, output_path: str, coord_path: str, staining: str = '',
                 coord_annotation_tag: str = 'hotspot', level: int = 0, overwrite: bool = False,
                 matched_files_excel: str = None):
        # initiate properties from parent class
        super().__init__(file_path=file_path, output_path=output_path, staining=staining, level=level,
                         overwrite=overwrite)
        # instantiate class parameters
        self.coord_path = coord_path
        self.coord_annotation_tag = coord_annotation_tag
        self.matched_files_excel = matched_files_excel

    @property
    def coord_files(self):
        if self.coord_path:
            return glob.glob(os.path.join(self.coord_path, f'*{self.staining}.xml')) if os.path.isdir(
                self.coord_path) else [self.coord_path]
        else:
            return None

    # overwrite
    @property
    def files_to_process(self):
        # we only have one file to process
        if len(self.wsi_files) == 1:
            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            output_file_name = os.path.join(self.output_path,
                                            f'{filename}-level{self.level}-{self.coord_annotation_tag}')
            # skip existing files, if overwrite = False
            if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                print(
                    f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
            else:
                return [(output_file_name, self.file_path, self.coord_path)]

        # we have multiple files to process
        else:
            # TODO: make it possible to parse a csv or excel file that has the matched up xmls and mrxs file names
            if self.matched_files_excel:
                # excel containing matched files is provided
                files_to_process = self._parse_matched_files_excel()
            else:
                # files need to be matched
                files_to_process = self._match_files()

            return files_to_process

    def _parse_matched_files_excel(self):
        files_to_process = []
        df = pd.read_excel(self.matched_files_excel)
        for wsi_path in self.wsi_files:
            filename = os.path.splitext(os.path.basename(wsi_path))[0]
            output_file_name = os.path.join(self.output_path,
                                            f'{filename}-level{self.level}-{self.coord_annotation_tag}')
            # skip existing files, if overwrite = False
            if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                print(
                    f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
                continue
            # get the name of the xml file from the excel
            xmls_name = ''
            xmls_name = os.path.join(self.coord_path, xmls_name)
            files_to_process.append((output_file_name, wsi_path, xmls_name))

        return files_to_process

    def _match_files(self):
        # create a list of the paired mrxs and coordinate files
        # only take files that have a corresponding coordinates file
        files_to_process = []
        for wsi_path in self.wsi_files:
            filename = os.path.splitext(os.path.basename(wsi_path))[0]
            output_file_name = os.path.join(self.output_path,
                                            f'{filename}-level{self.level}-{self.coord_annotation_tag}')
            # skip existing files, if overwrite = False
            if not self.overwrite and os.path.isfile(f'{output_file_name}.png'):
                print(
                    f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite.')
                continue

            checked = []
            for coord_file in self.coord_files:
                if filename in coord_file:
                    checked.append(coord_file)
            if len(checked) != 1:
                print(
                    f'File {filename}.mrxs/.ndpi does not have a / too many corresponding xml file/s. File will be skipped.')
            else:
                files_to_process.append((output_file_name, wsi_path, checked.pop()))

        return files_to_process

    # overwrite
    def process_files(self):
        # process the files with coordinates
        if ((os.path.isdir(self.file_path) and os.path.isdir(self.coord_path)) or (
                os.path.isfile(self.file_path) and os.path.isfile(self.coord_path))):

            for output_file_path, mrxs_path, coord_path in self.files_to_process:
                assert os.path.isfile(mrxs_path)
                wsi_img = openslide.open_slide(mrxs_path)
                coords = self.parse_xml(coord_path)
                # iterate over the patch-coordinates(s)
                for i, coord in enumerate(coords):
                    appendix = f'-{i}' if len(coords) > 1 else ''
                    output_file_path = f'{output_file_path}{appendix}.png'
                    # skip existing files, if overwrite = False
                    if not self.overwrite and os.path.isfile(output_file_path):
                        print(
                            f'File {output_file_path} already exists. Output saving is skipped. To overwrite add --overwrite.')
                    else:
                        # extract the patch
                        png = self.extract_crop(wsi_img, coord)
                        # save the image
                        print(f'Saving image {output_file_path}')
                        Image.fromarray(png[:, :, :3]).save(output_file_path)

        else:
            # Something went wrong
            print('mrxs and/or xml file paths are invalid.')

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


def extract_patch(file_path: str, output_path: str, coord_path: str, staining: str = '',
                  coord_annotation_tag: str = 'hotspot',
                  level: int = 0, overwrite: bool = False, matched_files_excel: str = None):
    png_extractor = AsapPngExtractor(file_path=file_path, output_path=output_path, staining=staining, level=level,
                                     overwrite=overwrite, coord_path=coord_path,
                                     coord_annotation_tag=coord_annotation_tag, matched_files_excel=matched_files_excel)
    # process the files
    png_extractor.process_files()


if __name__ == '__main__':
    fire.Fire(extract_patch)
