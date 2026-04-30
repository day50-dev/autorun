# Haberdash TODO

## Completed

- Pivot to **Macro Skill Mode**: `haby <skill>` opens a subshell for context.
- Modernized configuration with **TOML** (`~/.config/haberdash/config.toml`).
- Macro management CLI: `-l`, `--show`, `--edit`, `--delete`.
- Pre-flight AI connectivity checks to protect user effort.
- Isolated execution guards (`chroot`, `docker`).
- Project-isolated answer storage in `~/.config/haberdash/answers/`.
- Migrated all state out of the workspace (`.haby` removed).
- Updated README to reflect "Skills" philosophy.
- Support for local models (Ollama, llama.cpp) via optional API keys.

## Active Tasks

- [ ] Refine AI prompts for "next token" completion logic.
- [ ] Add `haby record <name>` to easily create new skill manifests from a session.
- [ ] Improve handling of multi-step execution logic in macros.

## Future Enhancements

- [ ] "Skill Discovery": Search for and download skills from a central registry.
- [ ] Better error recovery if a suggested completion command fails.
- [ ] Support for piped input into skills.
- [ ] Visual progress indicators for AI analysis.
- [ ] Comprehensive test suite for the new macro engine.
