// [INPUT]: SwiftUI, AppState, DSComponents, DSTokens, L10n
// [OUTPUT]: DashboardView — main status overview
// [POS]: Features/Dashboard — shows runtime state, drift, findings summary
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        DSPage(title: L10n.appName, subtitle: pageSubtitle, badges: pageBadges) {
            if let error = appState.lastError {
                errorSection(error)
            }

            metricsGrid

            if let report = appState.report {
                routesSection()
                findingsSection(report)
                changesSection(report)
            }
        }
    }

    private func errorSection(_ message: String) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.sm) {
                DSBadge(text: L10n.loadFailed, tone: .bad)
                Text(message)
                    .font(DSTypography.body)
                    .foregroundStyle(DSColor.textSecondary)
                    .textSelection(.enabled)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
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

    private var metricsGrid: some View {
        let report = appState.report
        return LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: DSSpacing.md), count: 4), spacing: DSSpacing.md) {
            DSMetricCard(
                label: L10n.runtimeState,
                value: report.map { $0.blocked ? L10n.blocked : L10n.ready } ?? "—",
                note: report.map { $0.driftCount == 0 ? L10n.noDriftDetected : L10n.reviewPlannedChanges } ?? "加载中..."
            )
            DSMetricCard(
                label: L10n.driftChanges,
                value: report.map { "\($0.driftCount)" } ?? "—",
                note: report.map { $0.driftCount == 0 ? L10n.allTargetsInSync : L10n.runReconcileToFix } ?? ""
            )
            DSMetricCard(
                label: L10n.findingsLabel,
                value: report.map { "\($0.findings.count)" } ?? "—",
                note: report.map { $0.findings.isEmpty ? L10n.noIssuesFound : "\($0.findings.filter { $0.severity == "error" }.count) \(L10n.errors)" } ?? ""
            )
            DSMetricCard(
                label: L10n.secretsLabel,
                value: report.map { "\($0.secrets.presentNames.count)/\($0.secrets.required.count)" } ?? "—",
                note: report.map { $0.secrets.missing.isEmpty ? L10n.allPresent : "\($0.secrets.missing.count) \(L10n.missing)" } ?? ""
            )
        }
    }

    @ViewBuilder
    private func routesSection() -> some View {
        let routes = appState.config?.routes
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.accessRoutes)
                    .font(DSTypography.heading)

                HStack(spacing: DSSpacing.xl) {
                    routeItem(role: L10n.searchDefault, toolId: routes?.searchDefault ?? "—")
                    routeItem(role: L10n.xReader, toolId: routes?.xReadDefault ?? "—")
                    routeItem(role: L10n.xFallback, toolId: routes?.xReadFallback ?? "—")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func routeItem(role: String, toolId: String) -> some View {
        VStack(alignment: .leading, spacing: DSSpacing.xs) {
            DSBadge(text: role, tone: .route)
            Text(toolId)
                .font(DSTypography.mono)
                .foregroundStyle(DSColor.textPrimary)
        }
    }

    @ViewBuilder
    private func findingsSection(_ report: DoctorReport) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.findings)
                    .font(DSTypography.heading)

                if report.findings.isEmpty {
                    Text(L10n.noFindingsHealthy)
                        .font(DSTypography.body)
                        .foregroundStyle(DSColor.textSecondary)
                        .padding(.vertical, DSSpacing.sm)
                } else {
                    ForEach(report.findings) { finding in
                        HStack(spacing: DSSpacing.sm) {
                            DSBadge(
                                text: finding.severity,
                                tone: finding.severity == "error" ? .bad : .warn
                            )
                            Text(finding.target)
                                .font(.system(size: 13, weight: .semibold))
                            Text(finding.message)
                                .font(DSTypography.body)
                                .foregroundStyle(DSColor.textSecondary)
                                .lineLimit(1)
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ViewBuilder
    private func changesSection(_ report: DoctorReport) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.plannedChanges)
                    .font(DSTypography.heading)

                if report.changes.isEmpty {
                    Text(L10n.noPlannedChanges)
                        .font(DSTypography.body)
                        .foregroundStyle(DSColor.textSecondary)
                        .padding(.vertical, DSSpacing.sm)
                } else {
                    ForEach(report.changes) { change in
                        HStack(spacing: DSSpacing.sm) {
                            DSBadge(text: change.action, tone: .info)
                            Text(change.target)
                                .font(.system(size: 13, weight: .semibold))
                            Text(change.detail)
                                .font(DSTypography.body)
                                .foregroundStyle(DSColor.textSecondary)
                                .lineLimit(1)
                            Spacer()
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
