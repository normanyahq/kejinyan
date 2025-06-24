FROM kejinyan/kejinyan:hechi

COPY simple_web /data/
COPY ./entrypoint.sh /entrypoint.sh
ENTRYPOINT [ "bash", "/entrypoint.sh" ]
