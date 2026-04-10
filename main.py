import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from types import SimpleNamespace

from schemas import RecipeInput
from api_client import fetch_nutritional_data
from calculator import convert_to_absolute

app = typer.Typer(help="Recipe Nutrition CLI - Calculate exact macros from raw ingredients.")
console = Console()

@app.command()
def calculate(
    recipe_path: Path = typer.Argument(..., help="Path to the JSON recipe file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """
    Calculate the precise nutritional breakdown of a recipe accounting for volume, mass, pieces, and moisture loss.
    """
    if not recipe_path.exists():
        console.print(f"[bold red]Error[/bold red]: File {recipe_path} does not exist.")
        raise typer.Exit(1)
        
    try:
        with open(recipe_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        recipe = RecipeInput(**data)
    except Exception as e:
        console.print(f"[bold red]Error parsing recipe[/bold red]: {e}")
        raise typer.Exit(1)
        
    console.print(f"\n[bold green]Processing Recipe: {recipe.recipe_name}[/bold green]")
    
    total_raw_mass = 0.0
    total_water = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    total_fiber = 0.0
    total_ash = 0.0
    total_kcal = 0.0
    
    # Process each ingredient
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Fetching data for {len(recipe.ingredients)} ingredients...", total=len(recipe.ingredients))
        
        for ingredient in recipe.ingredients:
            progress.update(task, description=f"Processing {ingredient.name}...")
            
            # 1. Fetch
            if ingredient.override:
                api_data = None # Will rely on override in conversion
                if verbose:
                    progress.console.print(f"[dim]Using override data for {ingredient.name}[/dim]")
            else:
                api_data = fetch_nutritional_data(ingredient.name, verbose=verbose, progress=progress)
                if verbose and api_data:
                    kcal_str = f"{api_data.kcal:.1f}kcal" if api_data.kcal is not None else "N/A"
                    progress.console.print(f"[dim]Fetched per-100g data for {ingredient.name}: kcal={kcal_str}, water={api_data.water_g:.1f}g, protein={api_data.protein_g:.1f}g, fat={api_data.fat_g:.1f}g, carbs={api_data.carbs_g:.1f}g, fiber={api_data.fiber_g:.1f}g[/dim]")
                
            # 2. Convert to absolute
            abs_data = convert_to_absolute(ingredient, api_data)
            if verbose:
                progress.console.print(f"[dim]Calculated absolute for {ingredient.amount} {ingredient.unit} of {ingredient.name}: mass={abs_data.total_mass_g:.1f}g, kcal={abs_data.kcal:.1f}kcal, water={abs_data.water_g:.1f}g, protein={abs_data.protein_g:.1f}g, fat={abs_data.fat_g:.1f}g, carbs={abs_data.carbs_g:.1f}g, fiber={abs_data.fiber_g:.1f}g[/dim]")
            
            # 3. Aggregate
            total_raw_mass += abs_data.total_mass_g
            total_water += abs_data.water_g
            total_protein += abs_data.protein_g
            total_fat += abs_data.fat_g
            total_carbs += abs_data.carbs_g
            total_fiber += abs_data.fiber_g
            total_ash += abs_data.ash_g
            total_kcal += abs_data.kcal
            
            progress.advance(task)
            
    console.print(f"\n[bold]Total Raw Mass:[/bold] {total_raw_mass:.2f} g")
    
    # 4. Evaporation prompt
    cooked_weight = typer.prompt("Cooking complete. Please enter the final weight of the cooked dish in grams (raw weight if uncooked)", type=float, default=total_raw_mass)
    
    if cooked_weight < 0:
        console.print("[bold red]Invalid total weight![/bold red]")
        raise typer.Exit(1)
        
    # Calculate water lost (or gained)
    mass_difference = total_raw_mass - cooked_weight
    total_water -= mass_difference
    
    # Sanity bounds check
    if total_water < 0:
        total_water = 0.0
        
    console.print(f"Evaporation: {mass_difference:.2f} g of water lost.")
    
    # 5. Calculate Final Per-100g Values
    if cooked_weight > 0:
        final_water_100g = (total_water / cooked_weight) * 100
        final_protein_100g = (total_protein / cooked_weight) * 100
        final_fat_100g = (total_fat / cooked_weight) * 100
        final_carbs_100g = (total_carbs / cooked_weight) * 100
        final_fiber_100g = (total_fiber / cooked_weight) * 100
        final_ash_100g = (total_ash / cooked_weight) * 100
        final_kcal_100g = (total_kcal / cooked_weight) * 100
    else:
        final_water_100g = final_protein_100g = final_fat_100g = final_carbs_100g = final_fiber_100g = final_ash_100g = final_kcal_100g = 0.0
        
    # 6. Display Table
    console.print("\n[bold]Final Prepared Nutritional Profile (Per 100g)[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Macronutrient")
    table.add_column("Amount per 100g", justify="right")
    
    table.add_row("Calories (est)", f"{final_kcal_100g:.1f} kcal")
    table.add_row("Water", f"{final_water_100g:.1f} g")
    table.add_row("Protein", f"{final_protein_100g:.1f} g")
    table.add_row("Fat", f"{final_fat_100g:.1f} g")
    table.add_row("Carbs", f"{final_carbs_100g:.1f} g")
    table.add_row("Fiber", f"{final_fiber_100g:.1f} g")
    table.add_row("Ash", f"{final_ash_100g:.1f} g")
    
    console.print(table)


if __name__ == "__main__":
    app()
