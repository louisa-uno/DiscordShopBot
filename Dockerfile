FROM python:3.8-slim

COPY . /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./discord-shop.py" ]
