# bisect

Find the commit that introduced a bug using git bisect.

## Detect

- Ask "What's the bad commit (where the bug exists)?" → store in bad_commit → save to .haby/bisect.json
- Ask "What's the good commit (before the bug)?" → store in good_commit → save to .haby/bisect.json
- Ask "What's the test command to run?" → store in test_command → save to .haby/bisect.json

## Ask

- **bad_commit**: "Bad commit (where bug exists)"
  - Default: HEAD
  - Store: .haby/bisect.json

- **good_commit**: "Good commit (before bug)"
  - Default: 
  - Store: .haby/bisect.json

- **test_command**: "Test command to run"
  - Default: make test
  - Store: .haby/bisect.json

- **auto_run**: "Automatically run bisect?"
  - Type: confirm
  - Default: yes
  - Store: .haby/bisect.json

## Execute

1. "git bisect start"
2. "git bisect bad ${bad_commit}"
3. "git bisect good ${good_commit}"
4. "git bisect run ${test_command}"

## Save

Save answers to .haby/bisect.json