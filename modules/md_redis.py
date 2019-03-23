#Imports
import redis
import pickle
import os

#Connection
redis_host = os.environ.get('REDIS_HOST', 'localhost')
r = redis.StrictRedis(host=redis_host, port=6379)


#Set/Get/Del
def redis_set(key, obj):
    pickled_object = pickle.dumps(obj)
    r.set(key, pickled_object)
    r.expire(key, 1800) #expire after 30min
    print("Set key for user {}".format(key))

def redis_get(key):
    res = r.get(key)
    if res is None:
        return None
    else:
        print("Loaded key for user {}".format(key))
        return pickle.loads(res)

def redis_delete(key):
    r.delete(key)
    print("Delete key for user {}".format(key))