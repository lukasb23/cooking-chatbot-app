#Imports
import os
import json
import pickle
import logging
from flask import Flask, request

#Modules
from modules.md_dialog_logic import Search
from modules.md_messenger import Messenger

app = Flask(__name__)

#Keys
with open("config/keys.json") as f: 
    keys = json.load(f)

app.config['SECRET_KEY'] = keys['FLASK_SECRET_KEY']
FB_ACCESS_TOKEN = keys['FB_ACCESS_TOKEN']
FB_VERIFY_TOKEN = keys['FB_VERIFY_TOKEN']
messenger = Messenger(FB_ACCESS_TOKEN)


#Enable gunicorn logging 
if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


#Main endpoint
@app.route("/webhook", methods=['GET', 'POST'])
def receive_message():
    
    if request.method == 'GET':

        token = request.args.get('hub.verify_token')
        if token == FB_VERIFY_TOKEN:
            messenger.init_bot()
            return request.args.get('hub.challenge')
        return 'FB_VERIFY_TOKEN does not match.'

    elif request.method == 'POST':
        messenger.handle(request.get_json(force=True))
        return 'OK'
    return ''


#Errorhandler
@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
