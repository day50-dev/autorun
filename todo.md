# Autorun TODO

## Completed

- Project structure setup
- CLI implementation with argparse
- GitHub repository cloning
- README reading and AI analysis
- Configuration file management (~/.config/autorun)
- Interactive config prompting on first run
- Dependency installation (pip, npm, make, etc.)
- Project running
- Directory structure reorganization:
  - $HOME/autorun/pkgs/ - cloned repositories
  - $HOME/autorun/bin/ - executables
  - $HOME/autorun/lib/ - libraries
  - $HOME/autorun/include/ - headers
- Auto-fix feature: On run failure, asks AI for fixes (up to 3 tries)
- Error handling for HTML responses from API
- Verbose mode for debugging
- --no-install flag option
- README documentation updates
- setup.py for packaging
- .gitignore

## Known Issues

- sudo apt-get install commands fail without password prompt in subprocess
   - Need to pre-install system dependencies separately
- AI prompts may need refinement for better error detection
- No cleanup of failed build artifacts

## Future Enhancements

- Better error messages for missing system dependencies
- Check for sudo available before attempting apt-get
- Add command to copy built binaries to $HOME/runthis/bin/
- Cache AI responses for common project types
- Support for more package managers (conda, cargo, go get, etc.)
- Add --dry-run flag to show what would be done
- Add --clean flag to remove cloned repos
- Add list command to show installed packages
- Better handling of non-zero exit codes that are actually expected
- Add tests