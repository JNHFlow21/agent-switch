// [INPUT]: SwiftUI, AppState, graphite design tokens
// [OUTPUT]: Fixed-width ghost-button sidebar and runtime footer
// [POS]: Navigation — owns sidebar item identity and selection presentation
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

enum SidebarItem: String, CaseIterable, Identifiable {
    case dashboard
    case agents
    case clis
    case skills
    case tools
    case secrets
    case settings

    var id: String { rawValue }

    var label: String {
        switch self {
        case .dashboard: return L10n.dashboard
        case .agents: return L10n.agents
        case .clis: return L10n.clis
        case .skills: return L10n.skills
        case .tools: return L10n.mcpTools
        case .secrets: return L10n.secrets
        case .settings: return L10n.settings
        }
    }

    var icon: String {
        switch self {
        case .dashboard: return "gauge.with.dots.needle.33percent"
        case .agents: return "person.2"
        case .clis: return "terminal"
        case .skills: return "shippingbox"
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
        VStack(alignment: .leading, spacing: 0) {
            Text(L10n.appName)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(DSColor.textPrimary)
                .padding(.horizontal, DSSpacing.lg)
                .frame(height: 52)

            ScrollView {
                VStack(spacing: DSSpacing.xs) {
                    ForEach(SidebarItem.allCases) { item in
                        SidebarRow(item: item, selected: selection == item) {
                            selection = item
                        }
                    }
                }
                .padding(.horizontal, DSSpacing.md)
                .padding(.top, DSSpacing.xs)
            }

            Divider().overlay(DSColor.separator)
            HStack(spacing: DSSpacing.sm) {
                Circle()
                    .fill(appState.isHealthy ? DSColor.textPrimary : DSColor.textMuted)
                    .frame(width: 8, height: 8)
                Text(appState.sidebarStatusText)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textSecondary)
                Spacer()
                Text("v\(AppVersion.current)")
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textMuted)
            }
            .padding(DSSpacing.lg)
        }
        .frame(minWidth: 260, idealWidth: 270, maxWidth: 280, maxHeight: .infinity)
        .background(DSColor.sidebar)
    }
}

private struct SidebarRow: View {
    let item: SidebarItem
    let selected: Bool
    let action: () -> Void
    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: DSSpacing.md) {
                Image(systemName: item.icon)
                    .font(.system(size: 16, weight: .regular))
                    .frame(width: 18)
                Text(item.label)
                    .font(.system(size: 14, weight: selected ? .medium : .regular))
                Spacer()
            }
            .foregroundStyle(DSColor.textPrimary)
            .padding(.horizontal, DSSpacing.md)
            .padding(.vertical, DSSpacing.xs)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .background(
            selected || isHovering ? DSColor.hover : Color.clear,
            in: RoundedRectangle(cornerRadius: DSRadius.medium, style: .continuous)
        )
        .onHover { isHovering = $0 }
    }
}
