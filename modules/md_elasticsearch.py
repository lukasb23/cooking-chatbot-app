#Imports
from elasticsearch import Elasticsearch
import json
import random
import os

#Modules
from .md_join import join
from .md_redis import redis_get


#Elastic connection
with open("config/keys.json") as f: 
    elastic_host = json.load(f)['ELASTIC_HOST']
es = Elasticsearch("http://{}:9200".format(elastic_host))

#No urls
with open("data/no_urls.json", "r") as f:
    image_urls = json.load(f)

    
class Elastic:
    
    def __init__(self):
        
        self.index = "recipes"
        self.doc_type = "recipe"
        
    
    ################# Search Functions ##########################
        
    def get_search_terms(self, state_dict):
        
        """Extracts search terms from state_dict"""
        
        shoulds = []
        all_tags = []
        for k,vals in state_dict['search-params'].items():
            boost = self.boosts.get(k)
            if vals == [None]:
                continue
            else:
                for val in vals:
                    shoulds.append({"term": {"categories.{}".format(k): {"value": "{}".format(val),
                                                                         "boost": boost}}})
                    all_tags.append(val)
        return shoulds, all_tags
        
    
    def should_query(self, b=0):
        
        """Fits search terms into Elasticsearch body structure for querying exact tags"""
        
        return {"from": b, "size": b+5, "query" : {"bool" : {"should" : self.shoulds}}}
        
    
    def fill_hit_list(self, hits):
        
        """Returns display parameters for Messenger webslider (max=5)"""
        
        for hit in hits:
            
            if len(self.hit_list) < 5:
            
                hit_dict = {'id': hit['_id'],
                     'recipe_id': hit['_source']['_recipe_id'],
                     'desc': hit['_source']['desc'],
                     'image_url': hit['_source']['image_link'],
                     'title': hit['_source']['title'],
                     'url': hit['_source']['url'] }
                
                if hit_dict['image_url'] == None:
                    hit_dict['image_url'] = random.choice(image_urls['no-urls'])
                
                if hit_dict['desc'] == None:
                    try:
                        hit_dict['desc'] = hit['_source']['preperation'][:100]
                    except KeyError:
                        hit_dict['desc'] = "Recipe including " +join(self.tags) +"."
                    
                #dedup
                ids = [hit['id'] for hit in self.hit_list]
                if not hit_dict['id'] in ids:
                    self.hit_list.append(hit_dict)
                
            else: break

    
    def run_search(self, body):
        
        """Runs Elasticsearch and fills max. 5 entries in the hit list"""

        res = es.search(
                index = self.index,
                doc_type = self.doc_type,
                body = body
            )
        self.fill_hit_list(res['hits']['hits'])
      
        
    def search(self, state_dict):
        
        """Builds and runs search"""
        
        self.boosts = {"meal": 3, "time": 3, "difficulty": 2, "ingredient": 4,
                       "special": 3, "cuisine": 1, "occasion": 1, "technique": 1}
        self.hit_list = []
        self.shoulds, self.tags = self.get_search_terms(state_dict)
        
        #run tag search
        self.run_search(self.should_query(state_dict['search_batch']))
        
        return self.hit_list
        
        
    ################# Retrieve Functions ##########################

    def get_recipe_details(self, recipe_id, field):
    
        """Retrieves recipe details based on _id"""
        
        res = es.get(index=self.index, doc_type=self.doc_type, id=recipe_id)
        
        #servings data
        servings = res['_source'].get("servings")
       
        #nutrient data
        if field == "nutrients":
            if res['_source'].get("nutrients"):
                res_list = Nutrients(res['_source']['nutrients']).get_nutrient_list()
                res_list = '\u2022 ' + '\n\u2022 '.join(res_list)
                if servings:
                    servings = "\n\nPer serving (serves: {}).".format(servings)
                else:
                    servings = "\n\nPer serving (total serves: unknown)."
            else:
                return "Apologies, for this recipes, there is no nutrient data available."
        
        #ingredient data
        elif field == "ingredients":
            res_list = self.get_grouped_ingredients(res['_source']['ingredients'])
            if res_list:
                if servings:
                     servings = "\n\nServes: {}.".format(servings)
                else:
                    servings = "\n\nNo data about serving size available."
            else:
                return "Apologies, for this recipe, there is no ingredients data available."
        
        return res_list+servings
        
        
    def get_grouped_ingredients(self, res_list):
            
        """Returns ingredients in grouped content format"""
            
        res_string = ""
        
        for res in res_list:
            k = res["ingredient_group"]
            if k is None:
                return None
            v = res["ingredient_group_content"]
            bullet_points = '\n\u2022 '.join(v)
            res_string = res_string +k +':\n\u2022 ' +bullet_points
        
        return res_string
      
          
    def send_recipe_details(self, user_id, payload, kind):
        
        """Retrieves and sends recipe details"""
        
        option = int(payload.split("_")[2])
        try:
            recipe_id = redis_get(user_id)['search_results'][option]
        except TypeError:
            return None
        return self.get_recipe_details(recipe_id, kind)



class Nutrients:
    
    def __init__(self, nutrient_dict):
        
        self.nutrients = nutrient_dict
        self.mapping_terms = {"calories": "Calories",
                   "fat": "Fat (g)",
                   "saturated_fat": "Saturated Fat (g)",
                   "poly_fat": "Polyunsaturated Fat (g)",
                   "mono_fat": "Monounsaturated Fat (g)",
                   "sodium": "Sodium (mg)",
                   "carbohydrates": "Carbohydrates (g)",
                   "protein": "Protein (g)",
                   "fiber": "Fiber (g)",
                   "cholesterol": "Cholesterol (mg)"}
                   
        self.mapping_nutrients = {"calories": 2000,
                   "fat": 69,
                   "saturated_fat": 16,
                   "poly_fat": 16,
                   "mono_fat": 37,
                   "sodium": 2350,
                   "carbohydrates": 320,
                   "protein": 50,
                   "fiber": 25,
                   "cholesterol": 300}
        
        
    def get_nutrient_list(self):
        
        """Gets nutrients from results and makes list representation"""
        
        nutrient_list = []
        for k,v in self.nutrients.items():
            if v is None:
                continue
            key = self.mapping_terms[k]
            percent = round(v / self.mapping_nutrients[k] * 100)
            nutrient_list.append("{}: {} ({}%)".format(key,v,percent))
        return nutrient_list
