# Agent Switch macOS App — CLAUDE.md

## Architecture

SwiftUI-first macOS 14+ application. Communicates with the Python `agent-switch` CLI backend via `Process` shell execution and JSON parsing.

## Directory Structure

```
macos-app/AgentSwitch/
├── Package.swift                      # SPM build manifest
├── AgentSwitch.xcodeproj/             # Xcode project (alternative build)
└── AgentSwitch/
    ├── AgentSwitchApp.swift           # App entry, Scene, menu commands
    ├── ContentView.swift              # Root NavigationSplitView
    ├── DesignSystem/
    │   ├── Tokens/DSTokens.swift      # Graphite palette, typography, spacing, radius
    │   └── Components/DSComponents.swift  # Flat cards, badges, metrics, icon/file buttons
    ├── Navigation/SidebarView.swift   # Sidebar enum + view
    ├── Models/AgentModels.swift       # Codable models mirroring Python data
    ├── Services/
    │   ├── AgentSwitchService.swift   # Actor bridging to Python CLI
    │   └── AppState.swift             # @MainActor observable root state
    └── Features/
        ├── Dashboard/DashboardView.swift
        ├── Agents/AgentsView.swift
        ├── CLIs/CLIsView.swift
        ├── Skills/SkillsView.swift
        ├── Tools/ToolsView.swift
        ├── Secrets/SecretsView.swift
        └── Settings/SettingsView.swift
```

## Build

```bash
cd macos-app/AgentSwitch
swift build
```

Or open `AgentSwitch.xcodeproj` in Xcode 15+.

Install the current Release build into the single canonical user location used
by the Dock entry:

```bash
./install.sh
```

The installer builds into temporary DerivedData, replaces
`~/Applications/Agent Switch.app`, refreshes Launch Services, and launches that
installed copy. Do not launch a DerivedData copy as the user-facing app.

## Design System

- All views consume `DSColor`, `DSTypography`, `DSSpacing`, `DSRadius` tokens.
- No raw color literals in feature views.
- Reusable product components: `DSCard`, `DSBadge`, `DSMetricCard`, `DSIconButton`, `DSPathRow`, `DSPathActions`.
- App chrome is achromatic: no status colors or card shadows; use graphite text, gray fills, icons, and hairline borders.

## Platform

- macOS 14.0+ (Sonoma)
- Swift 5.9+
- SwiftUI with NavigationSplitView sidebar
- No third-party dependencies

## Backend Contract

The app calls `python3 -m agent_switch doctor --json --no-ccswitch` (with `PYTHONPATH` set to `src/`) and decodes the resulting JSON into `DoctorReport`. Reconcile calls `reconcile --json --no-ccswitch`; supported-agent status calls `agents --json`; inventory uses `clis --json` and `skills --json`. Skill source updates call `skills update --json`, which delegates to Skill Hub `skillctl fetch` and never activates a Skill.

Secret writes use `secret set --stdin`. The eye-button reveal redirects `secret get --fd 3` into a private FIFO so secret bytes never use stdout, stderr, argv, the environment, or a regular temporary file. It intentionally does not invoke Touch ID or a system password dialog; visibility remains an explicit eye-button toggle. Secret deletion uses `secret delete NAME`.

Tool definitions and access routes are loaded from `~/.config/agent-switch/config.json` into `ConfigInfo`. Feature views must render MCP tools, target apps, commands, route ids, and required secret names from `ConfigInfo`, not from hardcoded defaults. `DoctorReport.secrets` is used only for runtime status such as present and missing secret names.
