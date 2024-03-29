import random
import datetime
import string
import time

def getSquareDist(p1, p2):
    return (int(p1[0])-int(p2[0])) ** 2 + (int(p1[1])-int(p2[1]))**2


def generateFileName():
    return getToken() + ".png"


def getToken():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S") \
        + "".join([random.choice(string.uppercase + string.lowercase + string.digits)
                   for i in range(0, 10)])


def timeit(f):
    def timed(*args, **kw):

        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        print 'func:%r took: %2.4f sec' % \
          (f.__name__, te-ts)
        return result

    return timed
