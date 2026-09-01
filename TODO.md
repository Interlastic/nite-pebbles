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
     
- [ ] **add /serverinfo command**
  - Scope: Fetch guild metadata via REST API with counts enabled (withCounts: true to retrieve approximateMemberCount and approximatePresenceCount without caching/chunking members) and display an embed containing: Server Name, Server ID, Server Owner mention/ID, Creation Date (formatted with Discord timestamps <t:timestamp:F> and <t:timestamp:R>), Total Member Count, Online Member Count, Channel Counts (categorized into text, voice, category, stage/forum), Role Count, Boost Status (Tier 0–3 and total boosts), Emoji Count (split into static vs. animated) and Sticker Count, Visual Assets (Avatar/Icon, Banner, Splash, Discovery Splash URLs if set), Moderation Settings (Verification Level, Explicit Content Filter), and Community Features (Server Description and Vanity URL if applicable).
  - Style: When the command is run, the bot will show a non-ephemeral message containing basic info: Server Name (with <:cobo:1493663694289371360> to the left of the name if the server is a boosted community server, <:cono:1493663579700989972> if the server is a non-boosted community server and <:dc:1493663575548362842> else), Server Icon, Server ID (small, <:ID:1493663589246963812> to the left of it), Member Count/Online count (<:uad:1493663591239254046> to the left of it), the boost tier + count (with <:cobo:1493663694289371360> to the left of it). Underneath all of this info, seperated by a seperator, there are buttons for more info (like Images etc. Seperate the info available cleanly. the submenus open as different messages and have a back option that deletes the emssage.)
  - Errors: Any info unavailable should just not be shown. 
  - Target files: `nite-pebbles/pebbles.json`, `nite-pebbles/locales/*-json`, `nite-pebbles/serverinfo.py`     
  - Tests: Verify the serverinfo flow and fallbacks and localization. run the tests in the repo.

## Bugs
