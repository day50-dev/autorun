<p align="center">
   <img width="500" height="160" alt="haberdash_500" src="https://github.com/user-attachments/assets/9122b177-3542-4b68-8bcf-0e1dd55cb7fc" />
   <br/>
   <a href=https://pypi.org/project/haberdash><img src=https://badge.fury.io/py/haberdash.svg/></a>
   <br/>
 </p>

# Haberdash (`haby`)

Haberdash is an AI-driven shell assistant that treats automation as **Skills**. Instead of rigid scripts, Haberdash uses Markdown-based macros that observe your context in a subshell and use AI to complete the task.

## Key Features

- **Skill Mode:** Run `haby <skill>`, establish context in a subshell (e.g., `git log`, `npm test`), and let AI determine the "next token" of commands to finish the job.
- **Markdown Macros:** Define automation logic in simple Markdown files.
- **Zero Workspace Clutter:** All configuration, macros, and project-isolated state are stored in `~/.config/haberdash`.
- **Pre-flight Checks:** Verifies AI connectivity *before* you start working to protect your manual effort.
- **Isolated Execution:** Optional `chroot` or `docker` guards for safe command execution.

## Installation

```bash
pip install haberdash
```

## Quick Start

### 1. Configure
On first run, `haby` will prompt for your OpenAI-compatible API settings (works great with local models like Ollama/llama.cpp).
```bash
haby config  # Open config.toml in your editor anytime
```

### 2. List & Manage Skills
```bash
haby -l              # List available skills
haby --show bisect   # View skill details and logic
haby --edit bisect   # Edit the skill's markdown manifest
```

### 3. Run a Skill
Apply a skill to your current workspace:
```bash
haby bisect
```
1. A subshell opens.
2. Perform your preparation (e.g., `git bisect start`, find a good commit).
3. `exit` the subshell.
4. AI analyzes your session and the `bisect` skill to suggest the completion commands.

## How Skills Work

Skills are defined as Markdown files in `~/.config/haberdash/macros/`. They include:
- **Detection:** Automatic variable setting based on files or previous answers.
- **Questions:** Interactive prompts for missing context.
- **Execution:** Conditional or looped shell commands.

Example `bisect.md`:
```markdown
# Bisect
Find the commit that introduced a bug.

## Ask
- **test_cmd**: "What command runs the failing test?"
  - Default: npm test

## Execute
1. git bisect run ${test_cmd}
2. git bisect reset
```

## License

MIT
