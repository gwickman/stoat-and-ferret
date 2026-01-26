# Prompt Templates

Templates used by MCP server to construct Claude Code prompts for version execution.

## Available Templates

| Template | Used For |
|----------|----------|
| [feature-implementation.md](./feature-implementation.md) | Implementing a single feature |
| [theme-retrospective.md](./theme-retrospective.md) | Creating theme retrospective |
| [version-retrospective.md](./version-retrospective.md) | Creating version retrospective |

## Placeholder Format

Templates use `{{placeholder}}` syntax for values to be filled in:

- `{{version}}` - Version identifier (e.g., `v018`)
- `{{theme}}` - Theme identifier (e.g., `01-process-and-config`)
- `{{feature}}` - Feature identifier (e.g., `001-cli-timeout-config`)
- `{{theme_path}}` - Full path to theme directory
- `{{feature_path}}` - Full path to feature directory

## Usage

The MCP server reads these templates and fills in placeholders before passing to Claude Code.
