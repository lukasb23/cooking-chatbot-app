#Imports
import redis
import pickle
import os
import json

#Connection
with open("config/keys.json") as f:
    redis_host = json.load(f)['REDIS_HOST']
r = redis.StrictRedis(host=redis_host, port=6379)


#Set/Get/Del
def redis_set(key, obj):
    pickled_object = pickle.dumps(obj)
    r.set(key, pickled_object)
    r.expire(key, 1800) #expire after 30mins

def redis_get(key):
    res = r.get(key)
    if res is None:
        return None
    else:
        return pickle.loads(res)

def redis_delete(key):
    r.delete(key)
