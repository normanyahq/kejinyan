import cv2
from sheethandler import fullpage, halfpage, handwriting
from utility.ocr import adjustOrientation, getGridlinePositions, getQRCornerContours, binarizeImage
import numpy as np
import traceback

def recognizeJPG(path, sheet_type):
    '''
    given path and type, return the recognition result in dictionary format:
    Success
        {"status": "success", "path": "/path/to/file", "result": {"id": ..., }}
    Failure:
        {"status": "error", "path": "/path/to/file", "message": "error messages..."}
    '''
    grayscale_image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    binary_image = binarizeImage(grayscale_image)
    kernel = np.ones((3,3),np.uint8)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)


    binary_image, centers = adjustOrientation(binary_image)
    contours = getQRCornerContours(binary_image)

    horizontal_pos, vertical_pos = getGridlinePositions(binary_image, contours, centers)

    recognizers = {"fullpage": fullpage.recognizeSheet,
                    "halfpage": halfpage.recognizeSheet,
                    "handwriting": handwriting.recognizeSheet}
    message = str()
    try:
        result = recognizers[sheet_type](binary_image, horizontal_pos, vertical_pos)
        return {"status": 'success', "path": path, "result": result}
    except:
        message = traceback.format_exc()
        return {"status": 'error', "path": path, "message": message}
