FROM python:3.9
WORKDIR ./inward
COPY . ./inward
RUN pip install -r ./inward/requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
EXPOSE 5000
CMD ["python3", "./inward/main.py"]