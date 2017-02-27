import cv2
from ..utility.ocr import extractGrids, getRatioFromStripe, getDigitFromSequence, getAnswerFromSequence
from ..utility.io import saveToDir
from .. import settings

data_section = {
    "name": (1, 0, 2, 5),
    "id": [(j, i, 10, 1) for j in [5, 16] for i in range(6)],
    "single_choice": [(i, j, 2, 2) for j in range(7, 26, 2) for i in range(1, 11, 3)],
    "true_false": [(16, i, 2, 2) for i in range(7, 26, 2)],
    "multiple_choice": [(i, j, 1, 5) for j in range(7, 26, 5)]
}

def recognizeSheet(binary_image, horizontal_pos, vertical_pos):
    def getNameImage():
        '''
        return the area of image
        '''
        return extractGrids(binary_image, horizontal_pos, vertical_pos, *data_section["name"])

    def getNameImagePath():
        image = getNameImage()
        _, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY_INV)
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
        for r, c, h, w in data_section["question"]:
            stripe = extractGrids(binary_image, horizontal_pos, vertical_pos, r, c, h, w)
            # cv2.imshow('stripe', stripe)
            # cv2.waitKey(0)
            sequence = getRatioFromStripe(stripe, 5)
            # print (sequence)
            answer = getAnswerFromSequence(sequence)
            result.append(answer)
        return result


    result = {"id" : recognizeId(),
              "answer" : recognizeAnswer(),
              "name_image": getNameImagePath()}
    print (result)


