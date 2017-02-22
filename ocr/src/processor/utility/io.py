import cv2
import os
from .common import generateFileName

def save_file(binary_image):
    dir_name = "/var/tmp/"
    file_name = generateFileName()
    save_path = os.path.join(dir_name, file_name)
    cv2.save(save_path)
    return save_path