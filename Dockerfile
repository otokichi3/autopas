FROM python:3.8-alpine3.10

# update apk repo
RUN echo "http://dl-4.alpinelinux.org/alpine/v3.10/main" >> /etc/apk/repositories && \
    echo "http://dl-4.alpinelinux.org/alpine/v3.10/community" >> /etc/apk/repositories

# install chromedriver
RUN apk update
RUN apk add chromium chromium-chromedriver

# upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt to the docker image and install packages
COPY requirements.txt /
RUN pip install -r requirements.txt

# Copy all files
COPY . /app

# Set env
ENV opas_id 27041850
ENV opas_password OPASyskt1829
ENV line_token hM4JwG7IXMwJlHtNc5sD3G9HRYRYyd5CsNujbpncq3W

# Set the WORKDIR to be the folder
WORKDIR /app
CMD ["python", "main.py"]
