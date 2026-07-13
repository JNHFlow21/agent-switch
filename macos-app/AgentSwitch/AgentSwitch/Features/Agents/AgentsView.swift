// [INPUT]: SwiftUI, AppState, shared design system
// [OUTPUT]: Supported-agent status and explicit takeover/onboarding surfaces
// [POS]: Features/Agents — explains and applies Agent Switch instruction management
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct AgentsView: View {
    @EnvironmentObject var appState: AppState

    private var detected: [AgentInfo] { appState.agents.filter(\.detected) }
    private var managed: [AgentInfo] { detected.filter(\.managed) }
    private var needsManagement: Bool { detected.contains { !$0.managed || !$0.inSync } }

    var body: some View {
        DSPage(title: L10n.agentManagement, subtitle: L10n.agentManagementSubtitle, badges: pageBadges) {
            explanation

            if let error = appState.lastError {
                DSCard {
                    Text(error)
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textSecondary)
                        .textSelection(.enabled)
                }
            }

            DSCard {
                VStack(spacing: 0) {
                    ForEach(Array(appState.agents.enumerated()), id: \.element.id) { index, agent in
                        AgentRow(agent: agent)
                        if index < appState.agents.count - 1 {
                            Divider().overlay(DSColor.separator)
                        }
                    }
                }
            }

            HStack(spacing: DSSpacing.md) {
                Button(L10n.manageDetectedAgents) {
                    Task { await appState.runReconcile() }
                }
                .buttonStyle(.bordered)
                .tint(DSColor.textPrimary)
                .disabled(!needsManagement || appState.isLoading)

                Text(L10n.manageDetectedAgentsNote)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textMuted)
            }
        }
    }

    private var pageBadges: [DSPageBadge] {
        [
            DSPageBadge(text: "\(managed.count)/\(detected.count) \(L10n.managed)", tone: needsManagement ? .warn : .good),
            DSPageBadge(text: "\(detected.count) \(L10n.detected)", tone: .neutral),
        ]
    }

    private var explanation: some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.howManagementWorks)
                    .font(DSTypography.heading)
                Text(L10n.howManagementWorksBody)
                    .font(DSTypography.body)
                    .foregroundStyle(DSColor.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct AgentRow: View {
    let agent: AgentInfo

    private var stateText: String {
        if !agent.detected { return L10n.notDetected }
        if !agent.managed { return L10n.notManaged }
        return agent.inSync ? L10n.synchronized : L10n.needsSync
    }

    var body: some View {
        HStack(alignment: .top, spacing: DSSpacing.lg) {
            Image(systemName: agent.managed && agent.inSync ? "checkmark.circle" : "circle.dashed")
                .font(.system(size: 18))
                .foregroundStyle(agent.detected ? DSColor.textPrimary : DSColor.textMuted)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: DSSpacing.xs) {
                HStack(spacing: DSSpacing.sm) {
                    Text(agent.name)
                        .font(DSTypography.heading)
                    DSBadge(text: stateText, tone: agent.managed && agent.inSync ? .good : .neutral)
                }
                HStack(spacing: DSSpacing.sm) {
                    Text(agent.instructionPath)
                        .font(DSTypography.mono)
                        .foregroundStyle(DSColor.textSecondary)
                        .textSelection(.enabled)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    DSPathActions(path: agent.instructionPath)
                }
                HStack(spacing: DSSpacing.sm) {
                    Text(agent.configPath)
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textMuted)
                        .textSelection(.enabled)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    DSPathActions(path: agent.configPath)
                }
            }
            Spacer()
        }
        .padding(.vertical, DSSpacing.compact)
    }
}

struct AgentOnboardingView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var appState: AppState
    let onManage: () async -> Bool
    let onSkip: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: DSSpacing.xxl) {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.welcomeHeading)
                    .font(DSTypography.title)
                    .foregroundStyle(DSColor.textPrimary)
                Text(L10n.welcomeBody)
                    .font(DSTypography.body)
                    .foregroundStyle(DSColor.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            VStack(alignment: .leading, spacing: DSSpacing.md) {
                ForEach(appState.agents.filter(\.detected)) { agent in
                    HStack(spacing: DSSpacing.md) {
                        Image(systemName: "checkmark")
                        Text(agent.name).font(DSTypography.body)
                    }
                }
            }

            Divider().overlay(DSColor.separator)

            HStack {
                Button(L10n.notNow) {
                    onSkip()
                    dismiss()
                }
                .buttonStyle(.plain)
                Spacer()
                Button(L10n.startManagement) {
                    Task {
                        if await onManage() { dismiss() }
                    }
                }
                .buttonStyle(.bordered)
                .tint(DSColor.textPrimary)
                .disabled(appState.isLoading)
            }
        }
        .padding(DSSpacing.xxl)
        .frame(width: 520)
        .background(DSColor.background)
    }
}
