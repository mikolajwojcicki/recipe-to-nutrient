# Recipe Nutrition CLI

A robust, Python-based CLI application for calculating the exact nutritional content of recipes. It handles volumetric scaling (via scientific density conversion) and evaporative moisture loss during cooking to give you scientifically accurate per-100g macro breakdowns for your final dishes.

## Features

- **Strict Data Schemas:** Uses `pydantic` to read any target `recipe.json` with strict type validation. Includes support for `g`, `ml`, and `piece` units. It also supports full bypass of APIs with custom `override` macronutrients.
- **Dual-API Network Tier:** Queries **USDA FoodData Central** with built-in piece weight heuristic extraction. If USDA data isn't found, it falls back gracefully to **Open Food Facts** text search. Fully fault-tolerant (handles missing API keys or network timeouts by defaulting to 0 macros).
- **Choi-Okos Mathematical Core:** Applies the standard **Choi and Okos (1986)** additive constituent model at 20°C to automatically calculate the exact density of volumetric elements based on their macronutrient composition. Translates all quantities (`g`, `ml`, `piece`) into a standardized absolute grams figure before calculations.
- **Interactive CLI Interface:** Powered by `typer` and `rich`, providing a clean terminal user interface with a live loading spinner for API fetches. After parsing, it interacts with the user to ask for the cooked dish weight, calculates water evaporative loss, and renders a visually striking styled table for the final macronutrients exactly scaled to a `Per 100g` format!
- **Verbose Mode:** A `-v` or `--verbose` flag is available to debug or audit the exact API calls, data payloads retrieved, and absolute macro calculation per ingredient.

## Installation

Ensure you have Python 3.8+ installed. 

Create a virtual environment and install the dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

You must supply an API key to access to the USDA FoodData Central database. Create a `.env` file in the project's root and export your database key:
```bash
USDA_API_KEY=your_usda_key_here
```

## Usage

Create a recipe JSON file. Here is an example of what `test_recipe.json` looks like:

```json
{
  "recipe_name": "Test Omelette",
  "ingredients": [
    {
      "name": "large egg",
      "amount": 2,
      "unit": "piece"
    },
    {
      "name": "whole milk",
      "amount": 50,
      "unit": "ml"
    },
    {
      "name": "butter",
      "amount": 10,
      "unit": "g"
    },
    {
      "name": "salt",
      "amount": 2,
      "unit": "g",
      "override": {
        "ash_g": 100.0,
        "protein_g": 0.0,
        "fat_g": 0.0,
        "carbs_g": 0.0,
        "water_g": 0.0
      }
    }
  ]
}
```

To run the script against your recipe file, execute:

```bash
python main.py test_recipe.json
```

If you want to view verbose information on how the macros are fetched and calculated on a per-ingredient basis, append the `--verbose` flag:

```bash
python main.py test_recipe.json --verbose
```

### The Evaporation Step

After aggregating all raw macros, the CLI will output the **Total Raw Mass** and ask you for the final weight of the cooked dish. Enter the cooked weight. The CLI will calculate the water volume lost via evaporation, and output the **Final Prepared Nutritional Profile** scaled to 100g portions.
