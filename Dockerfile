FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt requirements.txt
COPY . /app
RUN pip install --upgrade setuptools
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]