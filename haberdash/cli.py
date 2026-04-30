import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import pty
import select
import termios
import tty
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

try:
    import requests
except ImportError:
    print("Required dependencies not installed. Run: pip install requests")
    sys.exit(1)

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

import haberdash


def prompt_for_config() -> dict:
    print("Welcome to Haberdash! Let's set up your configuration.")
    print("Config will be saved as TOML at ~/.config/haberdash/config.toml")
    print()
    
    config = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o",
            "key": ""
        },
        "storage": {
            "cache_dir": str(Path.home() / "haberdash")
        }
    }
    
    base_url = input(f"API base URL [{config['openai']['base_url']}]: ").strip()
    if base_url: config["openai"]["base_url"] = base_url
    
    model = input(f"Model name [{config['openai']['model']}]: ").strip()
    if model: config["openai"]["model"] = model
    
    key = input("API key (optional for local models): ").strip()
    if key: config["openai"]["key"] = key
    
    cache_dir = input(f"Cache directory [{config['storage']['cache_dir']}]: ").strip()
    if cache_dir: config["storage"]["cache_dir"] = cache_dir
    
    config_path = Path.home() / ".config" / "haberdash" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"""[openai]
base_url = "{config['openai']['base_url']}"
model = "{config['openai']['model']}"
key = "{config['openai']['key']}"

[storage]
cache_dir = "{config['storage']['cache_dir']}"
"""
    
    with open(config_path, "w") as f:
        f.write(content)
    
    print(f"\nConfig saved to {config_path}")
    setup_haberdash_dirs(config["storage"]["cache_dir"])
    
    return config


def get_config() -> dict:
    config_path = Path.home() / ".config" / "haberdash" / "config.toml"
    
    if not config_path.exists():
        return prompt_for_config()
    
    try:
        with open(config_path, "rb") as f:
            if tomllib:
                config = tomllib.load(f)
            else:
                # Very basic fallback for simple TOML if library is missing
                print("Warning: TOML library missing. Using basic parser.")
                config = {"openai": {}, "storage": {}}
                content = f.read().decode()
                for line in content.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        v = v.strip().strip('"')
                        if "base_url" in k: config["openai"]["base_url"] = v
                        elif "model" in k: config["openai"]["model"] = v
                        elif "key" in k: config["openai"]["key"] = v
                        elif "cache_dir" in k: config["storage"]["cache_dir"] = v
            
            # Flatten or adapt to the rest of the app's expectations
            flat_config = {
                "openai_base_url": config.get("openai", {}).get("base_url", "https://api.openai.com/v1"),
                "model": config.get("openai", {}).get("model", "gpt-4o"),
                "key": config.get("openai", {}).get("key", ""),
                "cache_dir": config.get("storage", {}).get("cache_dir", str(Path.home() / "haberdash"))
            }
            return flat_config
    except Exception as e:
        print(f"Error reading config: {e}")
        return prompt_for_config()


def setup_haberdash_dirs(cache_dir: str):
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
    
    setup_haberdash_dirs(config["cache_dir"])
    
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


def record_shell_session(config: dict, verbose: bool) -> Tuple[str, List[str]]:
    """Open a PTY shell and record all commands. Returns (transcript, commands list)."""
    print("\n=== Macro Mode ===")
    print("Entering shell. Perform your task manually.")
    print("Exit with Ctrl+D or 'exit' when done.\n")
    
    transcript = []
    commands = []
    
    # Save original terminal settings
    old_tty = termios.tcgetattr(sys.stdin)
    
    try:
        # Create PTY
        master, slave = pty.openpty()
        
        # Fork shell process
        pid = os.fork()
        if pid == 0:
            # Child process
            os.close(master)
            os.setsid()
            os.dup2(slave, 0)
            os.dup2(slave, 1)
            os.dup2(slave, 2)
            os.close(slave)
            os.execlp(os.environ.get('SHELL', '/bin/bash'), '-i')
            sys.exit(1)
        
        # Parent process
        os.close(slave)
        
        # Set terminal to raw mode for passthrough
        tty.setraw(sys.stdin.fileno())
        
        current_line = ""
        command_buffer = []
        
        while True:
            ready, _, _ = select.select([master, sys.stdin], [], [], 0.1)
            
            if master in ready:
                try:
                    data = os.read(master, 1024)
                    if not data:
                        break
                    transcript.append(data.decode('utf-8', errors='replace'))
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()
                except OSError:
                    break
            
            if sys.stdin in ready:
                try:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    # Track what user types
                    decoded = data.decode('utf-8', errors='replace')
                    for char in decoded:
                        if char == '\r' or char == '\n':
                            if current_line.strip():
                                commands.append(current_line.strip())
                                if verbose:
                                    print(f"\n[DEBUG] Captured command: {current_line}")
                            current_line = ""
                        elif char == '\x7f':  # Backspace
                            current_line = current_line[:-1] if current_line else ""
                        elif ord(char) >= 32:  # Printable
                            current_line += char
                    os.write(master, data)
                except OSError:
                    break
        
        # Wait for child
        os.waitpid(pid, 0)
        
    finally:
        # Restore terminal
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        print("\n")  # Newline after shell exits
    
    full_transcript = ''.join(transcript)
    return full_transcript, commands


