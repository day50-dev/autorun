<p align="center">
   <img width="500" height="160" alt="haberdash_500" src="https://github.com/user-attachments/assets/9122b177-3542-4b68-8bcf-0e1dd55cb7fc" />
 </p>

Make an agent run software according to your personal security policies

## What It Does

```bash
haby <github-url>
```

That's it. Clones the repo, reads the README, figures out how to run it, installs deps, runs it.

## Install

```bash
uvx install haberdash
```

## Setup

Run `haby` once - it will prompt you to create `~/.config/haberdash`:

```ini
openai_base_url=https://api.openai.com/v1  # or your OpenAI-compatible API (e.g., https://openrouter.ai/api/v1)
model=gpt-4o
key=sk-your-api-key-here
cache_dir=$HOME/haberdash  # defaults to $HOME/haberdash
```

## Directory Structure

Haberdash creates the following directories in `~/.haberdash` (or your configured `cache_dir`):

- `~/.haberdash/pkgs/` - Where repositories are cloned
- `~/.haberdash/bin/` - Executables from builds
- `~/.haberdash/lib/` - Libraries
- `~/.haberdash/include/` - Header files

## Use

```bash
# Run any GitHub project
haby https://github.com/user/repo

# Want details?
haby --verbose https://github.com/user/repo

# Skip installing deps (if you're feeling lucky)
haby --no-install https://github.com/user/repo
```

## How It Works

1. Clones the repo to `~/.haberdash/pkgs/`
2. Sends README to AI: "How do I run this?"
3. Installs whatever it needs (pip, npm, make, etc.)
4. Runs what the AI says
5. If running fails, asks AI how to fix (up to 3 tries) and installs needed tools/libs

## Warning

This is v0.0.1. YOLO mode. No sandbox. No safety. It runs whatever the AI says to run. It will install system packages via apt-get. Don't run random shit you don't trust.

## License

MIT

---

**One command to run them all.**
