import cv2
import os
from .common import generateFileName


def saveToDir(binary_image, dir_name="/var/tmp/"):
    file_name = generateFileName()
    save_path = os.path.join(dir_name, file_name)
    cv2.imwrite(save_path, binary_image)
    return save_path
