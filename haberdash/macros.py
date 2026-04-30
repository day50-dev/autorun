"""
Haberdash macro system - markdown-based automation manifests.

Format:
  # Macro Name

  ## Detect
  - If file X exists, set VAR = value
  - Else ask "Question?" → store in VAR → save to file.json

  ## Ask
  - **question_id**: "Question text?"
    - Default: value or ${variable}
    - Type: string|confirm|select
    - Options: [for select type]
    - Validate: pattern
    - Store: path/to/answers.json

  ## Execute
  1. If CONDITION: command
  2. command with ${variable}
  3. For each ${item} in ${list}: command

  ## Save
  Save answers to path/to/answers.json
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


def parse_markdown_macro(content: str) -> Dict[str, Any]:
    """Parse a markdown macro manifest into structured data."""
    sections = {"name": "", "description": "", "detect": [], "ask": {}, "execute": [], "save": ""}
    
    lines = content.split('\n')
    current_section = None
    current_question = None
    
    for line in lines:
        line = line.strip()
        
        # Title
        if line.startswith('# ') and not line.startswith('## '):
            sections["name"] = line[2:].strip()
            continue
        
        # Description (paragraph after title)
        if sections["name"] and not sections["description"] and not line.startswith('#') and line:
            sections["description"] = line
            continue
        
        # Section headers
        if line.startswith('## '):
            section_name = line[3:].lower().strip()
            if section_name in ['detect', 'ask', 'execute', 'save']:
                current_section = section_name
                current_question = None
            continue
        
        # Parse detect section
        if current_section == "detect" and line.startswith('- '):
            detect_item = parse_detect_line(line[2:])
            if detect_item:
                sections["detect"].append(detect_item)
        
        # Parse ask section
        if current_section == "ask":
            if line.startswith('- **') and '**:' in line:
                # New question
                match = re.match(r'- \*\*(\w+)\*\*: "([^"]+)"', line)
                if match:
                    qid, text = match.groups()
                    current_question = qid
                    sections["ask"][qid] = {"question": text}
            elif current_question and line.startswith('- '):
                # Question attribute
                attr = parse_question_attribute(line[2:])
                if attr:
                    key, value = attr
                    sections["ask"][current_question][key] = value
        
        # Parse execute section
        if current_section == "execute" and line and line[0].isdigit():
            sections["execute"].append(parse_execute_line(line))
        
        # Parse save section
        if current_section == "save" and line.startswith('Save answers to'):
            sections["save"] = line.replace('Save answers to', '').strip()
    
    return sections


def parse_detect_line(line: str) -> Optional[Dict]:
    """Parse a detect line like: If file X exists, set VAR = value"""
    # Pattern: If file X exists, set VAR = value
    match = re.match(r'If file (\S+) exists, set (\w+) = (.+)', line, re.IGNORECASE)
    if match:
        return {
            "type": "file_exists",
            "file": match.group(1),
            "var": match.group(2),
            "value": match.group(3).strip()
        }
    
    # Pattern: Else ask "Question?" → store in VAR → save to file
    match = re.match(r'Else ask "([^"]+)".*store in (\w+)', line, re.IGNORECASE)
    if match:
        return {
            "type": "ask",
            "question": match.group(1),
            "var": match.group(2)
        }
    
    return None


def parse_question_attribute(line: str) -> Optional[Tuple[str, Any]]:
    """Parse a question attribute like: Default: value"""
    if line.startswith('Default:'):
        return ('default', line[8:].strip())
    elif line.startswith('Type:'):
        return ('type', line[5:].strip())
    elif line.startswith('Options:'):
        opts = line[8:].strip().strip('[]').split(',')
        return ('options', [o.strip() for o in opts])
    elif line.startswith('Validate:'):
        return ('validate', line[9:].strip())
    elif line.startswith('Store:'):
        return ('store', line[6:].strip())
    return None


def parse_execute_line(line: str) -> Dict:
    """Parse an execute line."""
    # Remove leading number and dot
    line = re.sub(r'^\d+\.\s*', '', line)
    
    # Check for condition
    if line.lower().startswith('if '):
        match = re.match(r'If (\w+) == "([^"]+)": (.+)', line, re.IGNORECASE)
        if match:
            return {
                "type": "conditional",
                "condition_var": match.group(1),
                "condition_value": match.group(2),
                "command": match.group(3).strip()
            }
    
    # Check for loop
    match = re.match(r'For each \$\{(\w+)\} in \$\{(\w+)\}: (.+)', line, re.IGNORECASE)
    if match:
        return {
            "type": "loop",
            "item_var": match.group(1),
            "list_var": match.group(2),
            "command": match.group(3).strip()
        }
    
    # Regular command
    return {"type": "command", "command": line}


def load_answers(path: str) -> Dict[str, Any]:
    """Load saved answers from JSON file."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_answers(path: str, answers: Dict[str, Any]):
    """Save answers to JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(answers, f, indent=2)


def substitute_variables(text: str, variables: Dict[str, Any]) -> str:
    """Substitute ${var} placeholders in text."""
    def replace(match):
        var_name = match.group(1)
        value = variables.get(var_name, match.group(0))
        return str(value)
    
    return re.sub(r'\$\{(\w+)\}', replace, text)


def detect_version_from_project(project_dir: str = ".") -> Tuple[str, str]:
    """Auto-detect package manager and current version from project files."""
    project_path = Path(project_dir)
    
    # Check package.json
    package_json = project_path / "package.json"
    if package_json.exists():
        import json
        with open(package_json) as f:
            data = json.load(f)
            version = data.get("version", "0.0.0")
            return ("npm", version)
    
    # Check pyproject.toml
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        # Simple regex extraction
        content = pyproject.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return ("python", match.group(1))
    
    # Check Cargo.toml
    cargo = project_path / "Cargo.toml"
    if cargo.exists():
        content = cargo.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return ("cargo", match.group(1))
    
    return ("unknown", "0.0.0")


def bump_version(version: str, bump_type: str = "patch") -> str:
    """Bump a semantic version string."""
    parts = version.split('.')
    if len(parts) < 2:
        return version
    
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        
        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
    except ValueError:
        return version


def run_detect_phase(detect_items: List[Dict], project_dir: str = ".") -> Dict[str, Any]:
    """Run the detect phase and return detected variables."""
    variables = {}
    
    for item in detect_items:
        if item["type"] == "file_exists":
            filepath = Path(project_dir) / item["file"]
            if filepath.exists():
                # Parse value (handle ${var} in detect too)
                value = item["value"]
                if value.startswith('${') and value.endswith('}'):
                    # Special variable substitution for project detection
                    var_name = value[2:-1]
                    if var_name == "detect_version()":
                        _, current_ver = detect_version_from_project(project_dir)
                        variables[item["var"]] = current_ver
                    elif var_name == "bump_patch":
                        _, current_ver = detect_version_from_project(project_dir)
                        variables[item["var"]] = bump_version(current_ver, "patch")
                    else:
                        variables[item["var"]] = value
                else:
                    variables[item["var"]] = value
        elif item["type"] == "ask":
            # This will be handled in ask phase
            pass
    
    return variables


def run_ask_phase(questions: Dict[str, Any], existing_answers: Dict[str, Any], 
                  variables: Dict[str, Any]) -> Dict[str, Any]:
    """Run the ask phase and return new answers."""
    answers = existing_answers.copy()
    
    for qid, qinfo in questions.items():
        if qid in answers:
            # Use cached answer
            variables[qid] = answers[qid]
            continue
        
        # Substitute variables in question
        question_text = substitute_variables(qinfo["question"], variables)
        
        # Get default value
        default = qinfo.get("default", "")
        default = substitute_variables(default, variables)
        
        # Handle type
        qtype = qinfo.get("type", "string")
        
        if qtype == "confirm":
            default_bool = default.lower() in ["yes", "true", "y"]
            prompt = f"{question_text} [{'Y/n' if default_bool else 'y/N'}]: "
            response = input(prompt).strip().lower()
            if not response:
                response = "yes" if default_bool else "no"
            answer = response in ["yes", "y", "true"]
        elif qtype == "select":
            options = qinfo.get("options", [])
            print(f"{question_text}")
            for i, opt in enumerate(options, 1):
                marker = "*" if opt == default else " "
                print(f"  [{marker}] {i}. {opt}")
            response = input(f"Select [1-{len(options)}] (default: {default}): ").strip()
            if not response:
                answer = default
            else:
                try:
                    idx = int(response) - 1
                    answer = options[idx] if 0 <= idx < len(options) else default
                except (ValueError, IndexError):
                    answer = default
        else:
            # String type
            prompt = f"{question_text} [{default}]: "
            response = input(prompt).strip()
            answer = response if response else default
        
        answers[qid] = answer
        variables[qid] = answer
    
    return answers


def run_execute_phase(commands: List[Dict], variables: Dict[str, Any], 
                     verbose: bool = False, guard: Optional[str] = None):
    """Execute commands with variable substitution."""
    for cmd in commands:
        if cmd["type"] == "conditional":
            var_value = variables.get(cmd["condition_var"], "")
            if str(var_value) != str(cmd["condition_value"]):
                if verbose:
                    print(f"Skipping (condition {cmd['condition_var']} != {cmd['condition_value']})")
                continue
            command = substitute_variables(cmd["command"], variables)
        elif cmd["type"] == "loop":
            list_var = cmd["list_var"]
            items = variables.get(list_var, [])
            if not isinstance(items, list):
                items = [items]
            for item in items:
                loop_vars = variables.copy()
                loop_vars[cmd["item_var"]] = item
                command = substitute_variables(cmd["command"], loop_vars)
                execute_command(command, verbose, guard)
            continue
        else:
            command = substitute_variables(cmd["command"], variables)
        
        execute_command(command, verbose, guard)


def execute_command(command: str, verbose: bool = False, guard: Optional[str] = None):
    """Execute a single command."""
    print(f"$ {command}")
    
    if guard:
        # Import guard functions from cli
        from haberdash.cli import run_docker, run_chroot
        
        # Parse guard string (format: "docker" or "docker:image" or "chroot:path")
        if guard.startswith("docker:"):
            image = guard[7:]
            run_docker(image, ".", command, verbose=verbose)
        elif guard == "docker":
            run_docker("alpine:latest", ".", command, verbose=verbose)
        elif guard.startswith("chroot:"):
            chroot_path = guard[7:]
            run_chroot(chroot_path, command, verbose=verbose)
        elif guard == "chroot":
            run_chroot("/tmp/haberdash-chroot", command, verbose=verbose)
        else:
            subprocess.run(command, shell=True, check=True)
    else:
        subprocess.run(command, shell=True, check=True)


def get_macro_path(macro_name: str, project_dir: str = ".") -> Optional[Path]:
    """Get the path to a macro file by name."""
    # Macros are always stored in the user's config directory
    path = Path.home() / ".config" / "haberdash" / "macros" / f"{macro_name}.md"
    return path if path.exists() else None


def list_macros(project_dir: str = ".") -> List[Dict[str, str]]:
    """List all available macros with their descriptions."""
    macros = []
    
    directory = Path.home() / ".config" / "haberdash" / "macros"
    if not directory.exists():
        return []
            
    for path in directory.glob("*.md"):
        name = path.stem
        try:
            with open(path) as f:
                content = f.read()
                macro_data = parse_markdown_macro(content)
                macros.append({
                    "name": name,
                    "description": macro_data.get("description", "No description provided"),
                    "path": str(path),
                    "location": "user"
                })
        except Exception:
            # Skip invalid macros
            continue
                
    return sorted(macros, key=lambda x: x["name"])


def delete_macro(macro_name: str, project_dir: str = ".") -> bool:
    """Delete a macro by name."""
    path = get_macro_path(macro_name, project_dir)
    if path and path.exists():
        path.unlink()
        return True
    return False


def load_macro(macro_name: str, project_dir: str = ".") -> Optional[Tuple[Dict, str]]:
    """Load a macro from project or user config."""
    path = get_macro_path(macro_name, project_dir)
    
    if path:
        with open(path) as f:
            content = f.read()
            return parse_markdown_macro(content), str(path)
    
    return None


def run_macro(macro_name: str, verbose: bool = False, guard: Optional[str] = None,
              project_dir: str = ".") -> bool:
    """Run a named macro."""
    result = load_macro(macro_name, project_dir)
    
    if result is None:
        print(f"Macro '{macro_name}' not found.")
        print(f"Create it at ~/.config/haberdash/macros/{macro_name}.md")
        return False
    
    macro, path = result
    
    if not macro:
        print(f"Macro '{macro_name}' not found.")
        print(f"Create it at ~/.config/haberdash/macros/{macro_name}.md")
        return False
    
    print(f"Running macro: {macro['name']}")
    print(f"{macro['description']}")
    if verbose:
        print(f"Loaded from: {path}")
    print()
    
    # Determine where to save answers - use user config with project isolation
    project_slug = Path(project_dir).resolve().name
    save_dir = Path.home() / ".config" / "haberdash" / "answers" / project_slug
    
    macro_save = macro.get("save")
    if macro_save and not Path(macro_save).is_absolute():
        # If it was a relative path (like .haby/foo.json), we redirect it
        save_filename = Path(macro_save).name
        save_path = str(save_dir / save_filename)
    else:
        save_path = str(save_dir / f"{macro_name}.json")
    
    # Load existing answers
    existing_answers = load_answers(save_path)
    
    # Run detect phase
    variables = run_detect_phase(macro.get("detect", []), project_dir)
    variables.update(existing_answers)
    
    # Run ask phase
    if macro.get("ask"):
        answers = run_ask_phase(macro["ask"], existing_answers, variables)
    else:
        answers = {}
    
    # Merge new answers
    existing_answers.update(answers)
    
    # Run execute phase
    if macro.get("execute"):
        run_execute_phase(macro["execute"], variables, verbose, guard)
    
    # Save answers
    save_answers(save_path, existing_answers)
    print(f"\nAnswers saved to: {save_path}")
    
    return True


def save_recorded_macro(macro_name: str, transcript: str, commands: List[str], 
                        analysis: Dict[str, Any], project_dir: str = ".") -> str:
    """Convert a recorded macro session into a markdown macro file."""
    
    # Extract task info
    task_summary = analysis.get("task_summary", macro_name)
    explanation = analysis.get("explanation", "")
    completion_cmds = analysis.get("completion_commands", [])
    
    # Build markdown content
    lines = [
        f"# {macro_name.title()}",
        "",
        task_summary,
        "",
        "## Detect",
        "- Ask user for any needed context",
        "",
        "## Ask",
    ]
    
    # Add questions based on what we detected
    lines.append(f"- **confirm**: \"{task_summary}, proceed?\"")
    lines.append("  - Type: confirm")
    lines.append("  - Default: yes")
    
    # Add a question for any variables we can infer
    lines.append("- **working_dir**: \"Working directory?\"")
    lines.append("  - Default: .")
    
    lines.extend([
        "",
        "## Execute",
    ])
    
    # Add completion commands
    for i, cmd in enumerate(completion_cmds, 1):
        lines.append(f"{i}. {cmd}")
    
    lines.extend([
        "",
        "## Save",
        "Save answers to {}.json".format(macro_name),
    ])
    
    content = '\n'.join(lines)
    
    # Save to user location
    save_dir = Path.home() / ".config" / "haberdash" / "macros"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{macro_name}.md"
    
    with open(save_path, 'w') as f:
        f.write(content)
    
    return str(save_path)
