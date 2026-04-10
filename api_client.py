import os
import requests
from typing import Optional
from dotenv import load_dotenv
from schemas import NutritionalData

load_dotenv()

USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

# Known USDA Nutrient IDs
NUTRIENT_IDS = {
    1051: "water_g",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
    1007: "ash_g"
}

def fetch_from_usda(query: str) -> Optional[NutritionalData]:
    """
    Search the USDA FoodData Central API for the given ingredient.
    """
    if not USDA_API_KEY:
        print("Warning: USDA_API_KEY not found in environment. Skipping USDA fetch.")
        return None
        
    params = {
        "query": query,
        "api_key": USDA_API_KEY,
        "pageSize": 1
    }
    
    try:
        response = requests.get(USDA_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        foods = data.get("foods", [])
        if not foods:
            return None
            
        food = foods[0]
        nutrients = food.get("foodNutrients", [])
        
        # Build the nutritional data
        result = NutritionalData()
        for nutrient in nutrients:
            n_id = nutrient.get("nutrientId")
            if n_id in NUTRIENT_IDS:
                attr = NUTRIENT_IDS[n_id]
                setattr(result, attr, float(nutrient.get("value", 0.0)))
                
        # Look for a piece weight
        portions = food.get("foodPortions", [])
        if portions:
            # Try to find a reasonable "piece" equivalent, or just average them
            # For simplicity, we'll take the first available gram weight as the generic "piece" weight
            for portion in portions:
                gw = portion.get("gramWeight")
                if gw:
                    result.piece_weight_g = float(gw)
                    break
                    
        return result
        
    except requests.RequestException as e:
        print(f"USDA API error for '{query}': {e}")
        return None


def fetch_from_open_food_facts(query: str) -> Optional[NutritionalData]:
    """
    Search Open Food Facts as a fallback.
    """
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1
    }
    
    try:
        # User-Agent is highly recommended by Open Food Facts
        headers = {"User-Agent": "RecipeToNutrientCLI/1.0"}
        response = requests.get(OFF_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        products = data.get("products", [])
        if not products:
            return None
            
        product = products[0]
        nutriments = product.get("nutriments", {})
        
        result = NutritionalData(
            protein_g=float(nutriments.get("proteins_100g", 0.0)),
            fat_g=float(nutriments.get("fat_100g", 0.0)),
            carbs_g=float(nutriments.get("carbohydrates_100g", 0.0)),
            water_g=float(nutriments.get("water_100g", 0.0)),
            ash_g=0.0 # Ash is rarely reported on OFF
        )
        return result

    except requests.RequestException as e:
        print(f"Open Food Facts API error for '{query}': {e}")
        return None


def fetch_nutritional_data(query: str, verbose: bool = False, progress = None) -> NutritionalData:
    """
    Cascade fetching from USDA and then Open Food Facts.
    If both fail, returns empty (zeros) profile.
    """
    def log(msg, dim=True):
        if verbose:
            if progress:
                progress.console.print(f"[dim]{msg}[/dim]" if dim else msg)
            else:
                print(msg)

    log(f"Fetching data from APIs for '{query}'...")
    
    usda_result = fetch_from_usda(query)
    if usda_result is not None:
        return usda_result
        
    log(f"USDA failed or returned nothing for '{query}'. Trying Open Food Facts...")
    off_result = fetch_from_open_food_facts(query)
    if off_result is not None:
        return off_result
        
    log(f"Could not find data for '{query}' anywhere. Defaulting to 0 macros.")
    return NutritionalData()
