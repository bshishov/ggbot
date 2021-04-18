FROM python:3.9.4-buster

MAINTAINER Boris Shishov <borisshishov@gmail.com>

WORKDIR /app

ADD . /app

ENV PYTHONPATH=/app/src

RUN python -m pip install --trusted-host pypi.python.org -r requirements.txt

CMD python src/ggbot/__main__.py app.toml