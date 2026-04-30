<p align="center">
   <img width="500" height="160" alt="haberdash_500" src="https://github.com/user-attachments/assets/9122b177-3542-4b68-8bcf-0e1dd55cb7fc" />
   <br/>
   <a href=https://pypi.org/project/haberdash><img src=https://badge.fury.io/py/haberdash.svg/></a>
   <br/>
 </p>

# Haberdash (`haby`)

Haberdash is a **runtime for agentic instructions**. 

The core insight of Haberdash is that **cloning a repository** and **running a macro** are fundamentally the same operation: applying agentic intent to a specific context (a README file or a live Shell session).

## Unified Instruction Runtime

Haberdash treats every task as an instruction set applied to context:

- **Static Instructions (Repo Mode):** Give `haby` a GitHub URL. It treats the README as the instruction set and the repository as the context to build and run the software.
- **Dynamic Instructions (Skill Mode):** Give `haby` a skill name. It treats the Markdown Macro as the instruction set and your live subshell session as the context to complete the task.

## Key Features

- **Agentic Automation:** Whether it's a README or a Macro, `haby` uses AI to determine the "next token" of commands needed for success.
- **Skill-Based Workflow:** Run `haby <skill>`, establish context in a subshell, and let AI finish the job.
- **Zero Workspace Clutter:** Internal state, macros, and project-isolated answers are stored in `~/.config/haberdash`.
- **Pre-flight Safety:** Connectivity checks protect your manual effort before you start working.
- **Guard Rails:** Optional `chroot` or `docker` isolation for all command execution.

## Installation

```bash
pip install haberdash
```

## Quick Start

### 1. Static Instructions: Run a Repo
`haby` clones the repo, analyzes the README, and executes the build/run plan.
```bash
haby https://github.com/user/repo
```

### 2. Dynamic Instructions: Apply a Skill
`haby` opens a subshell for you to provide live context, then completes the plan based on the skill manifest.
```bash
haby bisect
```

### 3. Manage Instructions
```bash
haby -l              # List available skills
haby config          # Edit your TOML configuration
```

## How Instructions are Structured

Instructions are defined in Markdown. Whether it's a README it's parsing on the fly or a local `.md` skill, the structure is the same:
- **Detection:** What environment variables or files are needed?
- **Interaction:** What context is missing from the user?
- **Execution:** What is the specific command sequence to achieve the goal?

## License

MIT
