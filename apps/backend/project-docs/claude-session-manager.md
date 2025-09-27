# Claude Session Manager

A lightweight session tracking tool for documenting your work with Claude Code in the Naga SIS project.

## Overview

The Claude Session Manager helps you keep track of what you accomplish during each development session. It creates timestamped markdown files that serve as a development journal, making it easy to:

- Track what was completed in each session
- Search across all sessions for specific work
- Maintain a development history
- Create notes for future reference

## Installation

1. The session manager script is located at:
   ```
   backend/scratchpad/claude-session-manager.sh
   ```

2. Make it executable:
   ```bash
   chmod +x backend/scratchpad/claude-session-manager.sh
   ```

3. Create an alias for convenience (add to ~/.bashrc or ~/.zshrc):
   ```bash
   alias claude-session='~/PycharmProjects/naga-monorepo/backend/scratchpad/claude-session-manager.sh'
   ```

4. Reload your shell configuration:
   ```bash
   source ~/.bashrc  # or source ~/.zshrc
   ```

## Storage Location

- Session data is stored in: `~/.claude/sessions/data/`
- Current session marker: `~/.claude/sessions/.current-session`
- Each session is saved as a markdown file with timestamp-based naming

## Commands

### `claude-session start [name]`
Start a new session with an optional descriptive name.

```bash
# Auto-generated name
claude-session start

# Custom name
claude-session start "Implementing payment reconciliation"
```

### `claude-session update [note]`
Add a timestamped note to the current session.

```bash
claude-session update "Fixed circular dependency in finance app"
claude-session update "Added StaffProfile to fixture generation"
```

### `claude-session current`
Display information about the current active session.

```bash
claude-session current
```

### `claude-session end`
End the current session and save it.

```bash
claude-session end
```

### `claude-session list`
List all sessions with their status (active/completed).

```bash
claude-session list
```

### `claude-session show [id/name]`
Display the full content of a specific session.

```bash
claude-session show 20250802_140532
```

### `claude-session search [term]`
Search across all sessions for a specific term.

```bash
claude-session search "database migration"
claude-session search "fixture"
```

### `claude-session help`
Display help information.

```bash
claude-session help
```

## Typical Workflow

1. **Start your day**
   ```bash
   claude-session start "Working on student enrollment features"
   ```

2. **Document as you work**
   ```bash
   claude-session update "Created new API endpoint for bulk enrollment"
   claude-session update "Fixed validation bug in enrollment form"
   claude-session update "Added test cases for enrollment edge cases"
   ```

3. **Review progress**
   ```bash
   claude-session current
   ```

4. **End your session**
   ```bash
   claude-session end
   ```

5. **Later: Review past work**
   ```bash
   # See all sessions
   claude-session list
   
   # Search for specific work
   claude-session search "enrollment"
   
   # Review a specific session
   claude-session show 20250802_143021
   ```

## Session File Format

Sessions are stored as markdown files with the following structure:

```markdown
# Claude Session: [Session Name]
**Started:** 2025-08-02 14:30:21  
**ID:** 20250802_143021  
**Project:** naga-monorepo  
**Directory:** /Users/username/PycharmProjects/naga-monorepo/backend  

## Session Notes

### Session Start
- Started new session: Working on student enrollment features
- Working directory: /Users/username/PycharmProjects/naga-monorepo/backend

### 2025-08-02 14:35:42
Created new API endpoint for bulk enrollment

### 2025-08-02 15:10:33
Fixed validation bug in enrollment form

### 2025-08-02 16:22:18
Added test cases for enrollment edge cases

---
**Ended:** 2025-08-02 17:00:45
```

## Benefits

1. **Development History**: Maintain a searchable log of all development activities
2. **Knowledge Transfer**: Easy to share session notes with team members
3. **Progress Tracking**: Track what was accomplished in each session
4. **Debugging Aid**: Quickly find when specific changes were made
5. **Personal Notes**: Keep track of ideas, TODOs, and observations

## Tips

- Use descriptive session names that indicate the main focus
- Add notes immediately after completing significant tasks
- Include error messages or important findings in your notes
- Use the search function to find when you worked on specific features
- Review previous sessions before starting related work

## Integration with Git

Consider adding session references to your git commits:

```bash
# In your commit message
git commit -m "feat(enrollment): Add bulk enrollment API

Session: 20250802_143021
- Created new endpoint for processing multiple enrollments
- Added validation for course capacity
- Implemented transaction rollback on errors"
```

## Troubleshooting

- If a session appears stuck, check for `.current-session` file in `~/.claude/sessions/`
- Sessions are plain text markdown files - you can edit them directly if needed
- To manually end a stuck session, simply delete the `.current-session` file

---

*Note: This tool is designed for personal development tracking and should not contain sensitive information like passwords or API keys.*