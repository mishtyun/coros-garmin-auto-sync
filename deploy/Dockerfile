FROM python:3.13.6-alpine3.21

WORKDIR /app

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
RUN python -m pip install --upgrade pip
RUN pip install pip pipenv && pip install --upgrade pip pipenv==2023.6.26

COPY ./Pipfile ./
COPY ./Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .

CMD python app.py
