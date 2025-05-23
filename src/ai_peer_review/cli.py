import click
import os
import json
import re
from pathlib import Path
from .review import process_paper, generate_meta_review
from .utils.config import get_api_key, set_api_key, get_prompt
from .version import __version__


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config-file",
    type=click.Path(exists=False),
    help="Path to a custom configuration file",
    envvar="AI_PEER_REVIEW_CONFIG_FILE"
)
@click.pass_context
def cli(ctx, config_file):
    """AI-based peer review of academic papers."""
    # Store config path in context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file


@cli.command()
@click.argument("service", type=click.Choice(["openai", "anthropic", "google", "together"]))
@click.argument("api_key", type=str)
@click.pass_context
def config(ctx, service, api_key):
    """Set API key for a service."""
    config_file = ctx.obj.get("config_file")
    set_api_key(service, api_key, config_file)
    click.echo(f"API key for {service} has been set successfully.")


@cli.command()
def list_models():
    """List all available models for review."""
    available_models = get_available_models()
    
    click.echo("Available models for peer review:")
    for model in available_models:
        click.echo(f"- {model}")
    
    click.echo("\nUse these model names with the --models option when running 'ai-peer-review review'.")


def get_available_models():
    """Return a list of all available models for review."""
    return [
        "gpt4-o1",
        "gpt4-o3-mini",
        "claude-3.7-sonnet",
        "gemini-2.5-pro",
        "deepseek-r1",
        "llama-4-maverick"
    ]


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./papers",
    help="Base directory to store reviews and meta-review",
)
@click.option(
    "--meta-review/--no-meta-review",
    default=True,
    help="Generate meta-review after individual reviews",
)
@click.option(
    "--models",
    type=str,
    help="Comma-separated list of models to use. Default is all supported models.",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite existing reviews",
)
@click.pass_context
def review(ctx, pdf_path, output_dir, meta_review, models, overwrite):
    """Process a paper and generate peer reviews using multiple LLMs."""
    # Use the input file's stem (filename without extension) as the output directory
    pdf_path = Path(pdf_path)
    file_stem = pdf_path.stem
    output_dir = Path(output_dir) / file_stem
    output_dir.mkdir(exist_ok=True, parents=True)
    
    click.echo(f"Output will be saved to: {output_dir}")
    
    available_models = get_available_models()
    
    selected_models = available_models
    if models:
        model_list = [m.strip() for m in models.split(",")]
        selected_models = [m for m in model_list if m in available_models]
        if not selected_models:
            click.echo(f"No valid models specified. Available models: {', '.join(available_models)}")
            return
    
    click.echo(f"Processing paper: {pdf_path}")
    click.echo(f"Selected models: {', '.join(selected_models)}")
    
    # Check for existing reviews and only process missing ones
    reviews = {}
    review_data = {}
    models_to_process = []
    
    for model_name in selected_models:
        review_file = output_dir / f"review_{model_name}.md"
        
        if review_file.exists() and not overwrite:
            # Read existing review
            with open(review_file, "r") as f:
                review_text = f.read()
            reviews[model_name] = review_text
            review_data[model_name] = review_text
            click.echo(f"Using existing review for {model_name} from {review_file}")
        else:
            models_to_process.append(model_name)
    
    # Process papers with LLMs for missing or to-be-overwritten reviews
    if models_to_process:
        click.echo(f"Processing models: {', '.join(models_to_process)}")
        config_file = ctx.obj.get("config_file")
        new_reviews = process_paper(pdf_path, models_to_process, config_file)
        
        # Save new reviews
        for model, review_text in new_reviews.items():
            review_file = output_dir / f"review_{model}.md"
            with open(review_file, "w") as f:
                f.write(review_text)
            reviews[model] = review_text
            review_data[model] = review_text
            click.echo(f"Review from {model} saved to {review_file}")
    
    if not reviews:
        click.echo("No reviews to process. Use --overwrite to regenerate existing reviews.")
    
    # Generate meta-review if requested
    if meta_review:
        click.echo("Generating meta-review...")
        config_file = ctx.obj.get("config_file")
        meta_review_text, nato_to_model = generate_meta_review(reviews, config_file)
        
        # Get the full meta-review text before cleaning for table extraction
        from .review import save_concerns_as_csv
        
        meta_review_file = output_dir / "meta_review.md"
        with open(meta_review_file, "w") as f:
            f.write(meta_review_text)
        click.echo(f"Meta-review saved to {meta_review_file}")
        
        # Extract concerns table and save as CSV with model names as columns
        from .review import GoogleClient
        meta_reviewer = GoogleClient(model="gemini-2.5-pro-preview-05-06")
        
        # Create reverse mapping from NATO code to model name
        model_names = list(reviews.keys())
        reviewer_codes = list(nato_to_model.keys())
        
        # Get custom config path if provided
        config_file = ctx.obj.get("config_file")
        
        # Get concerns extraction prompt from config
        prompt_template = get_prompt("concerns_extraction", config_file)
        if not prompt_template:
            # Fallback to hardcoded prompt if not found in config
            prompt_template = (
                "Based on the meta-review, extract all major concerns identified by reviewers.\n\n"
                "Create a JSON object with a 'concerns' array. Each concern object should have:\n"
                "1. A 'concern' field with a brief description\n"
                "2. One field for each model: {model_names}\n"
                "3. Each model field should be true if that model identified the concern, false otherwise\n\n"
                "Example structure:\n"
                "{{\n"
                "  \"concerns\": [\n"
                "    {{\n"
                "      \"concern\": \"Brief description of concern 1\",\n"
                "      \"{first_model}\": true,\n"
                "      \"{second_model}\": false,\n"
                "      ...\n"
                "    }},\n"
                "    ...\n"
                "  ]\n"
                "}}\n\n"
                "Return only valid JSON without any explanation.\n\n"
                "Meta-review:\n{meta_review_text}\n\n"
                "Model name mapping (for reference):\n{model_mapping}"
            )
        
        # Format the model names and mapping
        model_names_str = ', '.join(model_names)
        first_model = model_names[0] if model_names else ""
        second_model = model_names[1] if len(model_names) > 1 else ""
        model_mapping = ""
        for nato_code, model_name in nato_to_model.items():
            model_mapping += f"{nato_code}: {model_name}\n"
        
        prompt = prompt_template.format(
            model_names=model_names_str,
            first_model=first_model,
            second_model=second_model,
            meta_review_text=meta_review_text,
            model_mapping=model_mapping
        )
        
        json_text = meta_reviewer.generate(prompt)
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if json_match:
            try:
                # Convert to DataFrame
                import pandas as pd
                concerns_data = json.loads(json_match.group(0))
                if "concerns" in concerns_data:
                    df = pd.DataFrame(concerns_data["concerns"])
                    
                    # Ensure all model columns exist
                    for model_name in model_names:
                        if model_name not in df.columns:
                            df[model_name] = False
                    
                    # Save CSV
                    csv_path = output_dir / "concerns_table.csv"
                    df.to_csv(csv_path, index=False)
                    click.echo(f"Concerns table saved to {csv_path}")
            except Exception as e:
                click.echo(f"Error processing concerns table: {e}")
        
        # Save everything to JSON
        result = {
            "individual_reviews": review_data,
            "meta_review": meta_review_text,
            "reviewer_to_model": nato_to_model
        }
        
        json_file = output_dir / "results.json"
        with open(json_file, "w") as f:
            json.dump(result, f, indent=2)
        click.echo(f"All results saved to {json_file}")
    
    return reviews


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()