def analyze_macro(config: dict, transcript: str, commands: List[str], verbose: bool, macro_context: Optional[str] = None) -> Dict[str, Any]:
    """Ask AI what the user was trying to accomplish, with optional macro context."""
    
    macro_info = ""
    if macro_context:
        macro_info = f"\nThis session is applying a specific 'skill' or 'macro' defined as follows:\n{macro_context}\n"
    
    prompt = f"""You are an expert at understanding command-line workflows.

I recorded a user working in a shell.{macro_info}

I need you to:
1. Figure out what they were trying to accomplish
2. Summarize the task in one sentence
3. Determine what remains to be done to complete it
4. Provide the exact commands needed to finish

Commands executed: {commands}

Shell transcript:
{transcript[:4000]}

Return ONLY a JSON object with these keys:
- "task_summary": Brief description of what user was doing
- "status": Current state (e.g., "in_progress", "ready_to_complete")
- "completion_commands": Array of exact commands to finish the task
- "explanation": What the remaining commands will do
"""
    
    if verbose:
        print(f"\nAnalyzing macro with AI...")
    
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
        print(f"AI Analysis: {content}\n")
    
    import json
    try:
        result = json.loads(content)
        return result
    except json.JSONDecodeError:
        print(f"Failed to parse AI response: {content}")
        return {
            "task_summary": "unknown",
            "status": "unknown",
            "completion_commands": [],
            "explanation": "Could not parse AI response"
        }


