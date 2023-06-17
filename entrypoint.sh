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
gunicorn -w 4 server:app -b :8000
# python3 server.py