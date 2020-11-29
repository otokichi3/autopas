FROM python:3.8-alpine3.10

# update apk repo
RUN echo "http://dl-4.alpinelinux.org/alpine/v3.10/main" >> /etc/apk/repositories && \
    echo "http://dl-4.alpinelinux.org/alpine/v3.10/community" >> /etc/apk/repositories

# install chromedriver
RUN apk update
RUN apk add chromium chromium-chromedriver
RUN apk add locales
RUN echo "Japanese_Japan 932" > /etc/locale.gen

# upgrade pip
RUN pip install --upgrade pip

# install selenium
RUN pip install selenium
RUN pip install flask
RUN pip install beautifulsoup4
RUN pip install python-dateutil
RUN pip install flask_cors
RUN pip install requests