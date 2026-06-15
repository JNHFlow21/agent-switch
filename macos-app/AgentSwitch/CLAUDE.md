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
    │   ├── Tokens/DSTokens.swift      # DSColor, DSTypography, DSSpacing, DSRadius, DSDepth
    │   └── Components/DSComponents.swift  # DSCard, DSBadge, DSMetricCard
    ├── Navigation/SidebarView.swift   # Sidebar enum + view
    ├── Models/AgentModels.swift       # Codable models mirroring Python data
    ├── Services/
    │   ├── AgentSwitchService.swift   # Actor bridging to Python CLI
    │   └── AppState.swift             # @MainActor observable root state
    └── Features/
        ├── Dashboard/DashboardView.swift
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

## Design System

- All views consume `DSColor`, `DSTypography`, `DSSpacing`, `DSRadius` tokens.
- No raw color literals in feature views.
- Reusable product components: `DSCard`, `DSBadge`, `DSMetricCard`.

## Platform

- macOS 14.0+ (Sonoma)
- Swift 5.9+
- SwiftUI with NavigationSplitView sidebar
- No third-party dependencies

## Backend Contract

The app calls `python3 -m agent_switch doctor --json --no-ccswitch` (with `PYTHONPATH` set to `src/`) and decodes the resulting JSON into `DoctorReport`. Reconcile calls `reconcile --json --no-ccswitch`.

Tool definitions and access routes are loaded from `~/.config/agent-switch/config.json` into `ConfigInfo`. Feature views must render MCP tools, target apps, commands, route ids, and required secret names from `ConfigInfo`, not from hardcoded defaults. `DoctorReport.secrets` is used only for runtime status such as present and missing secret names.
