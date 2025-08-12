FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip
RUN pip install pip pipenv && pip install --upgrade pip pipenv==2023.6.26

COPY ./Pipfile ./
COPY ./Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .

CMD ["python", "app.py"]
