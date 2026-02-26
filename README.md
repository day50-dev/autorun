<p align="center">
   <img src="https://github.com/user-attachments/assets/575fd0a0-18e5-4b24-8077-4790bcd1bbbc">
  </p>

A runtime for AI agents to execute software with security policies.

## What Is This?

Haberdash is a CLI tool for AI agents to automatically clone, build, and run software from GitHub while enforcing configurable security policies.

## Why Do I Want This?

AI agents need to execute external tools and libraries to complete tasks. Haberdash provides a controlled runtime that:
- Automatically resolves and installs dependencies
- Sandboxes execution within configurable policies
- Caches builds for efficiency

## How Do I Use It?

**Install:**
```bash
uvx install haberdash
```

**Configure:**
```bash
haby <github-url>
```
First run prompts for OpenAI-compatible API settings.

**Run via CLI:**
```bash
haby https://github.com/user/repo
```


## License

MIT
