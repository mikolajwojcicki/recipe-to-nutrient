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
    1085: "fat_g",
    1005: "carbs_g",
    1079: "fiber_g",
    1007: "ash_g",
    1008: "kcal"
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
        "pageSize": 1,
        "dataType": ["Foundation", "SR Legacy"]
    }
    
    try:
        response = requests.get(USDA_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        foods = data.get("foods", [])
        if not foods:
            params.pop("dataType")
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
            fiber_g=float(nutriments.get("fiber_100g", 0.0)),
            water_g=float(nutriments.get("water_100g", 0.0)),
            ash_g=0.0 # Ash is rarely reported on OFF
        )
        kcal = nutriments.get("energy-kcal_100g", None)
        if kcal is not None:
            result.kcal = float(kcal)
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
    
    if query.lower().strip() == "water":
        log("Hardcoded pure water detected.")
        return NutritionalData(
            water_g=100.0,
            protein_g=0.0,
            fat_g=0.0,
            carbs_g=0.0,
            fiber_g=0.0,
            ash_g=0.0,
            kcal=0.0
        )
        
    def estimate_water_if_missing(res: NutritionalData):
        if res.water_g == 0.0:
            estimated_water = 100.0 - res.protein_g - res.fat_g - res.carbs_g - res.ash_g
            if estimated_water > 0:
                res.water_g = estimated_water
                log(f"Water property missing/zero. Algebraically estimated water to {estimated_water:.1f}g based on remaining mass.")

    usda_result = fetch_from_usda(query)
    if usda_result is not None:
        estimate_water_if_missing(usda_result)
        return usda_result
        
    log(f"USDA failed or returned nothing for '{query}'. Trying Open Food Facts...")
    off_result = fetch_from_open_food_facts(query)
    if off_result is not None:
        estimate_water_if_missing(off_result)
        return off_result
        
    log(f"Could not find data for '{query}' anywhere. Defaulting to 0 macros.")
    return NutritionalData()
