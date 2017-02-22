import random
import datetime
import string

def getSquareDist(p1, p2):
    return (int(p1[0])-int(p2[0])) ** 2 + (int(p1[1])-int(p2[1]))**2


def generateFileName():
    return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_") \
        + "".join([random.choice(string.uppercase + string.lowercase + string.digits)
                   for i in range(0, 5)]) + ".jpg"