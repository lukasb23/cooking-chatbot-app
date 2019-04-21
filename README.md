# cooking-chatbot-app

Building a Cooking Chatbot to search through >35.000 recipes from Epicurious, brief YouTube demo below:

[![EpiBot Demo](https://img.youtube.com/vi/zcZn3eAQzoI/0.jpg)](https://www.youtube.com/watch?v=zcZn3eAQzoI)


#### Key points:
- \>35k recipes extracted from epicurious.com
- Flask application communicating with:
  - Facebook Messenger over the [*fbmessenger*](https://github.com/rehabstudio/fbmessenger) library
  - Google Dialogflow API (chatbot platform) via Python's [*dialogflow*](https://dialogflow-python-client-v2.readthedocs.io/en/latest/) library
  - Elasticsearch as recipe store and search engine via [*elasticsearch-py*](https://elasticsearch-py.readthedocs.io/en/master/)
  - Redis for temporarily storing dialogue elements via [*redis-py*](https://redis-py.readthedocs.io/en/latest/)
- Hosted on Google Cloud Platform
  - Google App Engine Flex for running the flask app
  - Bitnami Elasticsearch-Cluster on Google Compute Engine
  - Google Cloud Memorystore for Redis

The project is/was running on Facebook Messenger under [EpiBot - Find your Recipe](https://www.facebook.com/find.your.recipe.1/?modal=admin_todo_tour) (most of the time offline though, I'm still just a poor student ;-) ).

#### Repo:
This repo is the actual app hosted on Google Cloud. The steps to crawl the data and prepare them for Elasticsearch are found under [*cooking-chatbot-data-generation*](https://github.com/lukasb23/cooking-chatbot-data-generation).

#### To test locally:

- Start Redis
  - cd Programs/redis-5.0.3/src
  - ./redis-server
- Start Elasticsearch
  - cd Programs/elasticsearch-6.6.1/
  - ./bin/elasticsearch
- Setup Ngrok
  - cd Programs/
  - ./ngrok http 127.0.0.1:5000
- Flask
  - export commands & activate Flask environment "chatbot-env"
    - export LC_ALL=C.UTF-8
    - export LANG=C.UTF-8
    - source chatbot-env/bin/activate
  - flask run
- Edit Messenger Subscription with current tunnel
  - https://developers.facebook.com/apps/[your_app]/webhooks/
  
#### Disclaimer:

This project is for research purposes only.
