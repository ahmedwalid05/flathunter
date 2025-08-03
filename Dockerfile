FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ARG PIP_NO_CACHE_DIR=1

# Install Chromium
RUN apt-get -y update
RUN apt-get install -y chromium

# Upgrade pip and install pipenv
RUN pip install --upgrade pip
RUN pip install pipenv

WORKDIR /usr/src/app

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install dependencies using pipenv
RUN pipenv install --system --deploy --ignore-pipfile

# Copy all other files, including source files
COPY . .
