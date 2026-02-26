import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import requests
except ImportError:
    print("Required dependencies not installed. Run: pip install requests")
    sys.exit(1)

import autorun


def prompt_for_config() -> dict:
    print("Welcome to Autorun! Let's set up your configuration.")
    print()
    
    config = {}
    
    openai_base_url = input("OpenAI API base URL (e.g., https://api.openai.com/v1 or https://openrouter.ai/api/v1) [https://api.openai.com/v1]: ").strip()
    config["openai_base_url"] = openai_base_url or "https://api.openai.com/v1"
    
    model = input("Model name [gpt-4o]: ").strip()
    config["model"] = model or "gpt-4o"
    
    key = input("API key: ").strip()
    while not key:
        key = input("API key (required): ").strip()
    config["key"] = key
    
    cache_dir = input(f"Directory to store cloned repos and builds [{Path.home()/'autorun'}]: ").strip()
    config["cache_dir"] = cache_dir or str(Path.home() / "autorun")
    
    config_path = Path.home() / ".config" / "autorun"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        f.write(f"openai_base_url={config['openai_base_url']}\n")
        f.write(f"model={config['model']}\n")
        f.write(f"key={config['key']}\n")
        f.write(f"cache_dir={config['cache_dir']}\n")
    
    print(f"\nConfig saved to {config_path}")
    print(f"Creating directory structure at {config['cache_dir']}")
    setup_autorun_dirs(config["cache_dir"])
    
    return config


def get_config() -> dict:
    config_path = Path.home() / ".config" / "autorun"
    if not config_path.exists():
        return prompt_for_config()
    
    config = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    
    for key in ["openai_base_url", "model", "key", "cache_dir"]:
        if key not in config:
            print(f"Missing required config key: {key}")
            print("Running setup...")
            return prompt_for_config()
    
    return config


def setup_autorun_dirs(cache_dir: str):
    base_dir = Path(cache_dir)
    (base_dir / "pkgs").mkdir(parents=True, exist_ok=True)
    (base_dir / "bin").mkdir(parents=True, exist_ok=True)
    (base_dir / "lib").mkdir(parents=True, exist_ok=True)
    (base_dir / "include").mkdir(parents=True, exist_ok=True)


def clone_repo(url: str, config: dict) -> Tuple[str, str]:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
    if not match:
        print("Invalid GitHub URL. Format: https://github.com/user/repo")
        sys.exit(1)
    
    user, repo = match.groups()
    git_url = f"https://github.com/{user}/{repo}.git"
    
    setup_autorun_dirs(config["cache_dir"])
    
    pkgs_dir = Path(config["cache_dir"]) / "pkgs"
    repo_path = pkgs_dir / repo
    
    if repo_path.exists():
        print(f"Removing existing directory: {repo_path}")
        shutil.rmtree(repo_path)
    
    print(f"Cloning {git_url}...")
    subprocess.run(["git", "clone", git_url, str(repo_path)], check=True)
    
    return str(repo_path), repo


def find_readme(repo_path: str) -> Optional[str]:
    for name in ["README.md", "README.txt", "README", "readme.md", "readme.txt", "readme"]:
        path = Path(repo_path) / name
        if path.exists():
            return str(path)
    return None


def read_readme(readme_path: str) -> str:
    with open(readme_path) as f:
        return f.read()


def ask_ai(config: dict, readme: str, verbose: bool) -> Tuple[str, str, str]:
    prompt = f"""You are an expert developer. I will provide you with a GitHub repository's README file.

Your task is to determine how to run this project:

1. Identify the programming language from the README
2. Determine the install command (e.g., "npm install", "pip install -r requirements.txt", "cargo build", etc.)
3. Determine the run command (e.g., "npm start", "python main.py", "cargo run", etc.)

Return ONLY a JSON object with these exact keys:
- "language": the programming language (e.g., "python", "javascript", "rust", "go", etc.)
- "install": the exact command to install dependencies (empty string if none needed)
- "run": the exact command to run the project

Do not include any explanation. Just the JSON.

Here is the README:

{readme}"""
    
    if verbose:
        print(f"\nSending to AI ({config['model']}):\n{prompt[:500]}...")
    
    base_url = config['openai_base_url'].rstrip('/')
    endpoint = f"{base_url}/chat/completions"
    
    if verbose:
        print(f"Requesting: {endpoint}")
    
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {config['key']}",
            "Content-Type": "application/json"
        },
        json={
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        },
        timeout=60
    )
    
    if verbose:
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response text (first 500 chars): {response.text[:500]}")
    
    response.raise_for_status()
    
    if not response.text.strip():
        print("Empty response from API")
        sys.exit(1)
    
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        print("Error: API returned HTML instead of JSON")
        print(f"Your configured openai_base_url: {base_url}")
        print(f"Requested endpoint: {endpoint}")
        print("Ensure it points to the API endpoint, not the web interface")
        print("Expected: https://api.openai.com/v1 or https://openrouter.ai/api/v1")
        sys.exit(1)
    
    data = response.json()
    
    if verbose:
        print(f"\nRaw response: {data}\n")
    
    content = data["choices"][0]["message"]["content"] or ""
    content = content.strip()
    
    if verbose:
        print(f"\nAI Response:\n{content}\n")
    
    import json
    try:
        result = json.loads(content)
        language = result.get("language", "").strip()
        install = result.get("install", "").strip()
        run = result.get("run", "").strip()
        
        if not language and not install and not run:
            print("AI could not determine how to run this project")
            print(f"Response: {content}")
            sys.exit(1)
        
        return language, install, run
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response: {e}")
        print(f"Content was: {content}")
        sys.exit(1)


