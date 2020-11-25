FROM python:3.9-alpine3.12

WORKDIR /app
COPY ./gym_booker.py /app

# update apk repo
RUN echo "http://dl-4.alpinelinux.org/alpine/v3.10/main" >> /etc/apk/repositories && \
    echo "http://dl-4.alpinelinux.org/alpine/v3.10/community" >> /etc/apk/repositories

# install chromedriver
RUN apk update
RUN apk add chromium chromium-chromedriver

# upgrade pip
RUN pip install --upgrade pip

# install selenium
RUN pip install selenium

CMD ["python", "gym_booker.py"]