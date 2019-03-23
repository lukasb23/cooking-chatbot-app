#Imports
import os
import json
import pickle
from flask import Flask, request

#Modules
from modules.md_dialog_logic import Search
from modules.md_messenger import Messenger

app = Flask(__name__)

#Facebook
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
FB_VERIFY_TOKEN = os.getenv('FB_VERIFY_TOKEN')
messenger = Messenger(FB_ACCESS_TOKEN)

#Flask
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

#Main endpoint
@app.route("/", methods=['GET', 'POST'])
def receive_message():
    
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == FB_VERIFY_TOKEN:
            messenger.init_bot()
            return request.args.get('hub.challenge')
        raise ValueError('FB_VERIFY_TOKEN does not match.')
    
    elif request.method == 'POST':
        messenger.handle(request.get_json(force=True))
        
    return ''
    

if __name__ == "__main__":
    app.run()
