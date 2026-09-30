# Contributing to CrewMate Voice

This repo is the speech engine shared by the CrewMate aircraft apps. Aircraft data (grammar, training phrases) and everything the app does with a command live in each aircraft repo, not here. Read the [README](README.md) first: it describes the stdout protocol and the grammar contract that every change here must keep.

## Setup

- Windows 10 or 11 with the English (United States) speech recognizer installed.
- .NET 10 SDK. It builds both projects; the trainer targets .NET Framework 4.7.2 and gets its reference assemblies from NuGet.
- An aircraft repo cloned next to this one (for example `..\CrewMateA350`) to test changes in a real app.

```powershell
git clone https://github.com/CrewMate-Flight-Sim/CrewMate-Voice.git
cd CrewMate-Voice
dotnet tool restore            # csharpier, the C# formatter
./Scripts/build.ps1            # dist/ with both exes and SHA256SUMS, version 0.0.0-dev
```

## Making a change

1. Branch from `main`.
2. Make the change in `Sidecar/` or `Trainer/`. Keep aircraft names, ids and phrases out of the code: anything aircraft-specific comes from the grammar, the phrase file or a command-line argument.
3. Format: `dotnet csharpier format .`
4. Build: `./Scripts/build.ps1`
5. Test it in an aircraft app:
   ```powershell
   $env:CREWMATE_VOICE_DIST = "C:\Dev\CrewMate\CrewMate-Voice\dist"
   cd ..\CrewMateA350
   npm run tauri dev
   ```
   The app's `fetch-voice.ps1` warns that it is using the local build and deploys it instead of the pinned release. Speak a few commands and check the app log. Remove the variable afterwards (`Remove-Item Env:CREWMATE_VOICE_DIST`); the next `npm run tauri dev` goes back to the pinned version.
6. Open a PR. CI checks the formatting (`dotnet csharpier check .`) and builds both projects on every PR.

### Compatibility rules

- Aircraft apps pin an exact engine version and upgrade on their own schedule, so a release must never break an app that moves to it without changing anything else, unless it is a major version.
- Adding a field to a stdout message, a new message type, or a new `FO_COMMANDS` parser is a minor version.
- Removing or renaming a field, changing what an existing grammar produces, or changing the arguments is a major version, and also bumps `PROTOCOL` in `Sidecar/Program.cs` when it touches the stdout JSON or the grammar contract. Update the README contract in the same PR.
- Every log or status line the apps show keeps its existing wording, because users search for it.

## Releasing a new engine version

1. Merge the changes to `main`.
2. Add a section for the new version at the top of `CHANGELOG.md`, one line per change, from the app developer's point of view. Commit it to `main`.
3. Tag and push:
   ```powershell
   git switch main
   git pull
   git tag v1.1.0
   git push origin v1.1.0
   ```
4. The `build` workflow builds both projects with that version and creates the GitHub release with `copilot_speech-x86_64-pc-windows-msvc.exe`, `CrewMate-SpeechTrainer.exe` and `SHA256SUMS`. Check that the run is green and the release has all three files.
5. **Never delete, move or re-push a tag, and never replace a release asset.** Apps download by tag and verify the hashes; a changed asset breaks every build pinned to it. If a release is wrong, fix it in a new version.
6. Each aircraft app adopts the new version in its own repo when it is ready (see that repo's Contributing guide): bump `voice.version`, run `npm run voice:fetch`, test, and ship it in one of that app's releases.

## Tools

- `Tools/convert-grammar-ids.py` converts an aircraft grammar from numeric `DISCRETE_COMMANDS` ids to command names, the change every app makes before it can use this engine. Run it from the aircraft repo root while `CopilotSpeechNew/` still exists; its header explains the options.

## License

By contributing you agree that your contributions are licensed under GPL-3.0.
