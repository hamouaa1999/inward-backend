FROM python:3.9
WORKDIR ./inward
COPY . ./inward
RUN pip freeze > requirements.txt
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python3", "main.py"]