#Imports
import json
import dialogflow
from google.api_core.exceptions import InvalidArgument
from google.oauth2.service_account import Credentials

#Modules
from .md_dialog_logic import Search

#Dialogflow parameter
with open("config/keys.json") as f:
    project_id = json.load(f)['DIALOGFLOW_PROJECT_ID']

dialogflow_config_path = 'config/cooking-chatbot-f88b6ceeeb5e.json'
credentials = Credentials.from_service_account_file(dialogflow_config_path)
language_code = 'en'


def detect_intent_texts(user_id, text):
    
    """Handles Dialogflow's intent detection and response generation"""
    
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session_dialogflow = session_client.session_path(project_id, user_id)

    text_input = dialogflow.types.TextInput(
        text=text, language_code=language_code
    )
    query_input = dialogflow.types.QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(
            session=session_dialogflow, query_input=query_input
        )
    except InvalidArgument:
        return ("I'm sorry, but your message was too long for me to handle,\
                please stick to a maximum of 256 characters.", None, None)

    intent = response.query_result.intent.display_name
    fields = response.query_result.parameters.fields

    #let Dialogflow handle all non-related queries
    print('INTENT', intent)
    if intent == "default-welcome-intent":
        return (response.query_result.fulfillment_text,
                ["Guided search", "Custom search", "More info"], None)

    elif not intent.startswith("search"):
        return (response.query_result.fulfillment_text, None, None)

    #custom logic
    else:
        return Search(text,user_id,intent,fields).logic()
