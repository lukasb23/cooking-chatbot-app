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
        self.exact_match = True
        
    
    ################# Search Functions ##########################
        
    def build_query(self, state_dict):
        
        """Extracts search terms from state_dict"""
        
        all_bools = []
        for k,vals in state_dict['search-params'].items():
         
            #boost = self.boosts.get(k)
            if vals == [None] or vals == []:
                continue
            else:
                term_list = []
                #must query for ingredient/special, must_not for must-not should for rest
                if k in ["ingredient", "special"]:
                    query = "must"
                elif k == "avoid":
                    k, query = ("ingredient", "must_not")
                else:
                    query = "should"
                
                #iterate and append
                for v in vals:
                    term_list.append({"term": {"categories.{}.keyword".format(k): {"value": "{}".format(v)}}})
                all_bools.append({"bool": {query: term_list}})
                    
        return all_bools
        
    
    def must_query(self, b=0):
        
        """Fits search terms into Elasticsearch body structure for MUST query"""
        
        print({"from": b, "size": 5, "query" : {"bool" : {"must" : self.bools}}})
        return {"from": b, "size": 5, "query" : {"bool" : {"must" : self.bools}}}
    
    def should_query(self, b=0, s=5):
        
        """Fits search terms into Elasticsearch body structure for SHOULD query"""
        
        return {"from": b, "size": s, "query" : {"bool" : {"should" : self.bools}}}
        
    
    def fill_hit_list(self, hits):
        
        """Returns display parameters for Messenger webslider (max=5)"""
        
        for hit in hits:
            
            subtitle = self.get_sub(hit['_source']['categories'],
                                    hit['_source']['rating'],
                                    hit['_source']['recomm_perc'])
            
            hit_dict = {'id': hit['_id'],
                 'recipe_id': hit['_source']['_recipe_id'],
                 'image_url': hit['_source']['image_link'],
                 'subtitle': subtitle,
                 'title': hit['_source']['title'],
                 'url': hit['_source']['url'] }
            
            if hit_dict['image_url'] is None:
                hit_dict['image_url'] = random.choice(image_urls['no-urls'])
            
            #dedup
            ids = [hit['id'] for hit in self.hit_list]
            if not hit_dict['id'] in ids:
                self.hit_list.append(hit_dict)
                
    
    def get_sub(self, categories, rating, recomm_perc):
        
        """Returns string representation for subtitle"""
        
        mapping = {None: "\U0001f636", 0: u"\u2639", 0.5: "\U0001F641",
                  1: "\U0001f615", 1.5: "\U0001f610", 2: "\U0001f610",
                  2.5: "\U0001f928", 3: "\U0001F642", 3.5: "\U0001F603",
                  4: "\U0001F603"}
        
        #categories
        meal = ["Main"] # to be adapted
        time_diff = [categories["time"][0], categories["difficulty"][0]]
        cuisine = [categories["cuisine"][0] if categories.get("cuisine") else ""]
        ingredients = categories["ingredient"][:3] if categories.get("ingredient") else [""]
        specials = categories["special"][:3] if categories.get("special") else [""]
        
        all_cats = meal+time_diff+cuisine+ingredients+specials
        if "" in all_cats:
            all_cats.remove("")
        all_cats = 'Tags: {}'.format(", ".join(all_cats))
            
        #rating/recomm
        first_line_tuple = (mapping[rating], str(rating), str(recomm_perc))
        first_line = "{} {}/4 | \U0001F374 {}%".format(*first_line_tuple)
        
        return first_line + "\n" + all_cats[:100]
        
        
    def run_search(self, body):
        
        """Runs Elasticsearch and fills max. 5 entries in the hit list"""

        res = es.search(
                index = self.index,
                doc_type = self.doc_type,
                body = body
            )
        self.fill_hit_list(res['hits']['hits'][:5])
      
        
    def search(self, state_dict):
        
        """Builds and runs search"""
        
        # self.boosts = {"meal": 3, "time": 3, "difficulty": 2, "ingredient": 3,
        #               "special": 3, "cuisine": 2, "occasion": 1, "technique": 1}
        self.hit_list = []
        self.bools = self.build_query(state_dict)
        
        #run must search
        self.run_search(self.must_query(state_dict['search_batch']))
        
        #if under 5 results, run should query for remaining, avoid duplicate results
        if len(self.hit_list) < 5:
            print('Entered the extra')
            self.exact_match = False
            self.run_search(self.should_query(state_dict['search_batch'],
                                              5+len(self.hit_list)))
        return (self.hit_list, self.exact_match)
        
        
    ################# Retrieve Functions ##########################

    def get_recipe_details(self, recipe_id, field):
    
        """Retrieves recipe details based on _id"""
        
        res = es.get(index=self.index, doc_type=self.doc_type, id=recipe_id)
        
        #servings data
        header = '{}\n\n'.format(res['_source'].get("title"))
        servings = res['_source'].get("servings")
        
        #nutrient data
        if field == "nutrients":
            if res['_source'].get("nutrients"):
                res_list = Nutrients(res['_source']['nutrients']).get_nutrient_list()
                res_list = 'Nutrients incl. % of daily need:\n' +'\u2022 ' +'\n\u2022 '.join(res_list)
                if servings:
                    servings = "\n\nPer serving, serves: {}.".format(servings)
                else:
                    servings = "\n\nPer serving, total serves: unknown."
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
        
        return header+res_list+servings
        
        
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
