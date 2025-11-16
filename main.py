import os
import sys
import time
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from knowledge_base_builder import KBBuilder


# -------------------------------------------------
# CLI ARGUMENTS + ENV FALLBACK
# -------------------------------------------------

def get_config():
    parser = argparse.ArgumentParser(description="Recursive KB Crawler + Builder")

    parser.add_argument("--url_target", type=str,
                        help="Base URL to crawl")
    parser.add_argument("--threads_worker", type=int,
                        help="Number of threads")
    parser.add_argument("--llm_provider", type=str, choices=["openai", "gemini", "anthropic"],
                        help="LLM Provider")
    parser.add_argument("--openai_api_key", type=str,
                        help="OpenAI API key")
    parser.add_argument("--gemini_api_key", type=str,
                        help="Gemini API key")
    parser.add_argument("--anthropic_api_key", type=str,
                        help="Anthropic API key")
    parser.add_argument("--github_api_key", type=str,
                        help="Github API key (optional)")
    parser.add_argument("--output_dir", type=str,
                        help="Directory to save KB files")
    parser.add_argument("--knowledge_name", type=str,
                        help="Knowledge base file name")

    args = parser.parse_args()

    cfg = {
        "url_target": args.url_target or os.getenv("URL_TARGET"),
        "threads_worker": args.threads_worker or int(os.getenv("THREADS_WORKER", "10")),
        "llm_provider": args.llm_provider or os.getenv("LLM_PROVIDER"),
        "openai_api_key": args.openai_api_key or os.getenv("OPENAI_API_KEY"),
        "gemini_api_key": args.gemini_api_key or os.getenv("GEMINI_API_KEY"),
        "anthropic_api_key": args.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"),
        "github_api_key": args.github_api_key or os.getenv("GITHUB_API_KEY"),
        "output_dir": args.output_dir or os.getenv("OUTPUT_DIR") or "./output",
        "knowledge_name": args.knowledge_name or os.getenv("KNOWLEDGE_NAME") or "knowledge_base.md",
    }

    # Validate required fields
    missing = []

    if not cfg["url_target"]:
        missing.append("URL_TARGET or --url_target")

    if not cfg["llm_provider"]:
        missing.append("LLM_PROVIDER or --llm_provider")

    if not cfg["output_dir"]:
        missing.append("OUTPUT_DIR or --output_dir")

    # LLM provider-specific checks
    if cfg["llm_provider"] == "openai" and not cfg["openai_api_key"]:
        missing.append("OPENAI_API_KEY or --openai_api_key")

    if cfg["llm_provider"] == "gemini" and not cfg["gemini_api_key"]:
        missing.append("GEMINI_API_KEY or --gemini_api_key")

    if cfg["llm_provider"] == "anthropic" and not cfg["anthropic_api_key"]:
        missing.append("ANTHROPIC_API_KEY or --anthropic_api_key")

    if missing:
        print("\n[ERROR] Missing required configuration:")
        for m in missing:
            print(" -", m)
        print()
        sys.exit(1)

    return cfg


# -------------------------------------------------
# GLOBAL CRAWLER CONFIG
# -------------------------------------------------

EXCLUDED_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".css", ".js", ".ico", ".woff", ".woff2", ".ttf", ".otf",
    ".pdf", ".zip", ".tar", ".gz"
)

visited = set()
visited_lock = Lock()


# -------------------------------------------------
# UTILITIES
# -------------------------------------------------

def is_asset(url: str) -> bool:
    l = url.lower()
    return any(l.endswith(ext) for ext in EXCLUDED_EXT)


def normalize_url(base, href):
    if not href:
        return None

    full = urljoin(base, href)
    full = full.split("#")[0]

    if "?" in full:
        full = full.split("?")[0]

    return full


# -------------------------------------------------
# MULTITHREADED CRAWLER
# -------------------------------------------------

def crawl_page(url, base_url):
    """Fetch a single page and return sublinks."""
    try:
        print("[+] Fetch:", url)
        r = requests.get(url, timeout=10)
        if r.status_code >= 400:
            print("    [!] HTTP", r.status_code, "- skipped")
            return []

        soup = BeautifulSoup(r.text, "html.parser")

        links = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue

            full = normalize_url(url, href)
            if not full:
                continue

            if not full.startswith(base_url):
                continue

            if is_asset(full):
                continue

            links.append(full)

        return links

    except Exception as e:
        print("    [!] Error:", e)
        return []


def crawl(base_url, threads):
    pending = [base_url]
    all_pages = []

    with ThreadPoolExecutor(max_workers=threads) as executor:
        while pending:
            futures = {}
            for u in pending:
                futures[executor.submit(crawl_page, u, base_url)] = u

            pending = []

            for fut in as_completed(futures):
                url = futures[fut]

                with visited_lock:
                    visited.add(url)

                all_pages.append(url)

                found = fut.result()
                if not found:
                    continue

                for f in found:
                    with visited_lock:
                        if f not in visited:
                            visited.add(f)
                            pending.append(f)

    return sorted(set(all_pages))


# -------------------------------------------------
# MAIN BUILDER
# -------------------------------------------------

def main():
    cfg = get_config()

    base_url = cfg["url_target"]
    threads = cfg["threads_worker"]
    output_dir = cfg["output_dir"]
    knowledge_name = cfg["knowledge_name"]

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[*] Crawling: {base_url}")
    print(f"[*] Threads: {threads}")
    print(f"[*] Output: {output_dir}")
    print(f"[*] Provider: {cfg['llm_provider']}\n")

    pages = crawl(base_url, threads)

    print("\n[✓] Total pages:", len(pages))
    for p in pages:
        print(" -", p)

    # Prepare KBBuilder config
    kb_config = {}

    if cfg["llm_provider"] == "openai":
        kb_config["OPENAI_API_KEY"] = cfg["openai_api_key"]

    elif cfg["llm_provider"] == "gemini":
        kb_config["GOOGLE_API_KEY"] = cfg["gemini_api_key"]

    elif cfg["llm_provider"] == "anthropic":
        kb_config["ANTHROPIC_API_KEY"] = cfg["anthropic_api_key"]

    # Optional:
    if cfg["github_api_key"]:
        kb_config["GITHUB_API_KEY"] = cfg["github_api_key"]

    print("\n[*] Building Knowledge Base…")

    builder = KBBuilder(kb_config)
    kb_output = builder.build(pages)

    out_file = os.path.join(output_dir, knowledge_name)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(kb_output)

    print("\n[✓] KB Saved to:", out_file)
    print("[✓] Done!\n")


if __name__ == "__main__":
    main()
