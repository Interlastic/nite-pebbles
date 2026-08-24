# Project Backlog

## Features
- [x] **Number Guessing Minigame (`/guess`)**
  - Scope: A simple, interactive minigame where the bot picks a secret number (e.g. 1–100) and players try to guess it with higher/lower feedback, attempt counters, and optional user stat tracking.
  - Target files: `nite-pebbles/fun_commands.py`, `nite-pebbles/locales/*.json`
  - Tests: Verify game flow, higher/lower feedback accuracy, timeout handling, and localization.

- [x] **Add max and attempts arguments to /guess**
  - Scope: Max: replaces 100 with the argument for a game with more diversity. Attempts: Replaces the attempt count (7) to anything, to make the game harder or easier.
  - Target files: `nite-pebbles/fun_commands.py`, `nite-pebbles/locales/*.json`
  - Tests: Verify the game flow, errors. Run the tests included in this repository.

## Bugs
