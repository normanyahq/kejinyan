from __future__ import division, print_function

import cv2
import wand.image
import PIL.Image
import numpy as np
import subprocess
import re
import time
from .common import getSquareDist
# from PyPDF2 import PdfFileReader
from ..utility.common import timeit

#timeit
def binarizeImage(gray_image):
    '''
    Given an grayscale image,
    return the inversed binary image.
        the main idea is:
            OSTU threshold with gamma correction
    '''

    # gamma correction
    # learned from university physics
    # many students failed in the final test
    # and the instructor, Shan Qiao, did it twice
    # and saved most (all?) of us

    rescale = lambda x: (25.5 * np.sqrt(x / 2.55))

    gray_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
    ret3, th3 = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ret3, th3 = cv2.threshold(gray_image, rescale(ret3), 255, cv2.THRESH_BINARY_INV)
    return th3

def getPDFPageNum(file_path):
    '''
    This is a fast version to get PDF Page Number
    reutrn 0 for malformated PDF
    '''
    # command example:
    # gs -dNODISPLAY -dBATCH -dNOPAUSE -o /dev/null ./half_a4.pdf \
    #    | grep -e '^Page \d+$'\
    #    | wc -l
    params = ["gs",
              "-dNOPAUSE",
              "-sDEVICE=nullpage", # this is a must, otherwise it will hang
              "-o/dev/null",
              "-dBATCH",
              file_path]
    result = subprocess.check_output(params)
    return len(re.findall("Page\s\d+", result))



# deprecated, will hang when the malformated file
# is relatively large
def _getPDFPageNum(file_path):
    '''
    given a file path, return the number of pages of pdf
    if the pdf file is invalid, return 0
    '''
    try:
        pdf = PdfFileReader(open(file_path, 'rb'))
        return pdf.getNumPages()
    except:
        import traceback
        traceback.print_exc()
        return 0



def pdf2jpg(file_path, resolution=300, save_path=None):
    '''
    convert pdf into jpg.
    if the pdf file, for example, a.pdf has more than one pages,
    the output filenames will be named as:
    a-00000.jpg, a-00001.jpg, a-00002.jpg, ...
    '''
    save_path = file_path.replace(".pdf", "")
    # command example:
    #   gs -dNOPAUSE -q -sDEVICE=jpeg -dBATCH -r300 -sOutputFile=a-%05d.jpg half.pdf
    params = ["gs",
              "-dNOPAUSE",
              "-sDEVICE=jpeg",
              "-dBATCH",
              "-q", # run silently
              "-r{}".format(resolution),
              "-sOutputFile={}-%05d.jpg".format(save_path),
              file_path]
    subprocess.call(params)


# deprecated, 10x slower than current version
# remain for potential use in AWS lambda
def _pdf2jpg(file_path, resolution=300, save_path=None):
    '''
    convert pdf into jpg.
    if the pdf file, for example, a.pdf has more than one pages,
    the output filenames will be named as:
    a-0.jpg, a-1.jpg, a-2.jpg, ...
    '''
    with wand.image.Image(filename=file_path, resolution=resolution) as img:
        if not save_path:
            save_path = file_path.replace(".pdf", ".jpg")
        print ('Save file to:', save_path)
        img.save(filename=save_path)

def getLastCorner(centers):
    '''
    Given the centers of 3 corners, return the 4th corner.
    Note: We assume that the image is already in correct orientation,
        and centers are stored in following order:
            topleft(p1) -> bottomleft(p2) -> topright(p3)
        so we use vector v(p1->p2) + v(p1->p3) to predict the 4th corner
    '''
    assert len(centers) == 3
    p1, p2, p3 = centers[:]
    return (p2[0]+p3[0]-p1[0], p2[1]+p3[1]-p1[1],)

#timeit
def rotateImage(gray_image, degree, expand=True):
    '''
    rotate the image clockwise by given degrees using pillow library
    '''
    im = PIL.Image.fromarray(gray_image)
    return np.asarray(im.rotate(degree, expand=expand))


def getPixelListCenter(pixels):
    '''
    given a list of pixels, return a tuple of their center
    '''
    return tuple(np.mean(pixels, axis=0).astype('uint32')[0])

