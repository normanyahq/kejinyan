
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
        "choice_num": [5] * 35
}, "full": {
        "name": (0, 0, 2, 8),
        "id": [(2, 9 + 2 * i, 10, 2) for i in range(12)],
        "question": list(chain(*[getBlockProblemPositions(14 + r * 6, 0 + c * 12, 1, 2, 5, 5) for c in range(3) for r in range(5)])),
        # be careful, itertools can be used only once
        "choice_num": [5] * 75
}, "full_old": {
        "name": (1, 0, 1, 5),
        "id": [(j, i, 10, 1) for j in [4, 15] for i in range(5)],
        "question": [(i, j, 1, 5) for j in [7, 14, 21] for i in range(25)],
        "choice_num": [5] * 75
}, "half_old": {
        "name": (1, 0, 1, 5),
        "id": [(4, i, 10, 1) for i in range(6)],
        "question": [(i, 1, 1, 5) for i in range(15, 25)] + [(i, 8, 1, 5) for i in range(25)],
        "choice_num" : [5] * 35
}, "makesi": {
        "name": (2, 0, 2, 11),
        "class": (5, 0, 2, 11),
        "id": [(4, 13 + i * 2, 10, 2) for i in range(10)],
        "question": list(chain(*[getBlockProblemPositions(19 + r * 6, 1 + c * 11, 1, 2, 5, 4) for c in range(2) for r in range(4)])) \
            + list(chain(*[getBlockProblemPositions(19, 24, 1, 2, 5, 4)])) \
            + list(chain(*[getBlockProblemPositions(28 + r * 6, 26, 1, 2, 5, 2) for r in range(2)])),
        "choice_num": [4] * 45 + [2] * 10
}, "english": {
        "name": (1, 0, 2, 8),
        "id": [(3, 9 + 2 * i, 10, 2) for i in range(12)],
        "question": list(chain(*[getBlockProblemPositions(16, 0 + c * 11, 1, 2, 5, 3, False) for c in range(3)])) \
            + getBlockProblemPositions(21, 0, 1, 2, 5, 3, False) \
            + list(chain(*[getBlockProblemPositions(21, 11 + c * 11, 1, 2, 5, 4, False) for c in range(2)])) \
            + getBlockProblemPositions(27, 0, 1, 2, 5, 4, False) \
            + getBlockProblemPositions(27, 11, 1, 2, 5, 7, False) \
            + getBlockProblemPositions(27, 22, 1, 2, 5, 7, False) \
            + list(chain(*[getBlockProblemPositions(36, 0 + c * 11, 1, 2, 5, 4, False) for c in range(3)])),
        "choice_num": [3] * 20 + [4] * 15 + [7] * 5 + [4] * 20
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
            # cv2.imwrite('/tmp/{}.jpg'.format(i), stripe)
            sequence = getRatioFromStripe(stripe, data_section["choice_num"][i-1])
            answer = getAnswerFromSequence(sequence)
            result.append(answer)
        return result


    result = {"id" : recognizeId(),
              "answer" : recognizeAnswer(),
              "name_image": getNameImagePath()}
    return result
