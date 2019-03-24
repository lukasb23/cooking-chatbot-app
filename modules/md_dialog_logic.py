#Imports
import random
import json
from collections import OrderedDict as od

#Modules
from .md_join import join
from .md_redis import redis_get, redis_set, redis_delete
from .md_elasticsearch import Elastic

#Entities
entities = od({"meal": "meals",
               "time": "time",
               "difficulty": "difficulty",
               "cuisine": "cuisine",
               "ingredient": "types and ingredients",
               "special": "special concerns",
               "occasion": "special occasions",
               "technique": "techniques"
})

#Responses
with open("data/responses.json", "r") as f:
    responses = json.load(f)
    

class Search:
    
    def __init__(self, user_text, user_id, intent, fields):
        
        self.user_text = user_text
        self.user_id = user_id
        self.intent = intent
        self.fields = fields
        
    
    def fill_search(self):
        
        self.param_dict, self.changed = self.get_expressed_params(self.fields)
        self.state_dict = self.merge_previous_params()
        
    
    def __repr__(self):
        
        """String representation of current search"""
        
        search = ["\n"]
        for k,v in self.state_dict['search-params'].items():
            if v == [None]:
                search.append("{}: no preferences".format(entities[k].capitalize()))
            elif len(v) != 0:
                search.append("{}: {}".format(entities[k].capitalize(), join(v)))
            
        return "\n".join(search)
        
        
    def get_expressed_params(self, fields):
    
        """Extracts all currently expressed params"""
        
        param_dict = od()
        changed = []
        for entity in entities.keys():
            
            try:
                param_dict[entity] = [value.string_value
                                      for value in fields.get(entity).list_value.values]
            except AttributeError:
                param_dict[entity] = []
                
            if len(param_dict[entity]) > 0:
                changed += [v for v in param_dict[entity]]
        
        return param_dict, changed
            
            

    def merge_previous_params(self):
        
        """Retrieves previously expressed params and merges with current params"""
        
        state_dict = redis_get(self.user_id)
        
        if state_dict:
            #merge with current params, filter None, drop duplicates
            for entity in entities.keys():
                new = list(set(state_dict['search-params'][entity]+self.param_dict[entity]))
                if None in new and len(new) > 1:
                    new = list(filter(None,new))
                state_dict['search-params'][entity] = new
                
        #no user data available
        else:
            state_dict = od()
            state_dict.update({'search-params': self.param_dict})
        
        return state_dict
    
    
    def check_required_entities(self):
        
        """Checks for undefined entities"""
        
        undefined = []
        for entity in entities.keys():
            if len(self.state_dict['search-params'][entity]) == 0:
                undefined.append(entity)
        
        return undefined
    
        
    def respond(self, ext=""):
        
        """Responds to user: prompt for meal, time, difficulty, cuisine, ingredient & special"""
        
        #prompt for next missing entity, defaults to False
        missing_entity = next((s for s in list(entities.keys())[:6] if s in self.undefined),
                              False)
        
        if missing_entity:
           
            #save stage
            self.state_dict["stage"] = missing_entity
            
            #save to redis
            redis_set(self.user_id, self.state_dict)
            
            prompts = responses[missing_entity]
            if self.changed:
                prompt = prompts["text"] if ext == "" else prompts["text"+ext]
            else:
                prompt = prompts["text"+ext]
            
            #no specific order unless "difficulty" or "time"
            if missing_entity in ["difficulty", "time"]:
                labels = prompts["quick-replies"]
            else:
                labels = random.sample(prompts["quick-replies"][1:], 3) + prompts["quick-replies"][:1]
            
            #fix "main" in meal
            prompt_qrpls = ["Main"] + labels[:-1] if missing_entity == "meal" else labels
            prompt_text = random.choice(prompt).format(join(self.changed))
            
            return (prompt_text, prompt_qrpls, None)
            
        #search complete
        else:
            self.state_dict["stage"] = "completed"
            redis_set(self.user_id, self.state_dict)
            return (random.choice(responses["search-complete"]["text"]).format(repr(self)),
                    responses["search-complete"]["quick-replies"], None)


    def check_and_respond(self, ext=""):
        
        """Check required entities and respond"""
        
        self.undefined = self.check_required_entities()
        return self.respond(ext)
    
        
    def search(self):
        
        """Pushes Search"""
        
        #Remove current search results
        self.state_dict['search_results'] = []
        
        elastic_hits = Elastic().search(self.state_dict)
        
        #Add search result ids to state_dict
        self.state_dict['search_results'] = [hit['id'] for hit in elastic_hits]
        self.state_dict['stage'] = "completed-yes"
        redis_set(self.user_id, self.state_dict)
        
        return (None, None, elastic_hits)
        
        
    def reset_entity(self, entity):
        
        """Rests Entity to no items"""
        
        self.state_dict['search-params'][entity] = []
        if entity not in ["occasion", "technique"]:
            return self.check_and_respond("-deleted")
        else:
            return self.check_and_respond()
            
    
    def logic(self):
        
        """Handles Logic of Dialogflow by matching intents"""
        
        try:
        
            #early return if "start-over" or "functionality"
            if self.intent == "search-start-over":
                redis_delete(self.user_id)
                prompts = responses["start-over"]
                return (random.choice(prompts["text"]), prompts["quick-replies"], None)
                
            elif self.intent == "search-functionality-question":
                prompts = responses["functionality"]
                return (random.choice(prompts["text"]), prompts["quick-replies"], None)
    
    
            #for all else: fill search
            self.fill_search()
            
            #normal search
            if self.intent == "search":
                return self.check_and_respond()
            
            #no responses
            elif self.intent == "search-no":
                
                #set entity to None if not completed already
                if not self.state_dict.get("stage").startswith("completed"):
                    stage = self.state_dict.get("stage")
                    self.state_dict['search-params'][stage] = [None]
                    return self.check_and_respond("-none")
                
                #extra case for thanking
                elif "thank" in self.user_text:
                    return (random.choice(responses["thank-you"]), None, None)
                
                #if completed, ask for changes
                else:
                    if self.state_dict.get("stage") == "completed-no":
                        self.state_dict["stage"] = "completed-yes"
                        self.state_dict['search_batch'] = 0
                        return self.search()
                    else:
                        self.state_dict["stage"] = "completed-no"
                        redis_set(self.user_id, self.state_dict)
                        return (random.choice(responses["search-confirm-no"]), None, None)
            
            #yes responses
            elif self.intent == "search-yes":
                if not self.state_dict.get("stage") == "completed":
                    return self.check_and_respond("-yes")
                else:
                    self.state_dict['search_batch'] = 0
                    return self.search()
            
            #delete one item by name
            elif self.intent == "search-delete-1-item":
                
                removed = False
                for key,vals in self.state_dict['search-params'].items():
                    for c in self.changed:
                        if c in vals:
                            vals.remove(c)
                            removed = True
                if removed:
                    return self.check_and_respond("-deleted")
                else:
                    return (responses["delete-failed"][0].format(self.changed), None, None)
                    
            #delete entire category
            elif self.intent == "search-delete-meals":
                return self.reset_entity("meal")
            
            elif self.intent == "search-delete-time":
                return self.reset_entity("time")
            
            elif self.intent == "search-delete-difficulty":
                return self.reset_entity("difficulty")
            
            elif self.intent == "search-delete-cuisine":
                return self.reset_entity("cuisine")
            
            elif self.intent == "search-delete-ingredients":
                return self.reset_entity("ingredient")
            
            elif self.intent == "search-delete-specials":
                return self.reset_entity("special")
            
            elif self.intent == "search-delete-occasions":
                return self.reset_entity("occasion")
                
            elif self.intent == "search-delete-techniques":
                return self.reset_entity("technique")
                
            #search replace
            elif self.intent == "search-replace-with" or self.intent == "search-instead":
                index = 0 if self.intent == "search-replace-with" else 1
                if len(self.changed) == 2:
                    print(self.changed)
                    for key,vals in self.state_dict['search-params'].items():
                        if self.changed[index] in vals:
                            vals.remove(self.changed[index])
                            print(vals)
                    return self.check_and_respond()
                else:
                    return (responses["replace-failed"][0], None, None)
            
            #load more results, index ['search_batch']
            elif self.intent == 'search-load-more':
                self.state_dict['search_batch'] += 5
                if self.state_dict['search_batch'] == 20:
                    prompts = responses["no-more-results"]
                    return (random.choice(prompts['text']), prompts['quick-replies'], None)
                else:
                    return self.search()
                    
            #show current results again
            elif self.intent == 'search-show-current':
                 return self.search()
                
            #edit search
            elif self.intent == 'search-edit':
                return (random.choice(responses["search-edit"]).format(repr(self)), None, None)
            
            #custom fallback
            else:
                return (responses["intent-match-failed"], None, None)
         
        #TypeError fallback
        except TypeError:
            return (responses["intent-match-failed"], None, None)
