from processor.utility.ocr import *
import cv2
from processor.sheethandler.SheetHandler import recognizeSheet
import time
# from processor import recognizeJPG
# pdf2jpg('../data/QR_2B_Answersheet.pdf')
for i in range(0,1):
    # print ('loading ' + 'data/QR_2B_Answersheet-{}.jpg'.format(i))
    grayscale_image = cv2.imread('/Users/Norman/git/Answer-Sheet-OCR/ocr/data/half-0.jpg'.format(i), cv2.IMREAD_GRAYSCALE)
    binary_image = binarizeImage(grayscale_image)
    cv2.imwrite('tmp/binarized.jpg'.format(i), binary_image)
    kernel = np.ones((3,3),np.uint8)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
    cv2.imwrite('tmp/morphologyEx.jpg'.format(i), binary_image)
    binary_image, original_image, centers = adjustOrientation(binary_image, grayscale_image, 'tmp/detect_{}.jpg'.format(i))
    contours = getQRCornerContours(binary_image, True)
    cv2.imwrite('tmp/handwritten.jpg', original_image)
    h, w = binary_image.shape
    cv2.imwrite('tmp/binary_image.jpg', binary_image)
    horizontal_pos, vertical_pos = getGridlinePositions(binary_image, contours, centers)
    t = time.time()
    print "\n\nstart standard recognition...\n\n"
    print recognizeSheet('/Users/Norman/git/Answer-Sheet-OCR/ocr/data/half-0.jpg', 'half')
    print time.time() - t
    color_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
    cv2.drawContours(color_image, contours, -1, (0, 255, 0), thickness=10)

    for c in vertical_pos:
        cv2.line(color_image, (c, 0), (c, h-1), (0, 255, 0), thickness=10)
    for r in horizontal_pos:
        cv2.line(color_image, (0, r), (w-1, r), (0, 255, 0), thickness=10)

    color_image = cv2.resize(color_image, (w//3, h//3))
    import matplotlib.pyplot as plt
    plt.imshow(color_image)
    # cv2.imshow('gray', color_image)
    # cv2.imshow('name', name)
    # cv2.waitKey(1)
    # cv2.destroyAllWindows()
