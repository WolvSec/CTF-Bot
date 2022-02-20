FROM python:3-alpine

LABEL org.opencontainers.image.source https://github.com/WolvSec/CTF-Bot

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "-m", "ctfbot" ]
