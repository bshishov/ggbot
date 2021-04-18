FROM python:3.9.4-alpine

MAINTAINER Boris Shishov <borisshishov@gmail.com>

WORKDIR /app

ADD . /app

RUN python -m pip install --trusted-host pypi.python.org -r requirements.txt

CMD python src/ggbot/__main__.py app.toml