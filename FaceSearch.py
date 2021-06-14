import os
import sys
import glob
import shutil
import boto3
from botocore.exceptions import ClientError
from PIL import Image
from time import sleep


def downsize_image(input_img, folder, long_edge):
    input_file_name = os.path.basename(input_img)
    temp_file_path = os.path.join(folder, input_file_name)
    try:
        with Image.open(input_img) as im:
            img_size = im.size
            img = im
            img.load()
    except(IOError, SyntaxError):
        print(f'  Problem loading {input_file_name}.')
        return
    temp_dimensions = (long_edge,
                       int(long_edge / (max(img_size) / min(img_size))))
    temp_img = img.resize((temp_dimensions[img_size.index(max(img_size))],
                           temp_dimensions[img_size.index(min(img_size))]),
                          resample = Image.HAMMING,
                          reducing_gap = 2.0)
    if not os.path.exists(folder):
        os.mkdir(folder)
    temp_img.save(temp_file_path,
                  quality = 75)
    print(f'  {input_file_name} downsized.')

    
def index_images(photo, c_id, img_id, maxface):
    client = boto3.client('rekognition', region_name = 'eu-west-2')
    with open(photo, 'rb') as im:
        img = im.read()

    response = client.index_faces(CollectionId = c_id,
                                  Image = {'Bytes': img},
                                  ExternalImageId = img_id,
                                  MaxFaces = maxface,
                                  QualityFilter = 'MEDIUM',
                                  DetectionAttributes = ['ALL'])

    face_count = len(response['FaceRecords'])
    if face_count == 1:
        print(f'  {face_count} face indexed for {os.path.basename(photo)}')
    else:
        print(f'  {face_count} faces indexed for {os.path.basename(photo)}')


def search_collection(photo, c_id, retmode, simthresh):
    client = boto3.client('rekognition', region_name = 'eu-west-2')
    with open(photo, 'rb') as im:
        img = im.read()

    response = client.search_faces_by_image(CollectionId = c_id,
                                            Image = {'Bytes': img},
                                            FaceMatchThreshold = simthresh,
                                            MaxFaces = 4096)
    face_matches = response['FaceMatches']

    if not face_matches:
        print('  No faces matched.')
        return(None)
    else:
        if retmode == '1':
            matches = [(face['Face']['ExternalImageId'], face['Similarity'])
                       for face in face_matches]
            return matches
        else:
            closest_match = [(face_matches[0]['Face']['ExternalImageId'],
                              face_matches[0]['Similarity'])]
            return closest_match


def output_image(returned_img, query_img):
    output_path = os.path.join('FaceSearch Images\\Output\\',
                               (os.path.splitext(
                                   os.path.basename(query_img))[0]
                                + '_' + os.path.basename(returned_img)))
    try:
        shutil.copy2(returned_img, output_path)
    except OSError:
        print('Error when moving file to Output folder.')


def empty_collection(c_id):
    client = boto3.client('rekognition', region_name = 'eu-west-2')
    status_code = 0
    try:
        face_list = client.list_faces(CollectionId = c_id)
        face_list = [x['FaceId'] for x in face_list['Faces']]

        if not face_list:
            print('No faces to delete.')
        else:
            response = client.delete_faces(CollectionId = c_id,
                                           FaceIds = face_list)

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print ('The collection ' + c_id + ' was not found ')
        else:
            print ('Error other than Not Found occurred: ' +\
                   e.response['Error']['Message'])

        status_code = e.response['ResponseMetadata']['HTTPStatusCode']

    return(status_code)


