import os

import redis
from rq import Worker, Queue, Connection


listen = ['default']

#redis_url = redis.Redis(host='redis', port=6379, decode_responses=True)
#redis_url = os.getenv('REDISTOGO_URL', 'redis://172.17.0.1:6379')
redis_url = os.getenv('REDISTOGO_URL', 'redis://127.0.0.1:6379')
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()