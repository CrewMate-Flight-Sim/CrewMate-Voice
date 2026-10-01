# Changelog

## 1.1.0

- Heading, speed and altitude commands spoken with "select" now send `verb: "select"` and the text `select heading 270`; before, "select" was dropped and the command looked like a plain set - @marxio09dio

## 1.0.0

- First release, built from the engine that shipped in CrewMate A350 1.0.1 plus the grammar command names - @marxio09dio
- The sidecar reports its version and protocol in the first `starting` status line - @marxio09dio
- The trainer takes its title and log folder from `#! app:` and `#! id:` lines in `training_phrases.txt` instead of a hardcoded A350 name - @marxio09dio
