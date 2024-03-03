import time
from redis import Redis
from rq import Queue

# Instantiate a Redis connection and a queue
redis_conn = Redis()
q = Queue(connection=redis_conn)

# Define a job function
def example_task():
    print(f"Task started")
    time.sleep(2000)
    print(f"Task completed")
    return n

# Enqueue the job
if __name__ == "__main__":
    from tasks import example_task
    job = q.enqueue(example_task, 5)