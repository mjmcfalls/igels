FROM python:3.8-slim
WORKDIR /app/src
WORKDIR /app
COPY ./compareImages.py /app
COPY src/BrokenScreen.png /app/src
COPY src/WorkingScreen_202005110830.png /app/src
COPY requirements.txt /app
RUN apt-get update && apt-get install -y libglib2.0-0 imagemagick && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt
CMD ["python", "compareImages.py"]