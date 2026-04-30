# release

Create a new release with version bump, changelog, and git tag.

## Detect

- If file package.json exists, set package_manager = npm and current_version = ${detect_version()}
- If file pyproject.toml exists, set package_manager = python and current_version = ${detect_version()}
- If file Cargo.toml exists, set package_manager = cargo and current_version = ${detect_version()}
- Else ask "What's your package manager?" → store in package_manager → save to .haby/release.json

## Ask

- **version**: "What version?"
  - Default: ${bump_patch(current_version)}
  - Validate: semver
  - Store: .haby/release.json

- **release_type**: "Release type?"
  - Type: select
  - Options: [patch, minor, major]
  - Default: patch
  - Store: .haby/release.json

- **create_gh_release**: "Create GitHub release?"
  - Type: confirm
  - Default: yes
  - Store: .haby/release.json

- **bump_first**: "Bump version before committing?"
  - Type: confirm  
  - Default: yes
  - Store: .haby/release.json

## Execute

1. If ${bump_first} == yes: "npm version ${version} --no-git-tag-version"
2. "git add -A"
3. "git commit -m 'Release v${version}'"
4. "git tag -a v${version} -m 'Release v${version}'"
5. "git push origin main --tags"
6. If ${create_gh_release} == yes: "gh release create v${version} --generate-notes"

## Save

Save answers to .haby/release.json