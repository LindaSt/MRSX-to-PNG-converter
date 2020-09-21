import os
import numpy as np
import glob
from openslide import open_slide
import fire
import xml.etree.ElementTree as ET
from PIL import Image


def parse_xml(file_path, coord_annotation_tag='hotspot'):
    # reads the xml files and retrieves the coordinates of all elements with the coord_annotation_tag
    tree = ET.parse(file_path)
    root = tree.getroot()

    groups = [coord_annotation_tag]
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

    return annotations[coord_annotation_tag]


def extract_crop(mrxs_file, level, coord=None):
    # crop the region of interest from the mrxs file on the specified level
    # get the level and the dimensions
    id_level = np.argmax(np.array(mrxs_file.level_downsamples) == level)
    dims = mrxs_file.level_dimensions[id_level]

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
    img = mrxs_file.read_region(top_left_coord, id_level, size)

    # Convert to img
    img = np.array(img)
    img[img[:, :, 3] != 255] = 255
    return img


def get_files_to_process(mrxs_files, coord_files):
    # create a list of the paired mrxs and coordinate files
    # only take files that have a corresponding coordinates file
    files_to_process = []
    for mrxs_path in mrxs_files:
        filename = os.path.splitext(os.path.basename(mrxs_path))[0]
        checked = []
        for coord_file in coord_files:
            if filename in coord_file:
                checked.append(coord_file)
        if len(checked) != 1:
            print(f'File {filename}.mrxs does not have a / too many corresponding xml file/s. File will be skipped.')
        else:
            files_to_process.append((filename, mrxs_path, checked.pop()))

    return files_to_process
    # return [(fn, mf, cf) for fn, mf, cf in zip(file_names, mrxs_files, coord_files_checked)]


def main(file_path, output_path,
         coord_path: str = '', staining: str = '', coord_annotation_tag: str = 'hotspot', level: int = 0, overwrite: bool = False):
    """
    This function converts (patches of) an mrxs file to a png format.

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
    # create the output folder, if it does not exist
    if not os.path.isdir(output_path):
        os.makedirs(output_path)

    # if we have xml files with coordinates, patches are extracted
    if (os.path.isdir(file_path) and os.path.isdir(coord_path)) or (os.path.isfile(file_path) and os.path.isfile(coord_path)):
        # get the files to be processed (depending on whether it's a folder or just a file
        if os.path.isdir(file_path) and os.path.isdir(coord_path):
            mrxs_files = glob.glob(os.path.join(file_path, f'*{staining}.mrxs'))
            coord_files = glob.glob(os.path.join(coord_path, f'*{staining}.xml'))
            files_to_process = get_files_to_process(mrxs_files, coord_files)
        elif os.path.isfile(file_path) and os.path.isfile(coord_path):
            mrxs_files = [file_path]
            coord_files = [coord_path]
            files_to_process = [(os.path.splitext(os.path.basename(file_path))[0], file_path, coord_path)]

        # process the files
        for file_name, mrxs_path, coord_path in files_to_process:
            mrxs_file = open_slide(mrxs_path)
            coords = parse_xml(coord_path, coord_annotation_tag)
            # iterate over the patch-coordinates(s)
            for i, coord in enumerate(coords):
                # extract the patch
                png = extract_crop(mrxs_file, level, coord)
                # save the image
                file_name = os.path.splitext(os.path.basename(mrxs_path))[0]
                output_file_name = os.path.join(output_path, f'{file_name}.png')
                if overwrite:
                    Image.fromarray(png[:, :, :3]).save(output_file_name)
                else:
                    if os.path.isfile(output_file_name):
                        print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --overwrite')
                    else:
                        Image.fromarray(png[:, :, :3]).save(os.path.join(output_path, f'{file_name}.png'))

    # if no coordinates are specified, the full image is extracted
    elif os.path.isfile(file_path) or os.path.isdir(file_path):
        print('No coordinates xml file specified, extracting full image(s).')
        mrxs_files = glob.glob(os.path.join(file_path, '*.mrxs')) if os.path.isdir(file_path) else [file_path]

        # process the files
        for mrxs_path in mrxs_files:
            mrxs_file = open_slide(mrxs_path)
            # extract the patch
            png = extract_crop(mrxs_file, level)
            # save the image
            file_name = os.path.splitext(os.path.basename(mrxs_path))[0]
            output_file_name = os.path.join(output_path, f'{file_name}.png')
            if overwrite: # TODO: refactor this to skip whole processing and make code cleaner for full extraction (unify)
                Image.fromarray(png[:, :, :3]).save(output_file_name)
            else:
                if os.path.isfile(output_file_name):
                    print(f'File {output_file_name} already exists. Output saving is skipped. To overwrite add --')
                else:
                    Image.fromarray(png[:, :, :3]).save(os.path.join(output_path, f'{file_name}.png'))

    else:
        # Something went wrong
        print('mrxs (and xml files, if specified) paths are invalid.')


if __name__ == '__main__':
    fire.Fire(main)
