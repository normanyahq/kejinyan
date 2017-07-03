from psycopg2 import connect
import os
import traceback
import json
import string
import random
import time

publicKeyPath = './pub.pem'
# validationUrlFilePath = '/tmp/validationUrl'
# tokenFile = '/tmp/validationRegistrationToken'
defaultValidationUrl = 'http://localhost:8848/validate'
requestInterval = 1
maxFailureTime = 6


def getDb():
    db = connect(database='kejinyan', host='localhost',
                 user='kejinyan', password='kejinyan')
    return db


def getRandomString(size=10, chars=string.ascii_uppercase + string.digits):
    # https://docs.python.org/2/library/random.html#random.SystemRandom
    # this is a must to reset the random seed
    # otherwise the random number is always the same
    random.seed(os.urandom(10))
    return ''.join(random.choice(chars) for _ in range(size))


def generateEncryptFile(message):
    filename = getRandomString()
    encryptedFilePath = os.path.join('/tmp/', filename)
    with open(encryptedFilePath, "w") as f:
        json.dump(message, f)

    encryptionCommandTemplate = '''openssl rsautl -encrypt -inkey pub.pem -pubin -in {} -out {}.enc'''
    encryptionCommand = encryptionCommandTemplate.format(encryptedFilePath,
                                                         encryptedFilePath)
    os.system(encryptionCommand)
    return encryptedFilePath + '.enc'


def postEncryptedFile(messageFilePath):
    validationUrl = getConfig('validationUrl')
    commandTemplate = '''curl -X POST -H "Content-Type: multipart/form-data"  -F "message=@{}" {}'''
    command = commandTemplate.format(messageFilePath, validationUrl)
    result = os.popen(command).read()
    return result


def validate():
    token = 'iloveyou'
    try:
        # token = open(tokenFile).read()
        token = getConfig('registrationCode')
    except:
        traceback.print_exc()
    message = {'salt': getRandomString(),
               'token': token}
    encryptedFilePath = generateEncryptFile(message)

    try:
        response = postEncryptedFile(encryptedFilePath)
        print response
        response = json.loads(response)
        if response.get('salt', '') == message['salt'] and response.get('valid'):
            return True
    except:
        traceback.print_exc()
    return False


def init():
    # os.system('echo {} > {}'.format(defaultValidationUrl,
    #                                 validationUrlFilePath))
    executeUpdate("update globalConfig set value = '{}' where key = 'validationUrl';".format(
        defaultValidationUrl))


def executeUpdate(command):
    db = getDb()
    c = db.cursor()
    c.execute(command)
    db.commit()
    db.close()


def getConfig(key):
    try:
        db = getDb()
        c = db.cursor()
        c.execute("select value from globalConfig where key = %s;", (key, ))
        t = c.fetchone()[0]
        db.close()
        return t
    except:
        traceback.print_exc()
    return ''


def setConfig(key, value):
    command = "update globalConfig set value = %s where key = %s;"
    db = getDb()
    c = db.cursor()
    c.execute(command, (value, key))
    db.commit()
    db.close()


def main():
    init()
    failedCounter = 0
    while True:
        if validate():
            executeUpdate(
                "update globalConfig set value = 'true' where key = 'valid';")
            failedCounter = 0
        else:
            failedCounter += 1
            if failedCounter > maxFailureTime:
                executeUpdate(
                    "update globalConfig set value = 'false' where key = 'valid';")

        time.sleep(requestInterval)

if __name__ == "__main__":
    main()
