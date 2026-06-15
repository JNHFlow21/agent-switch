// [INPUT]: SwiftUI, L10n
// [OUTPUT]: SidebarItem enum, SidebarView
// [POS]: Navigation — owns sidebar selection state and item list
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

enum SidebarItem: String, CaseIterable, Identifiable {
    case dashboard
    case tools
    case secrets
    case settings

    var id: String { rawValue }

    var label: String {
        switch self {
        case .dashboard: return L10n.dashboard
        case .tools: return L10n.mcpTools
        case .secrets: return L10n.secrets
        case .settings: return L10n.settings
        }
    }

    var icon: String {
        switch self {
        case .dashboard: return "gauge.with.dots.needle.33percent"
        case .tools: return "wrench.and.screwdriver"
        case .secrets: return "key"
        case .settings: return "gearshape"
        }
    }
}

struct SidebarView: View {
    @Binding var selection: SidebarItem
    @EnvironmentObject var appState: AppState

    var body: some View {
        List(selection: $selection) {
            Section(L10n.appName) {
                ForEach(SidebarItem.allCases) { item in
                    Label(item.label, systemImage: item.icon)
                        .tag(item)
                }
            }
        }
        .listStyle(.sidebar)
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: DSSpacing.xs) {
                Divider()
                HStack {
                    Circle()
                        .fill(appState.isHealthy ? DSColor.statusGood : DSColor.statusBad)
                        .frame(width: 8, height: 8)
                    Text(appState.sidebarStatusText)
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textSecondary)
                    Spacer()
                    Text("v0.1.2")
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textSecondary)
                }
                .padding(.horizontal, DSSpacing.lg)
                .padding(.bottom, DSSpacing.sm)
            }
        }
    }
}
