# CrewMate Voice

The speech engine shared by the CrewMate aircraft apps (A350, A310, MD11, …):

- **Sidecar** (`copilot_speech-x86_64-pc-windows-msvc.exe`): a .NET 10 console app that runs Windows SAPI speech recognition against the aircraft's grammar and writes one JSON object per line to stdout. The Tauri app starts it as its `copilot_speech` sidecar.
- **Trainer** (`CrewMate-SpeechTrainer.exe`): a .NET Framework 4.7.2 WinForms tool that trains the user's Windows speech profile on the aircraft's phrases.

This repo holds no aircraft data. Each aircraft repo keeps its own `grammar.xml` and `training_phrases.txt` and ships them next to these binaries.

This is a build-time dependency, not a product. It has no installer, no updater and no user-facing releases.

## How aircraft repos use it

Each aircraft repo pins an engine version in `voice.version` (for example `1.0.0`). Its `Scripts/fetch-voice.ps1` downloads that tag's release assets, checks them against `SHA256SUMS`, and copies them into `src-tauri/bin/` and `src-tauri/Trainer/`. Moving to a newer engine is that app's own decision, made by editing `voice.version` in one of its releases.

**Tags and their release assets are never deleted or replaced**, because aircraft repos build from them. A fix gets a new tag.

## Building

Requires the .NET 10 SDK.

```powershell
./Scripts/build.ps1          # dist/ with both exes and SHA256SUMS, version 0.0.0-dev
```

To try a local build in an aircraft app, set `CREWMATE_VOICE_DIST` to this repo's `dist/` folder before starting the app (`npm run tauri dev`). Its `fetch-voice.ps1` then deploys that build instead of the pinned release, with a warning. Unset it to go back to the pinned version.

## Releasing

1. Add the version to `CHANGELOG.md`.
2. Push a `vX.Y.Z` tag. CI builds both projects with that version and publishes a release with the two exes and `SHA256SUMS`.

## Sidecar contract

### Arguments

```
copilot_speech.exe <grammar.xml path> [input device name]
```

The grammar path defaults to `grammar.xml` next to the exe. An empty device name or `default` uses the system default input; a name that matches no device falls back to the default with a `warning` status.

### stdin

One JSON object per line; unknown or malformed lines are ignored.

| Message | Effect |
|---|---|
| `{"confidenceThreshold": 0.85}` | Results below this confidence become `speech_unrecognized` (default 0.85, clamped to 0–1) |
| `{"muted": true}` | Recognition results are dropped while muted |

### stdout

One JSON object per line, always with a `type`.

| `type` | Fields | Meaning |
|---|---|---|
| `status` | `status`, optional `details` | `starting` (first with `details.engineVersion` and `details.protocol`, then with the recognizer), `ready`, `warning` |
| `error` | `message` | Fatal setup problem (no recognizer, no input device, missing grammar); the process usually exits |
| `inputDevices` | `devices[]` of `{index, name, isDefault}` | Available input devices, sent once after start |
| `speech` | `commandType`, optional `payload`, `text`, `confidence` | A recognised command, see below |
| `speech_unrecognized` | `text` | Heard, but below the confidence threshold |
| `rejected` | `text`, `confidence`, `reason` | Matched the grammar but produced no command. Only in debug builds, except `numeric_discrete_id`, which is always sent |

`protocol` is `1`. It changes only when a change to this contract would break an existing app.

### Grammar contract

The grammar is SRGS XML with `tag-format="semantics/1.0"` and a public root rule. Every match must set `out.ActionRuleId` and `out.CmdId`, and may set `out.CmdValue`:

| `ActionRuleId` | `CmdId` | `CmdValue` | `commandType` sent |
|---|---|---|---|
| `DISCRETE_COMMANDS` | A snake_case command name, e.g. `brake_fan_on` | – | `discrete`, payload `{ "command": "<CmdId>" }` |
| `FO_COMMANDS` | A number that picks a parser (below) | The spoken value | See below |
| `FMA_CALLOUTS` | – | `thrust\|vertical\|lateral\|combined\|approachCat\|armed\|urgent` | `fma_callout`, payload with the non-empty parts |

A numeric `CmdId` from `DISCRETE_COMMANDS` means an old grammar that still used numeric ids; the sidecar rejects it with reason `numeric_discrete_id`. Adding a discrete command only needs a grammar item and a handler in the app; the engine passes any snake_case name through.

`FO_COMMANDS` ids:

| `CmdId` | `commandType` | `CmdValue` |
|---|---|---|
| 1 | `heading` | 0–359 |
| 2 | `altitude` (flight level) | 10–450 |
| 3 | `altitude` (feet) | 100–60000 |
| 4 | `speed` | 60–400 |
| 7 | `altimeter` | hPa 900–1100, or inHg ×100 (2700–3100) |
| 8–13 | `fuel` | `thousands\|hundreds` for kg (8, 9) and lbs (10, 11); tons as `18.5` (12, 13); even ids unbalanced, odd ids balanced |
| 14, 15 | `takeoff_data` | `V1\|VR\|V2\|FLX or TOGA\|flexTemp` |
| 16 | `missed_approach_altitude` | – (auto) |
| 17, 18 | `missed_approach_altitude` | feet (17) or flight level (18) |
| 19, 20 | `minimums` | feet; baro (19) or radio (20) |
| 21 | `runway` | `identifier\|designator`, e.g. `09\|L` |

For `heading`, `altitude` and `speed`, the payload also carries `verb` (`set`, `pull` or `manage`, taken from the spoken words) and `text` is normalised (e.g. `pull heading 270`).

## Trainer contract

The trainer reads `training_phrases.txt` next to its exe. Blank lines and lines starting with `#` are skipped; every other line is one phrase read aloud during training.

Two optional directives at the top name the aircraft:

```
#! app: CrewMate A350
#! id: crewmatea350
```

`app` sets the window and training titles. `id` (lowercase letters, digits, `-` and `_`) sets the log folder under the user's app data. Without them the trainer uses `CrewMate` and `crewmate`.

## License

GPL-3.0, see [LICENSE](LICENSE).
