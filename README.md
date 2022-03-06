## FaceSearch

Software which uses the AWS Rekognition SearchFaces function to find people in images using face recognition.

The program is provided with a folder of images you want to search *in* and a folder containing images you want to search *for*. It then looks through each image in the latter folder, returning every image in the former folder which contains their face.

The identity of the people in the image should always be confirmed via established methods, but experience has shown that it is very accurate. On many occasions it has been able to correctly identify people who, between photographs, have aged to the extent that they are unrecognisable to human observers.
