"""Pipeline for loading DICOM images and corresponding contour files"""
import os
import os.path
import re
import csv
import random
from multiprocessing import Process, Queue
import numpy as np
import parsing


def enumerate_data_files(dicom_dir, contour_dir):
    """Enumerate file paths of DICOMs with corresponding contour files

    :param dicom_dir: path to the directory of DICOM files
    :param contour_dir: path to the directory of contour files
    :return: generator over (dicom_path, contour_path) tuples
    """

    dicom_files = {}
    contour_files = {}

    for dicom_name in os.listdir(dicom_dir):
        match = re.match(r'^(\d+).dcm$', dicom_name)
        if match:
            dicom_id = match.group(1)
            dicom_files[dicom_id] = os.path.join(dicom_dir, dicom_name)

    for contour_name in os.listdir(contour_dir):
        match = re.match(r'^IM-\d+-(\d+)-[io]contour-manual.txt$', contour_name)
        if match:
            contour_id = match.group(1).lstrip('0')
            contour_files[contour_id] = os.path.join(contour_dir, contour_name)

    # only iterate over the intersection of the IDs (have both a DICOM and a contour)
    loadable_ids = dicom_files.keys() & contour_files.keys()
    return ((dicom_files[i], contour_files[i]) for i in loadable_ids)


def stub_data_loader(dicom_file, contour_file):
    """Stub data loader implementation for testing the pipeline"""

    return (dicom_file, contour_file)

def load_data_files(dicom_file, contour_file):
    """Load DICOM and corresponding contour file from disk

    :param dicom_file: path to the DICOM file
    :param contour_dir: path to the contour file
    :return: (dicom_image, contour_mask) tuple
    """

    # if loading any of the resources fails, just return None so it will be
    # skipped by the consumer
    print("loading DICOM {}".format(dicom_file))
    dicom = parsing.parse_dicom_file(dicom_file)
    if dicom is None:
        return None
    dicom_size = np.shape(dicom)
    print("loading contour {}".format(contour_file))
    contour = parsing.parse_contour_file(contour_file)
    if contour is None:
        return None
    mask = parsing.poly_to_mask(contour, dicom_size[0], dicom_size[1])
    if mask is None:
        return None
    return (dicom, mask)

def data_load_worker(data_files, batch_size, result_queue, loader_fn=load_data_files):
    """Load data files in batches. Should run in a separate process.

    :param data_files: list of data file tuples
    :param batch_size: number files to load in a batch
    :param result_queue: queue where results will be pushed
    """

    print("worker started")
    dicom_batch = []
    contour_batch = []
    for (dicom_file, contour_file) in data_files:
        try:
            loaded = loader_fn(dicom_file, contour_file)
        except Exception as err:
            print("error loading files: {}".format(err))
            continue
        if loaded is None:
            continue
        dicom_batch.append(loaded[0])
        contour_batch.append(loaded[1])
        if len(dicom_batch) >= batch_size:
            result_queue.put((np.array(dicom_batch), np.array(contour_batch)))
            dicom_batch = []
            contour_batch = []

    # signal that we're done loading data
    result_queue.put(None)


def async_load_data(data_dir, batch_size=8, test=False):
    """Load batches of data randomly and asynchronously

    :param data_dir: path to the base data directory
    :return: generator over batches of training data
    """

    data_files = []
    for study in get_directory_links(data_dir):
        data_files.extend(enumerate_data_files(study[0], study[1]))

    random.shuffle(data_files)
    result_queue = Queue(maxsize=2)
    data_loader_fn = load_data_files
    if test:
        data_loader_fn = stub_data_loader
    worker = Process(target=data_load_worker,
                     args=(data_files, batch_size, result_queue, data_loader_fn))
    worker.start()
    print("worker starting...")

    while True:
        result = result_queue.get()
        if result is None:
            break
        yield result

    worker.join()
    print("worker finished")


def get_directory_links(data_dir):
    """Get links between DICOM and contour directories

    :param data_dir: path to the base data directory
    :return: list of (DICOM_dir, contour_dir) tuples
    """
    with open(os.path.join(data_dir, 'link.csv'), 'r') as linkfile:
        reader = csv.reader(linkfile)
        next(reader, None)  # skip csv header
        return [(os.path.join(data_dir, 'dicoms', row[0]),
                 os.path.join(data_dir, 'contourfiles', row[1], 'i-contours'))
                for row in reader]


if __name__ == '__main__':
    test=False
    if 'TEST' in os.environ:
        test = True
    for batch in async_load_data('final_data', test=test):
        print("main process received a batch")
        if test:
            print(batch)

