#!/bin/bash
mkdir -p ./data/postgres
mkdir -p /data/file_storage
sudo -u postgres \
    nohup /usr/lib/postgresql/14/bin/postgres  \
    -D ./data/postgres \
    -c config_file=/etc/postgresql/14/main/postgresql.conf &
while ! sudo -u postgres psql -c 'create database kejinyan'; do sleep 1; done
sudo -u postgres psql -c 'create user kejinyan'
sudo -u postgres psql -c "alter user kejinyan password 'kejinyan'"
python3 -c "import server; server.init()"

gunicorn -w 4 server:app -b :8000 2>&1 > service.log &

while ! curl localhost:8000/; do sleep 1; done

curl -XPOST \
    -F token=00000000000000AAAAAAAAAA \
    -F standard=@/data/static/half_standard.pdf \
    localhost:8000/upload/
curl -XPOST \
    -F token=00000000000000AAAAAAAAAA \
    -F answers=@/data/static/half_example.pdf \
    localhost:8000/upload/
curl -XPOST \
    -F answersheettype=half \
    -F note=example \
    -F token=00000000000000AAAAAAAAAA \
    -F judgeMode=exact \
    localhost:8000/

echo "service is started"

tail -F service.log