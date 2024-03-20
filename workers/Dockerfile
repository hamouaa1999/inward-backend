FROM python:3.9
WORKDIR ./workers
COPY . ./workers
RUN pip install redis
RUN pip install rq
CMD ["python3", "./workers/worker.py"]