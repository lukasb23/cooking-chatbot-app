#Imports
from flask import Flask, request
from fbmessenger import BaseMessenger
from fbmessenger.templates import GenericTemplate
from fbmessenger.elements import Text, Button, Element
from fbmessenger import quick_replies
from fbmessenger.thread_settings import (
    GreetingText,
    GetStartedButton,
    PersistentMenuItem,
    PersistentMenu,
    MessengerProfile
)

import random
import json
from flask import current_app as app

#Modules
from .md_dialogflow import detect_intent_texts
from .md_elasticsearch import Elastic


#Responses
with open("data/responses.json", "r") as f:
    responses = json.load(f)

#Helpers
def process_quick_rpls(quick_rpls):

    """Takes n number of quick_replies and returns them processed"""

    q_rpls_list = []
    for q_r in quick_rpls:
        q_rpls_list.append(quick_replies.QuickReply(title=q_r, payload=q_r))
    return quick_replies.QuickReplies(quick_replies=q_rpls_list)


def get_recipe_button(ratio, url):
    return Button(
        button_type='web_url',
        title='Open in Browser',
        url=url,
        webview_height_ratio=ratio,
    )

def get_ingredient_button(index):
    return Button(
        button_type='postback',
        title='Show ingredients',
        payload='SHOW_INGREDIENT_{}'.format(index)
    )

def get_nutrient_button(index):
    return Button(
        button_type='postback',
        title='Show nutrients',
        payload='SHOW_NUTRIENT_{}'.format(index)
    )


def get_recipe_hits(elastic_hits):
    
    """Takes elastic_hits and returns webview elements"""
    
    elements = []
    for i,hit in enumerate(elastic_hits):
        btn1 = get_ingredient_button(i)
        btn2 = get_nutrient_button(i)
        btn3 = get_recipe_button('full', hit['url'])
        elements.append(Element(
            title=hit['title'],
            item_url=hit['url'],
            image_url=hit['image_url'],
            subtitle=hit['subtitle'],
            buttons=[btn1, btn2, btn3]
        ))
    
    return elements

 
def display_recipe_hits(elastic_hits):
     
    """Displays hits in form of generic templates"""
    
    elements = get_recipe_hits(elastic_hits)
    qrs = process_quick_rpls(['Edit search', 'Load more'])
    return GenericTemplate(elements=elements, quick_replies=qrs)
    
    

class Messenger(BaseMessenger):
    
    def __init__(self, page_access_token):
        self.page_access_token = page_access_token
        super(Messenger, self).__init__(self.page_access_token)

    def message(self, message):
        response, callback = self.process_message(message)
        if callback:
            response_info = self.generate_info_message()
            res = self.send(response_info, 'RESPONSE')
            res = self.send(response, 'RESPONSE')
        else:
            res = self.send(response, 'RESPONSE')
        app.logger.info('Response: {}'.format(res))

    def delivery(self, message):
        pass

    def read(self, message):
        pass

    def account_linking(self, message):
        pass

    def optin(self, message):
        pass
    
    def postback(self, message):
        user_id = message['sender']['id']
        payload = message['postback']['payload']
        
        if "WELCOME" in payload:
            text = responses["welcome"][0]
            self.handle_response(text)
            text = responses["welcome"][1]
            self.handle_response(text, ["Guided search", "Custom search", "More info"])
            
        if "RESTART" in payload:
            restart_msg = {'sender': {'id': message['sender']['id']},
                           'message': {'text':  message['postback']['title']}}
            self.message(restart_msg)
            
        if 'SHOW_INGREDIENT' in payload:
            self.send_recipe_details(user_id, payload, "ingredients")
        
        if 'SHOW_NUTRIENT' in payload:
            self.send_recipe_details(user_id, payload, "nutrients")
        

    def init_bot(self):
        
        """Handles greeting procedure and persistent menu"""
        
        greet_txt = responses["greet"]
        greeting_text = GreetingText(greet_txt)
        get_started = GetStartedButton(payload='WELCOME')
        
        menu_item = PersistentMenuItem(item_type='postback', title='Restart recipe search', payload='RESTART')
        menu = PersistentMenu(menu_items=[menu_item])

        messenger_profile = MessengerProfile(persistent_menus=[menu],
                                             get_started=get_started,
                                             greetings=[greeting_text])
        res = self.set_messenger_profile(messenger_profile.to_dict())
        app.logger.info('Response: {}'.format(res))
        
        
        
    def process_message(self, message):
    
        """Handles message processing on the part of facebook"""
        
        app.logger.info('Message received: {}'.format(message))
        
        user_id = message['sender']['id']
        callback = False
        
        if "message" in message:
            if 'attachments' in message['message']:
                print('entered')
                response = Text(text="Apologies, but I'm only able to understand text input!")
                return (response.to_dict(), callback)
            elif 'text' in message['message']:
                message_text = message['message']['text']
        
        elif "postback" in message:
            return self.postback(message)
        
        #run logic
        text, quick_rpls, elastic_hits = detect_intent_texts(user_id, message_text)
        
        if quick_rpls is None and elastic_hits is None:
            response = Text(text=text)
        
        elif elastic_hits is None:
            qrs = process_quick_rpls(quick_rpls)
            response = Text(text=text, quick_replies=qrs)
            
        elif elastic_hits and text is None:
            response = display_recipe_hits(elastic_hits)
        
        elif elastic_hits and text:
            response = display_recipe_hits(elastic_hits)
            callback = True
            
        return (response.to_dict(), callback)
    
    
    def generate_info_message(self):
        
        response = Text(text=random.choice(responses["no-exact-match"]))
        return response.to_dict()
        
    
    def send_recipe_details(self, user_id, payload, kind):
        
        """Communicates with ES to send recipe details"""
        
        text = Elastic().send_recipe_details(user_id, payload, kind)
        if text:
            self.handle_response(text, ["Edit search", "Show current", "Load more"])
        else:
            text = "Apologies, but your search is expired. Let's restart! :)"
            self.handle_response(text, ["Restart"])
    
    
    def handle_response(self, text, qrs_list=None):
        
        """Handles generic response sending"""
        
        if qrs_list:
            qrs = process_quick_rpls(qrs_list)
            response = Text(text=text, quick_replies=qrs).to_dict()
        else:
            response = Text(text=text).to_dict()
        res = self.send(response, 'RESPONSE')
        app.logger.info('Response: {}'.format(res))
        
