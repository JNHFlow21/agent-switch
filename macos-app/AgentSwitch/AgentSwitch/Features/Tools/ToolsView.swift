// [INPUT]: SwiftUI, AppState, DSComponents, DSTokens, L10n
// [OUTPUT]: ToolsView — lists managed MCP tools with status
// [POS]: Features/Tools — shows tool list, wrapper health, target apps
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct ToolsView: View {
    @EnvironmentObject var appState: AppState

    private var tools: [ToolDisplayItem] {
        guard let report = appState.report, let config = appState.config else { return [] }
        return config.tools.map { tool in
            let hasAllSecrets = tool.requiredSecrets.allSatisfy { report.secrets.presentNames.contains($0) }
            let missingSecrets = tool.requiredSecrets.filter { report.secrets.missing.contains($0) }
            return ToolDisplayItem(
                id: tool.id,
                name: tool.name,
                command: tool.displayCommand,
                description: tool.description,
                apps: tool.apps.enabledApps,
                requiredSecrets: tool.requiredSecrets,
                missingSecrets: missingSecrets,
                secretsOk: hasAllSecrets,
                hasDrift: report.changes.contains { $0.target == "wrappers" && $0.detail.contains(tool.id) }
            )
        }
    }

    var body: some View {
        DSPage(title: L10n.managedMCPTools, subtitle: pageSubtitle, badges: pageBadges) {
            if tools.isEmpty && appState.isLoading {
                ProgressView(L10n.loadingTools)
                    .padding(.top, DSSpacing.xxl)
            } else {
                toolSummary

                LazyVStack(spacing: DSSpacing.lg) {
                    ForEach(tools) { tool in
                        ToolRow(tool: tool)
                    }
                }
            }
        }
    }

    private var pageSubtitle: String? {
        appState.lastRefresh.map { "\(L10n.lastRefreshed)\($0.formatted(date: .omitted, time: .shortened))" }
    }

    private var pageBadges: [DSPageBadge] {
        guard let report = appState.report else { return [] }
        return [
            DSPageBadge(text: report.blocked ? L10n.blocked : L10n.ready, tone: report.blocked ? .bad : .good),
            DSPageBadge(text: "\(report.driftCount) \(L10n.drift)", tone: report.driftCount == 0 ? .good : .warn),
        ]
    }

    private var toolSummary: some View {
        let readyCount = tools.filter(\.secretsOk).count
        let missingCount = tools.reduce(0) { $0 + $1.missingSecrets.count }
        let driftCount = tools.filter(\.hasDrift).count

        return LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: DSSpacing.md), count: 4), spacing: DSSpacing.md) {
            DSMetricCard(
                label: L10n.mcpTools,
                value: "\(tools.count)",
                note: L10n.allTargetsInSync
            )
            DSMetricCard(
                label: L10n.readyState,
                value: "\(readyCount)",
                note: readyCount == tools.count ? L10n.allSecretsConfigured : L10n.reviewPlannedChanges
            )
            DSMetricCard(
                label: L10n.missing,
                value: "\(missingCount)",
                note: missingCount == 0 ? L10n.allPresent : L10n.missingSecrets
            )
            DSMetricCard(
                label: L10n.driftChanges,
                value: "\(driftCount)",
                note: driftCount == 0 ? L10n.noDriftDetected : L10n.runReconcileToFix
            )
        }
    }
}

struct ToolDisplayItem: Identifiable {
    let id: String
    let name: String
    let command: String
    let description: String?
    let apps: [String]
    let requiredSecrets: [String]
    let missingSecrets: [String]
    let secretsOk: Bool
    let hasDrift: Bool
}

struct ToolRow: View {
    let tool: ToolDisplayItem

    var body: some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.lg) {
                HStack {
                    VStack(alignment: .leading, spacing: DSSpacing.xs) {
                        HStack(spacing: DSSpacing.sm) {
                            Text(tool.name)
                                .font(DSTypography.heading)
                            if tool.hasDrift {
                                DSBadge(text: L10n.driftState, tone: .warn)
                            }
                        }
                        Text(tool.id)
                            .font(DSTypography.mono)
                            .foregroundStyle(DSColor.textSecondary)
                    }
                    Spacer()
                    DSBadge(
                        text: tool.secretsOk ? L10n.readyState : L10n.missingSecrets,
                        tone: tool.secretsOk ? .good : .bad
                    )
                }

                if let desc = tool.description {
                    Text(desc)
                        .font(DSTypography.body)
                        .foregroundStyle(DSColor.textSecondary)
                        .lineLimit(2)
                }

                HStack(spacing: DSSpacing.xl) {
                    VStack(alignment: .leading, spacing: DSSpacing.xs) {
                        Text(L10n.targets.uppercased())
                            .font(DSTypography.caption)
                            .foregroundStyle(DSColor.textSecondary)
                        HStack(spacing: DSSpacing.xs) {
                            if tool.apps.isEmpty {
                                DSBadge(text: "Reserved", tone: .neutral)
                            } else {
                                ForEach(tool.apps, id: \.self) { app in
                                    DSBadge(text: app, tone: .app)
                                }
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: DSSpacing.xs) {
                        Text(L10n.secretsSection.uppercased())
                            .font(DSTypography.caption)
                            .foregroundStyle(DSColor.textSecondary)
                        HStack(spacing: DSSpacing.xs) {
                            if tool.requiredSecrets.isEmpty {
                                DSBadge(text: "none", tone: .neutral)
                            } else {
                                ForEach(tool.requiredSecrets, id: \.self) { secret in
                                    DSBadge(
                                        text: secret,
                                        tone: tool.missingSecrets.contains(secret) ? .bad : .good
                                    )
                                }
                            }
                        }
                    }
                }

                HStack(spacing: DSSpacing.xs) {
                    Text("\(L10n.command):")
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textSecondary)
                    Text(tool.command)
                        .font(DSTypography.mono)
                        .foregroundStyle(DSColor.textPrimary)
                        .lineLimit(2)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