def main():
    try:
        with open('CollectionID.txt', 'r') as f:
            collection_id = f.read()
    except FileNotFoundError:
        print('You have no collection ID. \nPlease speak to Dan who will '
              + 'issue you with one.\n')
        sleep(5)
        sys.exit()
    if not collection_id:
        print('Your collection ID document is empty. Please speak to Dan.\n')
        sleep(5)
        sys.exit()

    # Ask user for return mode.
    print('Return modes:\n1. Return all images that match the query image.\n'
          '2. Return only the closest match to the query image.\n\nPlease '
          'select an option by typing 1 or 2, then press Enter.\n')
    while True:
        return_mode = input()
        if any([return_mode == '1',
                return_mode == '2']):
            break
        else:
            print('\nInvalid input, please try again.\n')

    # Ask for similarity threshold.
    print('\nSimilarity threshold:\nA higher value reduces the number of '
          'incorrect matches,\nbut may result in fewer correct matches being '
          'detected.\nA lower value allows more matches to be detected,\nbut '
          'can include a greater number of incorrect matches.\n\nRecommended '
          'values:\n99 when you want to avoid detecting the wrong people.\n80 '
          'when you want a high chance of finding someone.\n\nPlease type a '
          'value between 0 and 100, then press Enter.\n')
    while True:
        sim_thresh = input()
        try:
            sim_thresh = float(sim_thresh)
        except ValueError:
            print('\nInvalid input, please try again.\n')
        else:
            if 0 <= sim_thresh <= 100:
                break
            else:
                print('\nInvalid input, please try again.\n')

    # Ask for maximum faces to index.
    print('\nPlease enter the maximum number of faces in each database\n'
          'image that you would like to index, then press Enter.\n\nIf you '
          'choose 1, then only the largest face from each database\nimage '
          'will be available to match with a query image.\nIf you would like '
          'everyone in a database image to stand the\nchance of being matched '
          'with a query image, including people\nfar in the background, then '
          'choose a value which is higher\nthan the expected maximum number '
          'of people in every image.\n')
    while True:
        maximum_faces = input()
        try:
            maximum_faces = int(maximum_faces)
        except ValueError:
            print('\nInvalid input, please try again.\n')
        else:
            if maximum_faces >= 1:
                break
            else:
                print('\nInvalid input, please try again.\n')

    # Downsize all images from the Database folder,
    # save to the TEMP/Database folder
    print('\nProducing downsized Database copies.')
    for img_name in glob.glob('FaceSearch Images\\Database\\*.jpg'):
        downsize_image(img_name, 'TEMP\\Database\\', 600)

    # Downsize all images from the Query folder,
    # save to the TEMP/Query folder
    print('\nProducing downsized Query copies.')
    for img_name in glob.glob('FaceSearch Images\\Query\\*.jpg'):
        downsize_image(img_name, 'TEMP\\Query\\', 1000)

    # Index each downsized image to the collection
    print('\nIndexing images.')
    aws_image_id = {}
    id_num = 0
    for img_name in glob.glob('TEMP\\Database\\*.jpg'):
        id_num += 1
        aws_image_id[str(id_num)] = os.path.join(
            'FaceSearch Images\\Database\\', os.path.basename(img_name))
        index_images(img_name, collection_id, str(id_num), maximum_faces)
    print()

    # Search collection for faces found in the Query folder
    # Output images with faces that match each Query image
    for img_name in glob.glob('TEMP\\Query\\*.jpg'):
        print(f'Searching for faces in {os.path.basename(img_name)}')
        search_result = search_collection(img_name, collection_id, return_mode,
                                          sim_thresh)
        if not search_result:
            pass
        else:
            for r in search_result:
                match_img = aws_image_id[r[0]]
                print(f'  {os.path.basename(match_img)} matched with a '
                      f'similarity of {round(r[1], 4)}%')
                output_image(match_img, img_name)

    # Empty collection
    print('\nRemoving faces from collection')
    status_code = empty_collection(collection_id)
    if status_code == 0:
        print('Collection successfully emptied.')
    else:
        print('Problem removing faces from collection')

    # Delete files in TEMP folders
    print('\nRemoving temporary files')
    file_list = glob.glob('TEMP\\**\\*.jpg', recursive = True)
    for file_path in file_list:
        try:
            os.remove(file_path)
        except OSError:
            print('Error while deleting temporary file')
    print('Temporary files deleted.')
    
    input('\nPress enter to quit.')


if __name__ == '__main__':
    main()