def execute_macro(config: dict, analysis: Dict[str, Any], verbose: bool, working_dir: str = ".", guard: Optional[str] = None, docker_image: str = "alpine:latest", chroot_root: str = "/tmp/haberdash-chroot"):
    """Execute the completion commands."""
    commands = analysis.get("completion_commands", [])
    if not commands:
        print("No completion commands provided.")
        return
    
    print(f"\nExecuting: {analysis.get('task_summary', 'task')}")
    print(f"Description: {analysis.get('explanation', 'N/A')}")
    if guard:
        print(f"Guard mode: {guard}")
    print()
    
    for cmd in commands:
        print(f"$ {cmd}")
        try:
            if guard == "docker":
                run_docker(docker_image, working_dir, cmd, verbose=verbose)
            elif guard == "chroot":
                run_chroot(chroot_root, cmd, verbose=verbose)
            else:
                subprocess.run(cmd, shell=True, cwd=working_dir, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            response = input("Continue with remaining commands? (y/n): ")
            if response.lower() != 'y':
                break


def run_macro_mode(config: dict, verbose: bool, guard: Optional[str] = None, docker_image: str = "alpine:latest", chroot_root: str = "/tmp/haberdash-chroot", save_name: Optional[str] = None):
    """Run the macro recording and execution mode."""
    transcript, commands = record_shell_session(config, verbose)
    
    if not commands:
        print("\nNo commands recorded. Exiting.")
        return
    
    print(f"\nRecorded {len(commands)} commands:")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. {cmd}")
    
    print("\nAnalyzing session...")
    analysis = analyze_macro(config, transcript, commands, verbose)
    
    # Save macro if requested
    if save_name:
        from haberdash.macros import save_recorded_macro
        save_path = save_recorded_macro(save_name, transcript, commands, analysis)
        print(f"\nMacro saved to: {save_path}")
        print(f"Run it anytime with: haby {save_name}")
        return
    
    task_summary = analysis.get("task_summary", "unknown task")
    
    print(f"\n{'='*60}")
    print(f"Detected task: {task_summary}")
    print(f"Status: {analysis.get('status', 'unknown')}")
    if analysis.get("explanation"):
        print(f"Explanation: {analysis['explanation']}")
    print(f"{'='*60}\n")
    
    completion_cmds = analysis.get("completion_commands", [])
    if completion_cmds:
        print("Suggested commands to complete:")
        for cmd in completion_cmds:
            print(f"  $ {cmd}")
        print()
    
    response = input("Proceed with completion? (y/n/e[edit]): ").lower().strip()
    
    if response == 'y':
        execute_macro(config, analysis, verbose, ".", guard, docker_image, chroot_root)
    elif response == 'e':
        # Allow editing
        print("\nEnter completion commands (one per line, empty line to finish):")
        edited_cmds = []
        while True:
            cmd = input("$ ").strip()
            if not cmd:
                break
            edited_cmds.append(cmd)
        if edited_cmds:
            analysis["completion_commands"] = edited_cmds
            execute_macro(config, analysis, verbose, ".", guard, docker_image, chroot_root)
    else:
        print("Cancelled.")


def run_docker(image: str, working_dir: str, command: str, args: Optional[List[str]] = None, verbose: bool = False):
    """Run a command in a Docker container."""
    import shutil
    
    if shutil.which("docker") is None:
        print("Error: docker command not found")
        print("Please install Docker: https://docs.docker.com/get-docker/")
        sys.exit(1)
    
    docker_args = [
        "docker", "run", "--rm",
        "-v", f"{working_dir}:{working_dir}",
        "-w", working_dir,
        image,
        "/bin/sh", "-c", command
    ]
    
    if verbose:
        print(f"Running in Docker: {' '.join(docker_args)}")
    
    try:
        subprocess.run(docker_args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Docker command failed with exit code {e.returncode}")
        raise


def run_chroot(chroot_root: str, command: str, args: Optional[List[str]] = None, verbose: bool = False):
    """Run a command in a chroot jail."""
    if os.geteuid() != 0:
        print("Error: chroot requires root privileges")
        print("Try: sudo haby --guard chroot ...")
        sys.exit(1)
    
    if not os.path.exists(chroot_root):
        print(f"Error: Chroot directory does not exist: {chroot_root}")
        print(f"Create it first with: sudo mkdir -p {chroot_root}")
        sys.exit(1)
    
    if shutil.which("chroot") is None:
        print("Error: chroot command not found")
        sys.exit(1)
    
    chroot_args = ["chroot", chroot_root, "/bin/sh", "-c", command]
    
    if verbose:
        print(f"Running in chroot: {' '.join(chroot_args)}")
    
    try:
        subprocess.run(chroot_args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Chroot command failed with exit code {e.returncode}")
        raise


def handle_macro_command(args, config: dict):
    """Handle the 'macro' subcommand."""
    action = args.macro_action
    
    from haberdash.macros import list_macros, load_macro, delete_macro, get_macro_path
    
    if action == "list":
        macros = list_macros()
        if not macros:
            print("No macros found.")
            return
        
        print(f"{'NAME':<20} {'LOCATION':<10} {'DESCRIPTION'}")
        print("-" * 60)
        for m in macros:
            print(f"{m['name']:<20} {m['location']:<10} {m['description']}")
            
    elif action == "show":
        if not args.name:
            print("Error: Macro name required.")
            return
        
        result = load_macro(args.name)
        if not result:
            print(f"Macro '{args.name}' not found.")
            return
            
        macro, path = result
        print(f"Macro: {macro['name']}")
        print(f"Path:  {path}")
        print(f"Description: {macro['description']}")
        print("-" * 40)
        
        if macro.get("detect"):
            print("\nDetection Steps:")
            for d in macro["detect"]:
                if d["type"] == "file_exists":
                    print(f"  - If {d['file']} exists, set {d['var']} = {d['value']}")
                elif d["type"] == "ask":
                    print(f"  - Ask '{d['question']}' -> {d['var']}")
                    
        if macro.get("ask"):
            print("\nQuestions:")
            for qid, q in macro["ask"].items():
                print(f"  - {qid}: {q['question']} (default: {q.get('default', 'None')})")
                
        if macro.get("execute"):
            print("\nExecution Steps:")
            for i, cmd in enumerate(macro["execute"], 1):
                if cmd["type"] == "conditional":
                    print(f"  {i}. IF {cmd['condition_var']} == \"{cmd['condition_value']}\": {cmd['command']}")
                elif cmd["type"] == "loop":
                    print(f"  {i}. FOR EACH {cmd['item_var']} IN {cmd['list_var']}: {cmd['command']}")
                else:
                    print(f"  {i}. {cmd['command']}")
                    
    elif action == "delete":
        if not args.name:
            print("Error: Macro name required.")
            return
            
        confirm = input(f"Are you sure you want to delete macro '{args.name}'? (y/n): ")
        if confirm.lower() == 'y':
            if delete_macro(args.name):
                print(f"Macro '{args.name}' deleted.")
            else:
                print(f"Macro '{args.name}' not found.")
        else:
            print("Cancelled.")
            
    elif action == "edit":
        if not args.name:
            print("Error: Macro name required.")
            return
            
        path = get_macro_path(args.name)
        if not path:
            print(f"Macro '{args.name}' not found.")
            return
            
        editor = os.environ.get("EDITOR", "vim")
        print(f"Opening {path} in {editor}...")
        subprocess.run([editor, str(path)])
    
    else:
        print("Usage: haby macro [list|show|delete|edit] [name]")


def main():
    parser = argparse.ArgumentParser(description="Run code from GitHub in one command (Haberdash)")
    
    # We'll use a two-pass approach to support both positional URLs and subparsers
    # or just handle the subcommand manually.
    commands = ["macro", "config"]
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        subparsers = parser.add_subparsers(dest="subcommand")
        
        # Macro management subcommand
        macro_parser = subparsers.add_parser("macro", help="Manage macros")
        macro_action_subparsers = macro_parser.add_subparsers(dest="macro_action")
        macro_action_subparsers.add_parser("list", help="List available macros")
        show_parser = macro_action_subparsers.add_parser("show", help="Show macro details")
        show_parser.add_argument("name", help="Macro name")
        delete_parser = macro_action_subparsers.add_parser("delete", help="Delete a macro")
        delete_parser.add_argument("name", help="Macro name")
        edit_parser = macro_action_subparsers.add_parser("edit", help="Edit a macro")
        edit_parser.add_argument("name", help="Macro name")
        
        # Config management subcommand
        subparsers.add_parser("config", help="Edit configuration file")
    
    # Common arguments
    parser.add_argument("url", nargs='?', help="GitHub repository URL or macro name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    parser.add_argument("--no-install", action="store_true", help="Skip installing dependencies")
    parser.add_argument("--list", "-l", action="store_true", help="List available macros")
    parser.add_argument("--show", metavar="NAME", help="Show macro details")
    parser.add_argument("--edit", metavar="NAME", help="Edit a macro")
    parser.add_argument("--delete", metavar="NAME", help="Delete a macro")
    parser.add_argument("--macro", "-m", action="store_true", help="Record shell session and auto-complete the task")
    parser.add_argument("--save", "-s", metavar="NAME", help="Save recorded macro as NAME")
    parser.add_argument("--guard", choices=["chroot", "docker"], help="Run in isolated environment (chroot or docker)")
    parser.add_argument("--docker-image", default="alpine:latest", help="Docker image to use (default: alpine:latest)")
    parser.add_argument("--chroot-root", default="/tmp/haberdash-chroot", help="Chroot root directory (default: /tmp/haberdash-chroot)")
    
    args = parser.parse_args()
    config = get_config()
    
    # Handle subcommands if any
    subcommand = getattr(args, 'subcommand', None)
    if subcommand == "macro":
        handle_macro_command(args, config)
        return
    
    if subcommand == "config":
        config_path = Path.home() / ".config" / "haberdash" / "config.toml"
        editor = os.environ.get("EDITOR", "vim")
        print(f"Opening {config_path} in {editor}...")
        subprocess.run([editor, str(config_path)])
        return
    
    # Handle top-level management flags
    if args.list:
        from haberdash.macros import list_macros
        macros = list_macros()
        if not macros:
            print("No macros found.")
        else:
            print(f"{'NAME':<20} {'LOCATION':<10} {'DESCRIPTION'}")
            print("-" * 60)
            for m in macros:
                print(f"{m['name']:<20} {m['location']:<10} {m['description']}")
        return

    if args.show:
        from haberdash.macros import load_macro
        result = load_macro(args.show)
        if not result:
            print(f"Macro '{args.show}' not found.")
        else:
            macro, path = result
            print(f"Macro: {macro['name']}")
            print(f"Path:  {path}")
            print(f"Description: {macro['description']}")
            print("-" * 40)
            if macro.get("detect"):
                print("\nDetection Steps:")
                for d in macro["detect"]:
                    if d["type"] == "file_exists":
                        print(f"  - If {d['file']} exists, set {d['var']} = {d['value']}")
                    elif d["type"] == "ask":
                        print(f"  - Ask '{d['question']}' -> {d['var']}")
            if macro.get("ask"):
                print("\nQuestions:")
                for qid, q in macro["ask"].items():
                    print(f"  - {qid}: {q['question']} (default: {q.get('default', 'None')})")
            if macro.get("execute"):
                print("\nExecution Steps:")
                for i, cmd in enumerate(macro["execute"], 1):
                    if cmd["type"] == "conditional":
                        print(f"  {i}. IF {cmd['condition_var']} == \"{cmd['condition_value']}\": {cmd['command']}")
                    elif cmd["type"] == "loop":
                        print(f"  {i}. FOR EACH {cmd['item_var']} IN {cmd['list_var']}: {cmd['command']}")
                    else:
                        print(f"  {i}. {cmd['command']}")
        return

    if args.edit:
        from haberdash.macros import get_macro_path
        path = get_macro_path(args.edit)
        if not path:
            print(f"Macro '{args.edit}' not found.")
        else:
            editor = os.environ.get("EDITOR", "vim")
            print(f"Opening {path} in {editor}...")
            subprocess.run([editor, str(path)])
        return

    if args.delete:
        from haberdash.macros import delete_macro
        confirm = input(f"Are you sure you want to delete macro '{args.delete}'? (y/n): ")
        if confirm.lower() == 'y':
            if delete_macro(args.delete):
                print(f"Macro '{args.delete}' deleted.")
            else:
                print(f"Macro '{args.delete}' not found.")
        else:
            print("Cancelled.")
        return
    
    # Handle the case where someone might do 'haby list' and it's not a URL/macro
    # but they meant 'haby macro list'
    if args.url in ["list", "show", "delete", "edit"] and not args.macro:
        # Check if a macro with this name exists first
        from haberdash.macros import get_macro_path
        if not get_macro_path(args.url):
            print(f"Warning: You used '{args.url}' which is a macro management command.")
            print(f"Did you mean 'haby macro {args.url}'?")
            print(f"If you have a macro named '{args.url}', use 'haby run {args.url}' (coming soon) or just 'haby {args.url}'.")
    
    # Check if url is a macro name (no slashes, no dots)
    if args.url and '/' not in args.url and '.' not in args.url:
        from haberdash.macros import load_macro
        result = load_macro(args.url)
        if result:
            macro, path = result
            print(f"\n--- Applying Skill: {macro['name']} ---")
            print(f"Description: {macro['description']}")
            print("Establish context in the subshell, then exit to complete.\n")
            
            # Record session
            transcript, commands = record_shell_session(config, args.verbose)
            
            # Analyze with macro context
            with open(path) as f:
                macro_content = f.read()
            
            print("Analyzing context...")
            analysis = analyze_macro(config, transcript, commands, args.verbose, macro_context=macro_content)
            
            # Show analysis and ask to proceed
            task_summary = analysis.get("task_summary", "unknown task")
            print(f"\nDetected intent: {task_summary}")
            if analysis.get("explanation"):
                print(f"Plan: {analysis['explanation']}")
            
            completion_cmds = analysis.get("completion_commands", [])
            if completion_cmds:
                print("\nCommands to finish:")
                for cmd in completion_cmds:
                    print(f"  $ {cmd}")
                print()
                
                response = input("Execute? (y/n/e[edit]): ").lower().strip()
                if response == 'y':
                    execute_macro(config, analysis, args.verbose, ".", args.guard, args.docker_image, args.chroot_root)
                elif response == 'e':
                    print("\nEnter commands (empty line to finish):")
                    edited_cmds = []
                    while True:
                        cmd = input("$ ").strip()
                        if not cmd: break
                        edited_cmds.append(cmd)
                    if edited_cmds:
                        analysis["completion_commands"] = edited_cmds
                        execute_macro(config, analysis, args.verbose, ".", args.guard, args.docker_image, args.chroot_root)
            else:
                print("\nAI did not suggest any completion commands.")
            return
        # If not found, fall through to treat as URL
    
    if args.macro:
        run_macro_mode(config, args.verbose, guard=args.guard, docker_image=args.docker_image, chroot_root=args.chroot_root, save_name=args.save)
        return
    
    if not args.url:
        parser.error("URL is required unless using --macro mode")
    
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
