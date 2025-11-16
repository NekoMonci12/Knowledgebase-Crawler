# Knowledge Base Builder Crawler

A flexible web-crawler tool that automatically downloads documentation pages, filters unwanted assets, and generates a clean RAG-ready knowledge base using `knowledge-base-builder`.

Designed for projects that need structured KB data for OpenWebUI, RAG pipelines, or custom LLM indexing systems.

---

## ✨ Features

- 🌐 Recursive crawler — crawls all pages under a specific URL subtree
- 🚫 Smart filtering — excludes assets (.png, .jpg, .js, .css, etc.) automatically
- 🧰 LLM-agnostic — supports:
> OpenAI<br>
> Gemini<br>
> Anthropic<br>
- 🔑 Auto provider logic
> Only 1 API key required depending on chosen provider
- 🧵 Multi-threaded crawler for faster scraping
- 📦 Exports structured RAG files into a chosen output directory
- ⚙️ Dual-input config: CLI args → fallback to .env → error if missing

---

## 📦 Installation

Clone the repository:
```
git clone https://github.com/NekoMonci12/Knowledgebase-Crawler
cd Knowledgebase-Crawler
```

---

## ⚙️ Configuration
> This tool uses CLI arguments, which automatically fall back to environment variables.

--- 

## 🚀 Usage
### Basic usage with CLI args
```python
python main.py \
  --url_target "https://docs.papermc.io/paper/dev/api/" \
  --threads_worker 8 \
  --llm_provider "openai" \
  --openai_api_key "YOUR_KEY" \
  --output_dir "./output" \
  --knowledge_name "knowledge_base.md"
```

### Using `.env` only
```python
python main.py
```

### Notes
>CLI args always override `.env`:
```python
python main.py --threads_worker 16
```