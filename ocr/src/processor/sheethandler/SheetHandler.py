
import cv2
from itertools import chain
from ..utility.ocr import *
import numpy as np

from ..utility.io import saveToDir
from .. import settings
from utility import getBlockProblemPositions

SheetSectionPositions = {"half": {
        "name": (1, 0, 3, 12),
        "id": [(3, 14 + 2 * i, 10, 2) for i in range(12)],
        "question": getBlockProblemPositions(8, 2, 1, 2, 5, 5) \
            + getBlockProblemPositions(14, 2, 1, 2, 5, 5) \
            + getBlockProblemPositions(20, 2, 1, 2, 5, 5) \
            + getBlockProblemPositions(14, 15, 1, 2, 5, 5) \
            + getBlockProblemPositions(20, 15, 1, 2, 5, 5) \
            + getBlockProblemPositions(14, 28, 1, 2, 5, 5) \
            + getBlockProblemPositions(20, 28, 1, 2, 5, 5),
}, "full": {
        "name": (0, 0, 2, 8),
        "id": [(2, 9 + 2 * i, 10, 2) for i in range(12)],
        "question": chain(*[getBlockProblemPositions(14 + r * 6, 0 + c * 12, 1, 2, 5, 5) for c in range(3) for r in range(5)])
}}


def recognizeSheet(path, sheet_type):

    data_section = SheetSectionPositions[sheet_type]

    grayscale_image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    binary_image = binarizeImage(grayscale_image)
    kernel = np.ones((3,3),np.uint8)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
    binary_image, original_image, centers = adjustOrientation(binary_image, grayscale_image)
    contours = getQRCornerContours(binary_image)
    horizontal_pos, vertical_pos = getGridlinePositions(binary_image, contours, centers)


    def getNameImage():
        '''
        return the area of image
        '''
        return extractGrids(original_image, horizontal_pos, vertical_pos, *data_section["name"])

    def getNameImagePath():
        image = getNameImage()
        # _, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY_INV)

        return saveToDir(image, settings.name_dir)

    def getIdImage(image_id):
        # TODO
        # extract images
        pass

    def recognizeId():
        result = list()
        for r, c, h, w in data_section['id']:
            stripe = extractGrids(binary_image, horizontal_pos, vertical_pos, r, c, h, w)
            sequence = getRatioFromStripe(stripe, 10)
            digit = getDigitFromSequence(sequence)
            result.append(digit)
        return "".join(result).strip("-")


    def recognizeAnswer():
        result = list()
        i = 0
        for r, c, h, w in data_section["question"]:
            i += 1
            stripe = extractGrids(binary_image, horizontal_pos, vertical_pos, r, c, h, w)
            cv2.imwrite('tmp/{}.jpg'.format(i), stripe)
            sequence = getRatioFromStripe(stripe, 5)
            answer = getAnswerFromSequence(sequence)
            result.append(answer)
        return result


    result = {"id" : recognizeId(),
              "answer" : recognizeAnswer(),
              "name_image": getNameImagePath()}
    return result
