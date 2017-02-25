import cv2
from sheethandler import fullpage, halfpage, handwriting
from utility.ocr import adjustOrientation, getGridlinePositions
import numpy as np

def recognizeJPG(path, sheet_type):
    '''
    given path and type, return the recognition result in dictionary format:
    Success
        {"status": "Success", "Result": {"id": ..., }}
    Failure:
        {"status": "Error", "Result": {"message": ...}}
    '''
    grayscale_image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    _, binary_image = cv2.threshold(grayscale_image, 200, 255,
                                    cv2.THRESH_BINARY_INV)
    kernel = np.ones((3,3),np.uint8)
    # binary_image = cv2.dilate(binary_image, kernel, iterations=1)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)


    binary_image, contours, centers = adjustOrientation(binary_image)

    # _, binary_image = cv2.threshold(grayscale_image, 128, 255,
    #                             cv2.THRESH_BINARY_INV)
    horizontal_pos, vertical_pos = getGridlinePositions(binary_image, contours, centers)

    recognizers = {"fullpage": fullpage.recognizeSheet,
                    "halfpage": halfpage.recognizeSheet,
                    "handwriting": handwriting.recognizeSheet}

    return recognizers[sheet_type](binary_image, horizontal_pos, vertical_pos)