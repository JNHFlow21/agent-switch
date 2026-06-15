// [INPUT]: SwiftUI, AppState, Navigation views
// [OUTPUT]: Root content view with sidebar navigation
// [POS]: Main navigation host; routes between feature views
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var selection: SidebarItem = .dashboard

    var body: some View {
        NavigationSplitView {
            SidebarView(selection: $selection)
        } detail: {
            switch selection {
            case .dashboard:
                DashboardView()
            case .tools:
                ToolsView()
            case .secrets:
                SecretsView()
            case .settings:
                SettingsView()
            }
        }
        .navigationSplitViewStyle(.balanced)
        .task {
            await appState.refresh()
        }
        .toolbar {
            ToolbarItemGroup {
                if appState.isLoading {
                    ProgressView()
                        .controlSize(.small)
                }
                Button {
                    Task { await appState.refresh() }
                } label: {
                    Label(L10n.refresh, systemImage: "arrow.clockwise")
                }

                Button {
                    Task { await appState.runReconcile() }
                } label: {
                    Label(L10n.reconcile, systemImage: "arrow.triangle.2.circlepath")
                }
            }
        }
    }
}
