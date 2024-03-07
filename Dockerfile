FROM python:3.8-alpine3.10

# update apk repo
RUN echo "http://dl-4.alpinelinux.org/alpine/v3.10/main" >> /etc/apk/repositories && \
    echo "http://dl-4.alpinelinux.org/alpine/v3.10/community" >> /etc/apk/repositories

# install chromedriver
RUN apk update
RUN apk add --no-cache gcc libc-dev libffi-dev
RUN apk add --no-cache chromium chromium-chromedriver

# upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt to the docker image and install packages
COPY requirements.txt /
RUN pip install -r requirements.txt

# Copy all files
COPY . /app

# Set env
ENV opas_id 9999999
ENV opas_password hogehoge
ENV line_token foo
ENV line_token_test bar
ENV captcha_key fuga

# Set the WORKDIR to be the folder
WORKDIR /app
CMD ["python", "main.py"]
