<p align="center">
   <img width="500" height="160" alt="haberdash_500" src="https://github.com/user-attachments/assets/9122b177-3542-4b68-8bcf-0e1dd55cb7fc" />
   <br/>
   <a href=https://pypi.org/project/haberdash><img src=https://badge.fury.io/py/haberdash.svg/></a>
   <br/>
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
