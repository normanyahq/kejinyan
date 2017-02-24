import cv2
from sheethandler import fullpage, halfpage, handwriting
from utility.ocr import adjustOrientation, getGridlinePositions


def recognizeJPG(path, sheet_type):
    '''
    given path and type, return the recognition result in dictionary format:
    Success
        {"status": "Success", "Result": {"id": ..., }}
    Failure:
        {"status": "Error", "Result": {"message": ...}}
    '''
    grayscale_image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    _, binary_image = cv2.threshold(grayscale_image, 128, 255,
                                    cv2.THRESH_BINARY_INV)

    binary_image, contours, centers = adjustOrientation(binary_image)

    # _, binary_image = cv2.threshold(grayscale_image, 128, 255,
    #                             cv2.THRESH_BINARY_INV)
    horizontal_pos, vertical_pos = getGridlinePositions(binary_image, contours, centers)

    recognizers = {"fullpage": fullpage.recognizeSheet,
                    "halfpage": halfpage.recognizeSheet,
                    "handwriting": handwriting.recognizeSheet}

    return recognizers[sheet_type](binary_image, horizontal_pos, vertical_pos)