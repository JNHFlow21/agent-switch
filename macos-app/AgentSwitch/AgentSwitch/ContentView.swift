// [INPUT]: SwiftUI, AppState, Navigation views
// [OUTPUT]: Root content view with sidebar navigation
// [POS]: Main navigation host; routes between feature views
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var selection: SidebarItem = .dashboard
    @State private var showingAgentOnboarding = false
    @AppStorage("didCompleteAgentOnboarding") private var didCompleteAgentOnboarding = false

    var body: some View {
        NavigationSplitView {
            SidebarView(selection: $selection)
        } detail: {
            switch selection {
            case .dashboard:
                DashboardView()
            case .agents:
                AgentsView()
            case .clis:
                CLIsView()
            case .skills:
                SkillsView()
            case .tools:
                ToolsView()
            case .secrets:
                SecretsView()
            case .settings:
                SettingsView()
            }
        }
        .navigationSplitViewStyle(.balanced)
        .tint(DSColor.textPrimary)
        .preferredColorScheme(.light)
        .task {
            if appState.report == nil {
                await appState.refresh()
            }
            if !didCompleteAgentOnboarding && appState.agents.contains(where: { $0.detected && !$0.managed }) {
                showingAgentOnboarding = true
            }
        }
        .sheet(isPresented: $showingAgentOnboarding) {
            AgentOnboardingView {
                await appState.runReconcile()
                didCompleteAgentOnboarding = appState.agents.filter(\.detected).allSatisfy(\.managed)
                return didCompleteAgentOnboarding
            } onSkip: {
                didCompleteAgentOnboarding = true
            }
            .environmentObject(appState)
        }
        .toolbar {
            ToolbarItem {
                Button {
                    Task { await appState.runReconcile() }
                } label: {
                    if appState.isLoading {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Label(L10n.syncAndCheck, systemImage: "arrow.triangle.2.circlepath")
                    }
                }
                .disabled(appState.isLoading)
                .help(L10n.syncAndCheck)
            }
        }
    }
}