def install_deps(repo_path: str, install_cmd: str, verbose: bool):
    if not install_cmd:
        print("No install command needed")
        return
    
    print(f"Installing dependencies: {install_cmd}")
    
    if verbose:
        print(f"Working directory: {repo_path}")
    
    subprocess.run(install_cmd, shell=True, cwd=repo_path, check=True)


def run_project(repo_path: str, run_cmd: str, verbose: bool):
    if not run_cmd:
        print("No run command specified")
        return
    
    print(f"Running: {run_cmd}")
    
    if verbose:
        print(f"Working directory: {repo_path}")
    
    subprocess.run(run_cmd, shell=True, cwd=repo_path, check=True)


def ask_ai_to_fix(config: dict, error_output: str, readme_content: str, repo_path: str, verbose: bool) -> Tuple[List[str], List[str], List[str], str]:
    for root, dirs, files in os.walk(repo_path):
        relative_root = os.path.relpath(root, repo_path)
        dirs_to_check = ["bin", "lib", "include", "share"]
        if any(d in relative_root for d in dirs_to_check):
            continue
    
    prompt = f"""I tried to run a project but it failed. Here's the error:

{error_output}

The README is:

{readme_content}

Please determine what needs to be done to fix this:

1. Is it missing build tools (e.g., gcc, make, cmake, autoconf)?
2. Is it missing libraries (e.g., ffmpeg, libavformat-dev, libavcodec-dev)?
3. Are there environment variables that need to be set?

Return ONLY a JSON object with these exact keys:
- "missing_libs": array of library apt-get install commands if applicable
- "missing_tools": array of tool apt-get install commands if applicable
- "other_deps": array of other installation commands
- "run_fix": command to fix the issue if not covered by above

Return empty arrays if not applicable."""
    
    if verbose:
        print(f"\nAsking AI to fix error...\n{prompt[:500]}...")
    
    base_url = config['openai_base_url'].rstrip('/')
    endpoint = f"{base_url}/chat/completions"
    
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {config['key']}",
            "Content-Type": "application/json"
        },
        json={
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        },
        timeout=60
    )
    
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"] or ""
    content = content.strip()
    
    if verbose:
        print(f"\nAI Fix Response:\n{content}\n")
    
    import json
    try:
        result = json.loads(content)
        return (
            result.get("missing_libs", []),
            result.get("missing_tools", []),
            result.get("other_deps", []),
            result.get("run_fix", "")
        )
    except json.JSONDecodeError:
        print("Failed to parse AI fix response")
        return [], [], [], ""


def main():
    parser = argparse.ArgumentParser(description="Run code from GitHub in one command (Autorun)")
    parser.add_argument("url", help="GitHub repository URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    parser.add_argument("--no-install", action="store_true", help="Skip installing dependencies")
    
    args = parser.parse_args()
    
    config = get_config()
    
    repo_path, repo_name = clone_repo(args.url, config)
    
    readme_path = find_readme(repo_path)
    if not readme_path:
        print("No README found in repository")
        sys.exit(1)
    
    print(f"Found README: {readme_path}")
    
    readme_content = read_readme(readme_path)
    
    language, install_cmd, run_cmd = ask_ai(config, readme_content, args.verbose)
    
    print(f"\nDetected language: {language}")
    print(f"Install command: {install_cmd or 'None'}")
    print(f"Run command: {run_cmd}")
    
    if not args.no_install:
        install_deps(repo_path, install_cmd, args.verbose)
    
    max_tries = 3
    for attempt in range(max_tries):
        try:
            run_project(repo_path, run_cmd, args.verbose)
            break
        except subprocess.CalledProcessError as e:
            print(f"\nRun failed (exit code {e.returncode})")
            if attempt < max_tries - 1:
                print(f"Asking AI how to fix (attempt {attempt + 1}/{max_tries})...")
                missing_libs, missing_tools, other_deps, run_fix = ask_ai_to_fix(config, str(e), readme_content, repo_path, args.verbose)
                
                all_commands = missing_libs + missing_tools + other_deps
                if run_fix:
                    all_commands.append(run_fix)
                
                if all_commands:
                    print(f"\nAttempting to install dependencies and fix issues:")
                    for cmd in all_commands:
                        print(f"  Running: {cmd}")
                        try:
                            subprocess.run(cmd, shell=True, check=True)
                        except subprocess.CalledProcessError:
                            print(f"  Failed to run: {cmd}")
                    
                    print("\nRe-running build after installing dependencies...")
                    install_deps(repo_path, install_cmd, args.verbose)
                else:
                    print("\nNo fixes suggested by AI")
                    break
            else:
                print(f"\nFailed after {max_tries} attempts")


if __name__ == "__main__":
    main()