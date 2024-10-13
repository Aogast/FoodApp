FROM python:3.11-slim

WORKDIR /FoodApp

COPY . /FoodApp

RUN pip install --no-cache-dir -r requirements.txt


CMD ["flask", "run", "--host=0.0.0.0"]
