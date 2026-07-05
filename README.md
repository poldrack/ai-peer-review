# AI Peer Review

This package facilitates AI-based peer review of academic papers, particularly in neuroscience. It uses multiple large language models (LLMs) to generate independent reviews of a paper, and then creates a meta-review summarizing the key points.

NOTE: All code in this project was AI-generated using Claude Code.

## Features

- Submit papers for review by multiple LLMs
- Generate individual peer reviews from various models
- Create a meta-review analyzing common themes and unique insights
- Generate a concerns table identifying which model found each concern
- Store results in markdown, CSV, and JSON formats

## Supported Models

- GPT-4o (via OpenAI API)
- GPT-4o-mini (via OpenAI API)
- Claude 3.7 Sonnet (via Anthropic API)
- Google Gemini 2.5 Pro (via Google AI API)
- DeepSeek R1 (via Together API)
- Llama 4 Maverick (via Together API)

## Installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Usage

### API Keys

You can set API keys in two ways:

#### Using the CLI config command

```bash
# Set API keys (recommended)
ai-peer-review config openai "your-openai-key"
ai-peer-review config anthropic "your-anthropic-key"
ai-peer-review config google "your-google-key"
ai-peer-review config together "your-together-ai-key"  # Used for DeepSeek R1 and Llama 4 Maverick
```

Keys are stored in `~/.ai-peer-review/config.json`.

#### Using environment variables

Alternatively, you can set environment variables either by exporting them or by using a `.env` file:

**Option 1: Export variables in your shell:**

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"
export TOGETHER_API_KEY="your-together-ai-key"  # Used for DeepSeek R1 and Llama 4 Maverick
```

**Option 2: Create a .env file:**

Copy the `.env.example` file to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit the .env file with your API keys
```

You can place the `.env` file in:
- The current working directory
- Your home directory at `~/.ai-peer-review/.env`

### Command Line Interface

Review a paper with all available models:

```bash
ai-peer-review review path/to/paper.pdf
```

Specify specific models to use:

```bash
ai-peer-review review path/to/paper.pdf --models "gpt4-o1,claude-3.7-sonnet"
```

Specify output directory:

```bash
ai-peer-review review path/to/paper.pdf --output-dir ./my_reviews
```

Skip meta-review generation:

```bash
ai-peer-review review path/to/paper.pdf --no-meta-review
```

Use a custom configuration file:

```bash
ai-peer-review --config-file /path/to/custom/config.json review path/to/paper.pdf
```

## Prompts and Configuration

The tool uses specific prompts for generating peer reviews and meta-reviews:

### Review Prompt

By default, papers are submitted to LLMs with the following prompt:

```
You are a neuroscientist and expert in brain imaging who has been asked to provide 
a peer review for a submitted research paper, which is attached here. Please provide 
a thorough and critical review of the paper. First provide a summary of the study 
and its results, and then provide a detailed point-by-point analysis of any flaws in the study.
```

### Meta-Review Prompt

The meta-review is generated using the following prompt:

```
The attached files contain peer reviews of a research article. Please summarize 
these into a meta-review, highlighting both the common points raised across reviewers 
as well as any specific concerns that were only raised by some reviewers. Then rank 
the reviews in terms of their usefulness and identification of critical issues.
```

When generating the meta-review, all model identifiers are removed from the individual reviews to prevent bias.

### Customizing Prompts

You can customize the prompts used by the tool by editing the configuration file:

1. Locate or create the configuration file at `~/.ai-peer-review/config.json`
2. Add or modify the `prompts` section:

```json
{
  "api_keys": {
    ...
  },
  "prompts": {
    "system": "Your custom system prompt",
    "review": "Your custom review prompt. Include the {paper_text} placeholder where the paper text should be inserted.",
    "metareview": "Your custom meta-review prompt. Include the {reviews_text} placeholder where the reviews should be inserted."
  }
}
```

The configuration file will be created automatically with default prompts if it doesn't exist. You can modify it to suit your needs.

### Using a Custom Configuration File

You can specify a custom configuration file path using the `--config-file` option:

```bash
ai-peer-review --config-file /path/to/custom/config.json review path/to/paper.pdf
```

This allows you to maintain multiple configuration files for different purposes or environments. The custom config file will be used for all operations in that command session, including loading prompts and API keys.

### Bundled profile: scientific-validity-only review

The repository ships a ready-to-use configuration profile at `configs/scientific-only.json` that swaps the default prompts for a **scientific-validity-only** reviewing standard. The review, meta-review, and concerns-extraction prompts instruct the models to raise a criticism only when resolving it could change the validity, support, scope, reproducibility, or interpretation of a scientific claim, and to exclude concerns whose only consequence is formatting, length, readability, layout, grammar, or prose style (a wording or labeling issue is kept only when it creates scientifically consequential ambiguity, such as an undefined unit or an inconsistent cohort label). The prompts ask for a recommendation that would be unchanged if the paper were reformatted without changing its evidence or claims.

This is useful when you want the models to focus on methods, inference, statistics, reproducibility, external validity, demonstrated novelty of explicit novelty claims, and claim-to-source support rather than producing presentation nitpicks. Because the prompts operate on the extracted PDF text, they instruct the models to treat a missing item as a request for clarification rather than asserting the work was not done.

Run a review with the profile via the existing `--config-file` option:

```bash
ai-peer-review --config-file configs/scientific-only.json review path/to/paper.pdf
```

API keys are resolved from `*_API_KEY` environment variables first (see [API Keys](#api-keys) above), so you do not need to put any secrets in the profile; its `api_keys` section is intentionally left empty. If you prefer to keep keys in a config file, copy the profile to a private, untracked location and add them there rather than editing the tracked copy.

The profile keeps the same placeholders (`{paper_text}`, `{reviews_text}`, `{meta_review_text}`, `{model_names}`, `{first_model}`, `{second_model}`, `{model_mapping}`), the `CONCERNS_TABLE_DATA` marker, the fenced JSON block, and the NATO phonetic reviewer names, so it preserves the interpolation and output-parsing contracts the existing pipeline relies on.

## Outputs

The tool generates the following outputs in the specified directory (default: `./papers/[paper-name]`):

- `review_[model-name].md` - Individual reviews from each LLM
- `meta_review.md` - Summary and analysis of all reviews
- `concerns_table.csv` - CSV file with concerns identified by each model
- `results.json` - Structured data containing all reviews, meta-review, and reviewer-to-model mapping