#timeit
def getQRCornerContours(gray_image, t=False):
    '''
    given binary image, return the pixel lists of their contours:
    '''

    #timeit
    def getContourDepth(hierarchy):
        result = dict()
        def _getDepth(hierarchy, i):
            if i in result:
                return result[i]
            Next, Previous, First_Child, Parent = 0, 1, 2, 3
            cur_index = hierarchy[i][First_Child]
            children_indexes = list()
            while cur_index != -1:
                children_indexes.append(cur_index)
                cur_index = hierarchy[cur_index][Next]
            if children_indexes:
                result[i] = max(map(lambda x: _getDepth(hierarchy, x), children_indexes)) + 1
            else:
                result[i] = 1
            return result[i]

        for i in range(len(hierarchy)):
            if i not in result:
                result[i] = _getDepth(hierarchy, i)

        return result

    #timeit
    def filter_with_shape(contours, err_t=1.5):
        '''
        remove squares whose min bouding rect is not like square
        '''
        ratios = list()
        for i in range(len(contours)):
            rect = cv2.boundingRect(contours[i])
            ratios.append(max(rect[3], rect[2]) / min(rect[3], rect[2]))
        # print (sorted(ratios))
        valid_index = filter(lambda i: ratios[i] <=err_t, range(len(contours)))
        contours = [contours[i] for i in valid_index]
        return contours

    #timeit
    def filter_with_positions(contours, err_t=0.1):
        '''
        find all contours triplets whose centers are most similar to a right
        triangle:
                abs(sqrt(a^2 + b^2) - c) < err_t
        and pick the triplet which forms the larget triangle
        '''
        centers = list(map(lambda c: getPixelListCenter(c), contours))

        i, j, k = 0, 1, 2
        min_err = float('inf')
        triplets = list()
        while i+2 != len(contours):
            j = i + 1
            while j+1 != len(contours):
                k = j + 1
                while k != len(contours):
                    tri_edge_sqr = [getSquareDist(centers[i], centers[k]),
                        getSquareDist(centers[i], centers[j]),
                        getSquareDist(centers[j], centers[k])]
                    tri_edge_sqr.sort()
                    err = abs(tri_edge_sqr[0] + tri_edge_sqr[1] - tri_edge_sqr[2]) / tri_edge_sqr[2]
                    if err < err_t:
                        triplets.append((i, j, k, tri_edge_sqr[2]))
                    k += 1
                j += 1
            i += 1
        triplets.sort(key=lambda x: x[3]) # sort with the largest edge
        best_triplet = triplets[-1]
        contours = [contours[best_triplet[0]], contours[best_triplet[1]], contours[best_triplet[2]]]
        return contours

    #timeit
    def rearrange_contours(contours):
        '''
        use polar coordinates to rearrange contours in counter-clockwise order,
        and the contour on right angle is the first element in rearranged array
        '''
        centers = list(map(lambda c: getPixelListCenter(c), contours))
        triangle_center = np.mean(np.array(centers), axis=0)
        std_centers = list(map(lambda (x, y): (x-triangle_center[0], triangle_center[1]) - y, centers))
        theta_index = zip(map(lambda (x, y): np.arctan2(y, x), std_centers), range(len(contours)))
        theta_index.sort()
        contours = [contours[i] for theta, i in theta_index]
        centers = [centers[i] for theta, i in theta_index]
        min_err = float('inf')
        right_angle_index = 0
        for t1 in range(len(contours)):
            t2 = (t1 + 1) % len(contours)
            t3 = (t2 + 1) % len(contours)
            diff = abs(getSquareDist(centers[t1], centers[t2])
                + getSquareDist(centers[t1], centers[t3])
                - getSquareDist(centers[t2], centers[t3]))
            if min_err > diff:
                min_err = diff
                right_angle_index = t1
        t = [i % len(contours) for i in range(right_angle_index, right_angle_index+len(contours))]

        contours = [contours[i] for i in t]

        centers = [getPixelListCenter(c) for c in contours]
        return contours

    image_edge = cv2.Canny(gray_image, 100, 200)
    kernel = np.ones((3,3),np.uint8)
    image_edge = cv2.dilate(image_edge, kernel, iterations=1)
    _, contours, hierarchy = cv2.findContours(image_edge.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)


    contours_depth = getContourDepth(hierarchy[0])


    valid_index = filter(lambda x: contours_depth[x] == 6, range(len(contours)))
    contours = [contours[i] for i in valid_index]

    contours = filter_with_shape(contours)


    # print("number of contour before filter of positions: {}".format(len(contours)))

    # Find best triplet which can form a right triangle
    if len(contours) > 3:
        contours = filter_with_positions(contours)

    contours = rearrange_contours(contours)
    return contours

