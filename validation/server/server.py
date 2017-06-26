from flask import Flask, request
import json
import random
import subprocess
import string
import os
import sqlite3
import traceback
import time
app = Flask(__name__)

privateKeyPath = './key.pem'
tempDirectory = '/tmp/'


def getDb():
    conn = sqlite3.connect('validate.db')
    return conn


def init():
    try:
        commands = ['''
                        CREATE TABLE tokenInfo
                            (token TEXT PRIMARY KEY, valid INTEGER);
                    ''',
                    '''
                        CREATE TABLE accessHistory
                            (token TEXT, accessTime REAL);
                    ''']
        conn = getDb()
        c = conn.cursor()
        for command in commands:
            c.execute(command)
        conn.commit()
        conn.close()
    except:
        pass


def getDecryptedStringOfFile(encryptedFilePath):
    command = 'openssl rsautl -decrypt -inkey {} -in {} -out {}.decrypted'\
        .format(privateKeyPath,
                encryptedFilePath,
                encryptedFilePath) \
        .split()
    subprocess.call(command)
    return open(encryptedFilePath + ".decrypted").read()


def getRandomString(size=10, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def isValidToken(token):
    conn = getDb()
    c = conn.cursor()
    c.execute("SELECT * FROM tokenInfo WHERE token = ?;", (token, ))
    t = c.fetchone()
    return (t and len(t) == 2 and t[1] > 0)


def insertAccessHistory(token):
    conn = getDb()
    c = conn.cursor()
    c.execute("INSERT INTO accessHistory VALUES (?, ?);", (token, time.time()))
    t = c.fetchone()
    conn.commit()


@app.route("/validate", methods=["POST"])
def validate():
    result = {"valid": False,
              "salt": getRandomString()}

    filename = getRandomString()
    filepath = os.path.join(tempDirectory, filename)

    try:
        request.files['message'].save('{}'.format(filepath))
        decryptedString = getDecryptedStringOfFile(filepath)
        info = json.loads(decryptedString)
        # salt is used to make encrypted result different
        salt = info['salt']

        if isValidToken(info['token']):  # if token is valid
            result = {"valid": True,
                      "salt": salt,
                      "seed": getRandomString()}
            insertAccessHistory(info['token'])

    except:
        traceback.print_exc()

    return json.dumps(result)

if __name__ == '__main__':
    init()
    app.run(host="0.0.0.0", debug=True, port=8848)
