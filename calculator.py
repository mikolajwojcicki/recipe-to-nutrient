from schemas import IngredientInput, NutritionalData, AbsoluteNutritionalData

# Choi and Okos (1986) density at standard room temperature (20 degrees C).
# Units are kg/m^3 which is equivalent to g/L.
# To convert to g/ml, divide by 1000.
CHOI_OKOS_DENSITIES_20C = {
    "water": 995.74,
    "protein": 1319.53,
    "fat": 917.23,
    "carbs": 1592.89,
    "ash": 2418.18
}

def calculate_density_g_ml(macros_per_100g: NutritionalData) -> float:
    """
    Calculate the effective bulk density of a homogenous liquid using the 
    Choi and Okos (1986) volume additive rules based on its macro constituents.
    """
    # Mass fractions (Xi) for each component (grams per gram)
    x_water = macros_per_100g.water_g / 100.0
    x_protein = macros_per_100g.protein_g / 100.0
    x_fat = macros_per_100g.fat_g / 100.0
    x_carbs = macros_per_100g.carbs_g / 100.0
    x_ash = macros_per_100g.ash_g / 100.0
    
    # 1 / ρ_food = Σ(Xi / ρi)
    # Note: Using kg/m^3 for the component densities
    sum_inverse_density = 0.0
    
    if x_water > 0: sum_inverse_density += x_water / CHOI_OKOS_DENSITIES_20C["water"]
    if x_protein > 0: sum_inverse_density += x_protein / CHOI_OKOS_DENSITIES_20C["protein"]
    if x_fat > 0: sum_inverse_density += x_fat / CHOI_OKOS_DENSITIES_20C["fat"]
    if x_carbs > 0: sum_inverse_density += x_carbs / CHOI_OKOS_DENSITIES_20C["carbs"]
    if x_ash > 0: sum_inverse_density += x_ash / CHOI_OKOS_DENSITIES_20C["ash"]
    
    # If the API returned nothing (0 for all), just assume water density (~1.0 g/ml)
    if sum_inverse_density == 0:
        return 1.0
        
    density_kg_m3 = 1.0 / sum_inverse_density
    # Convert kg/m3 to g/ml
    density_g_ml = density_kg_m3 / 1000.0
    return density_g_ml


def convert_to_absolute(ingredient: IngredientInput, api_data: NutritionalData) -> AbsoluteNutritionalData:
    """
    Takes an ingredient input and its corresponding API data (or override data),
    and converts it into absolute mass and macronutrient figures.
    """
    # 1. Determine the base macros per 100g to use.
    if ingredient.override is not None:
        macros = NutritionalData(
            water_g=ingredient.override.water_g,
            protein_g=ingredient.override.protein_g,
            fat_g=ingredient.override.fat_g,
            carbs_g=ingredient.override.carbs_g,
            fiber_g=ingredient.override.fiber_g,
            ash_g=ingredient.override.ash_g,
            kcal=ingredient.override.kcal if ingredient.override.kcal is not None else (api_data.kcal if api_data else None),
            piece_weight_g=ingredient.override.piece_weight_g or (api_data.piece_weight_g if api_data else None)
        )
    else:
        macros = api_data
        
    # 2. Determine absolute total mass in grams based on unit
    total_mass_g = 0.0
    if ingredient.unit == "g":
        total_mass_g = ingredient.amount
    elif ingredient.unit == "piece":
        if macros.piece_weight_g:
            total_mass_g = ingredient.amount * macros.piece_weight_g
        else:
            # Fallback if piece size not available: assume an arbitrary 100g per piece to avoid crashes,
            # and print a warning.
            print(f"Warning: No piece size found for {ingredient.name}. Assuming 100g/piece.")
            total_mass_g = ingredient.amount * 100.0
    elif ingredient.unit == "ml":
        density = calculate_density_g_ml(macros)
        total_mass_g = ingredient.amount * density
    else:
        # Invalid unit
        raise ValueError(f"Unknown unit: {ingredient.unit}")
        
    # 3. Calculate absolute macros using scaling factor
    # Since 'macros' are per 100g, the scaling factor is total_mass_g / 100
    scale = total_mass_g / 100.0
    
    absolute_kcal = 0.0
    if macros.kcal is not None:
        absolute_kcal = macros.kcal * scale
    else:
        # Fallback to macro-based calculation
        absolute_kcal = (macros.protein_g * 4.0 + macros.carbs_g * 4.0 + macros.fat_g * 9.0) * scale
    
    return AbsoluteNutritionalData(
        total_mass_g=total_mass_g,
        water_g=macros.water_g * scale,
        protein_g=macros.protein_g * scale,
        fat_g=macros.fat_g * scale,
        carbs_g=macros.carbs_g * scale,
        fiber_g=macros.fiber_g * scale,
        ash_g=macros.ash_g * scale,
        kcal=absolute_kcal
    )
