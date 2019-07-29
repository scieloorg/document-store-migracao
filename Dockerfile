FROM python:3.7-alpine

 COPY . /app
RUN apk add --no-cache --virtual .build-deps \
        make gcc libxml2-dev libxslt-dev musl-dev g++ git openjdk8 \
    && apk add libxml2 libxslt \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install -e /app

 WORKDIR /app
ENV PYTHONUNBUFFERED 1

 RUN chown -R nobody:nogroup /app
USER nobody

 CMD ["/bin/sh"]  