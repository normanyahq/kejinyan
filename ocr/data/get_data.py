#!/usr/local/bin/python3

import requests

files = [("QR_2B_Answersheet.pdf", "https://dn-coding-net-production-file.qbox.me/98da9fc9-00e0-490d-9b2c-7f7d743041c2.pdf?download/QR_2b_answersheet.pdf&e=1487407451&token=goE9CtaiT5YaIP6ZQ1nAafd_C1Z_H2gVP8AwuC-5:nk16_FncNGhDgLg3tXh0CCXt1qQ=")]


for i, (name, url) in enumerate(files):
    with open (name, 'wb') as f:
        print ("Downloading {} / {}: {}".format(i+1, len(files), name))
        f.write(requests.get(url).content)