#timeit
def adjustOrientation(binary_image, original_image, save_path=None):
    '''
    given an answer sheet, return an copy which is rotated to the correct orientation,
    contours of three corner blocks and four corner positions in (col, row) tuple
    '''
    #timeit
    def rotateCoordinate(x, y, w, h, degree, paper_orientation_changed=False):
        _x, _y = x - w // 2, h // 2 - y
        angle = degree / 180 * np.pi
        # print ("_x:{}, _y:{}, angle:{}".format(_x, _y, angle))
        if not paper_orientation_changed:
            r_x = int(_x * np.cos(angle) - _y * np.sin(angle)) + w // 2
            r_y = h // 2 - int(_y * np.cos(angle) + _x * np.sin(angle))
        else:
            r_x = int(_x * np.cos(angle) - _y * np.sin(angle)) + h // 2
            r_y = w // 2 - int(_y * np.cos(angle) + _x * np.sin(angle))

        return (r_x, r_y)

    #timeit
    def rotateContour(contour, w, h, degree, paper_orientation_changed=False):
        # print ("before:{}".format(contour[:10]))

        # print ("contour: {}".format(contour))

        # weird storage format
        result = np.array([[list(rotateCoordinate(c[0][0], c[0][1], w, h, degree, paper_orientation_changed))] \
            for c in contour])
        # result = np.array(list(map(lambda c: [list(rotateCoordinate)], contour)))

        # print ("after:{}".format(result[:10]))
        return result


    def getAdjustDegree(centers):
        x = [int(c[0]) for c in centers]
        y = [int(c[1]) for c in centers]
        d1 = np.arctan2(y[0]-y[1], x[1]-x[0]) + np.pi / 2
        d2 = np.arctan2(y[0]-y[3], x[3]-x[0])
        # print ("d1: {}, d2: {}, Adjust Degree: {}".format(d1, d2, (d1 + d2) / 2 / np.pi * 180))
        return -(d1 + d2) / 2 / np.pi * 180



    contours = getQRCornerContours(binary_image)
    centers = list(map(lambda c: getPixelListCenter(c), contours))

    # append the 4th corner according to the other 3
    centers.insert(2, getLastCorner(centers))
    # print ("centers: {}".format(centers))



    h, w = binary_image.shape
    x, y = centers[0][0] - w//2, h//2 - centers[0][1]

    # print ("orientation test: x={}, y={}".format(x, y))

    degree = 0
    paper_orientation_changed = False # landscape <-> portrait
    if x > 0 and y > 0:
        degree = 90
        paper_orientation_changed = True
    elif x > 0 and y < 0:
        degree = 180
    elif x < 0 and y < 0:
        degree = 270
        paper_orientation_changed = True

    # slightly adjust orientation, making the edges vertical and horizontal
    if degree:
        centers = [rotateCoordinate(x, y, w, h, degree, paper_orientation_changed) for x, y in centers]
        binary_image = rotateImage(binary_image, degree)
        original_image = rotateImage(original_image, degree)
        # contours = [rotateContour(contour, w, h, degree, paper_orientation_changed) for contour in contours]
    # print ("rotate degree: {}, centers: {}".format(degree, centers))
    # cv2.imshow('xx', gray_image)
    # cv2.waitKey(0)

    delta_degree = getAdjustDegree(centers)



    if delta_degree:
        binary_image = rotateImage(binary_image, delta_degree, expand=False)
        original_image = rotateImage(original_image, delta_degree, expand=False)
        centers = [rotateCoordinate(x, y, w, h, delta_degree) for x, y in centers]
        # contours = [rotateContour(contour, w, h, delta_degree) for contour in contours]

    # Expand should be false, otherwise, we should shift centers a bit


    ######################################
    #  TODO: Affine Transform if needed  #
    ######################################


    # After rotation, the image is no longer binary image
    # thus, we need to do it again
    _, binary_image = cv2.threshold(binary_image, 0, 255,
                                    cv2.THRESH_BINARY + cv2.THRESH_OTSU)


    # return gray_image, contours, centers
    return binary_image, original_image, centers,

