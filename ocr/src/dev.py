from utility import *
import cv2
# pdf2jpg('../data/QR_2B_Answersheet.pdf')
for i in range(1, 5):
    grayscale_image = cv2.imread('data/QR_2B_Answersheet-{}.jpg'.format(i), cv2.IMREAD_GRAYSCALE)
    grayscale_image, contours, centers = adjustOrientation(grayscale_image, 'tmp/detect_{}.jpg'.format(i))
    _, binary_image = cv2.threshold(grayscale_image, 50, 255,
                                    cv2.THRESH_BINARY_INV)

    h, w = binary_image.shape

    horizontal_pos, vertical_pos = getGridlinePositions(binary_image, contours, centers)

    color_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
    for c in vertical_pos:
        cv2.line(color_image, (c, 0), (c, h-1), (0, 255, 0), thickness=10)
    for r in horizontal_pos:
        cv2.line(color_image, (0, r), (w-1, r), (0, 255, 0), thickness=10)

    color_image = cv2.resize(color_image, (w//3, h//3))
    cv2.imshow('color_image', color_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
