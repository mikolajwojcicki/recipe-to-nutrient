from pydantic import BaseModel, ConfigDict, Field
from typing import List, Literal, Optional

class OverrideMacros(BaseModel):
    """
    Manual overrides for an ingredient's nutritional profile.
    Values should be provided per 100g or 100ml.
    """
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    water_g: float = 0.0
    ash_g: float = 0.0
    kcal: Optional[float] = None
    
    # Optional piece weight if unit is "piece"
    piece_weight_g: Optional[float] = None
    
    model_config = ConfigDict(extra='ignore')


class IngredientInput(BaseModel):
    """
    A single ingredient from the user's input JSON.
    """
    name: str = Field(..., description="Name of the ingredient to search for.")
    amount: float = Field(..., description="Amount of the ingredient.")
    unit: Literal["g", "ml", "piece"] = Field(..., description="Unit of measurement.")
    override: Optional[OverrideMacros] = Field(None, description="Optional manual macronutrient values to bypass APIs.")


class RecipeInput(BaseModel):
    """
    The top-level recipe structure from the user's input JSON.
    """
    recipe_name: str
    ingredients: List[IngredientInput]


class NutritionalData(BaseModel):
    """
    Standardized internal model for nutritional facts per 100g.
    """
    water_g: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    ash_g: float = 0.0
    kcal: Optional[float] = None
    
    # Optional piece weight if derived from API
    piece_weight_g: Optional[float] = None

    model_config = ConfigDict(extra='ignore')

class AbsoluteNutritionalData(BaseModel):
    """
    Standardized internal model for the absolute nutritional facts of a given amount of an ingredient.
    """
    total_mass_g: float = 0.0
    water_g: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    ash_g: float = 0.0
    kcal: float = 0.0