def _separateGrides(stripe):
    '''
    given a stripe on image, calculate the position of gridlines
    corner block should not be included
    '''

    # if it's vertical stripe, transpose it to horizontal
    if stripe.shape[0] > stripe.shape[1]:
        stripe = stripe.transpose()
    h, w = stripe.shape

    bw_line = (np.sum(stripe > 128, axis=0)) > (h // 2)

    #### Smooth
    # t = 0
    # while bw_line[t] == True:
    #     bw_line[t] = False
    #     t += 1
    for i in range(1, w-1):
        if bw_line[i] != bw_line[i+1] and bw_line[i] != bw_line[i-1] and bw_line[i-1] == bw_line[i+1]:
            bw_line[i] = bw_line[i-1]
    ### Smooth

    cur_state = bw_line[0]
    result = list()
    for i in range(1, w):
        if cur_state != bw_line[i]:
            cur_state = bw_line[i]
            result.append(i)

    return result

def getGridlinePositions(binary_image, contours, centers):
    '''
    calculate the horizontal and vertical gridline positions
    '''
    # print (len(contours))
    bounding_rects = list(map(cv2.boundingRect, contours))
    # print ("bounding rects: {}".format(bounding_rects))
    x, y, w, h = bounding_rects[1]
    # print (x, y, w, h, centers)
    stripe = binary_image[y + int(0.3*h) : y + int(0.7*h), x+w : centers[2][0]]
    # print ("stripe.shape:{}".format(stripe.shape))
    vertical = list(map(lambda c: c+x+w, _separateGrides(stripe)))

    # x1, y1, w1, h1 = bounding_rects[0]
    # x2, y2, w2, h2 = bounding_rects[1]

    # considering the topleft, bottomleft corners have block,
    # we use right and bottom lines to locate grids
    # so that there's no conflict between corner block and black grids

    x1, y1, w1, h1 = bounding_rects[2]
    x2, y2, w2, h2 = x1, y, w, h # use approximates here.
    stripe = binary_image[y1+h1: y2-1, x1+int(0.15*(w1+w2)) : x1+int(0.35*(w1+w2))]
    horizontal = list(map(lambda r: r+y1+h1, _separateGrides(stripe)))
    # print ("stripe.shape:{}".format(stripe.shape))
    # print ("horizontal:{}\nvertical:{}".format(horizontal, vertical))
    return horizontal, vertical

# count = 0
def getBlackRatio(grid, padding_ratio = 0.2):
    '''
    return the ratio of black pixels
    Track only 36% (60% * 60%) area in the center
    '''
    h, w = grid.shape
    dh, dw = int(h * padding_ratio), int(w * padding_ratio)
    grid = grid[dh:h-dh, dw:w-dw]
    # global count
    # cv2.imwrite("tmp/{}_{}.jpg".format(count, np.sum((grid>128).flatten()) / grid.size), grid)
    # count += 1
    return np.sum((grid>128).flatten()) / grid.size

def extractGrids(binary_image, horizontal_pos, vertical_pos, r, c, h, w):
    '''
    given a binary image, return the rectangular area of grids in
    from ROW_r -> ROW_{r+h}, COLUMN_c -> COLUMN_{c+w}
    '''
    y1, y2 = horizontal_pos[r], horizontal_pos[r + h]
    x1, x2 = vertical_pos[c], vertical_pos[c + w]
    return binary_image[y1:y2, x1:x2]

def getRatioFromStripe(stripe, num_choice, multiple=False):
    '''
    given stripe, and number of choice, return the black pixel ratio sequence
    of the stripe
    '''
    if stripe.shape[0] > stripe.shape[1]:
        stripe = stripe.transpose()
    h, w = stripe.shape
    grid_len = w // num_choice
    result = list()

    for i in range(num_choice):
        grid = stripe[:, i*grid_len : (i+1)*grid_len]
        result.append(getBlackRatio(grid))
    return result

def getDigitFromSequence(sequence, T=0.5):
    '''
    given sequence array, return argmax(sequence) if a value
    larger than threshold T exists
    '''
    return str(np.argmax(sequence)) if np.max(sequence) > T else "-"

def getAnswerFromSequence(sequence, T=0.5):
    '''
    given sequence array, return all index i's which ratio_i's are
    larger than threshold T
    '''
    # print (max(sequence), min(sequence), sequence)
    Choices = "ABCDEFGHIJK"
    result = "".join([Choices[i] for i in range(len(sequence)) if sequence[i] > T])
    return result if result else "-"
