// [INPUT]: SwiftUI, AppState, DSComponents, DSTokens, L10n
// [OUTPUT]: SecretsView — displays secret inventory and status
// [POS]: Features/Secrets — shows present/missing secrets for all tools
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct SecretsView: View {
    @EnvironmentObject var appState: AppState

    private var secretInfo: SecretInfo? {
        appState.report?.secrets
    }

    var body: some View {
        DSPage(title: L10n.secretsInventory, subtitle: pageSubtitle, badges: pageBadges) {
            if let info = secretInfo {
                secretSummary(info)
                secretsList(info)
            } else if appState.isLoading {
                ProgressView(L10n.loadingTools)
                    .padding(.top, DSSpacing.xxl)
            } else {
                emptyState
            }
        }
    }

    private var pageSubtitle: String? {
        appState.lastRefresh.map { "\(L10n.lastRefreshed)\($0.formatted(date: .omitted, time: .shortened))" }
    }

    private var pageBadges: [DSPageBadge] {
        guard let info = secretInfo else { return [] }
        return [
            DSPageBadge(text: info.missing.isEmpty ? L10n.ready : L10n.missing, tone: info.missing.isEmpty ? .good : .bad),
            DSPageBadge(text: "\(info.presentNames.count)/\(info.required.count)", tone: info.missing.isEmpty ? .good : .warn),
        ]
    }

    @ViewBuilder
    private func secretSummary(_ info: SecretInfo) -> some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: DSSpacing.md), count: 4), spacing: DSSpacing.md) {
            DSMetricCard(
                label: L10n.secretFile,
                value: info.exists ? L10n.found : L10n.missingFile,
                note: info.path
            )
            DSMetricCard(
                label: L10n.requiredSecrets,
                value: "\(info.required.count)",
                note: "\(L10n.ofRequired) \(info.required.count) \(L10n.requiredSuffix)"
            )
            DSMetricCard(
                label: L10n.present,
                value: "\(info.presentNames.count)",
                note: "\(L10n.ofRequired) \(info.required.count) \(L10n.requiredSuffix)"
            )
            DSMetricCard(
                label: L10n.missing,
                value: "\(info.missing.count)",
                note: info.missing.isEmpty ? L10n.allSecretsConfigured : info.missing.joined(separator: ", ")
            )
        }
    }

    @ViewBuilder
    private func secretsList(_ info: SecretInfo) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.requiredSecrets)
                    .font(DSTypography.heading)

                ForEach(info.required, id: \.self) { name in
                    HStack {
                        Image(systemName: info.presentNames.contains(name) ? "checkmark.circle.fill" : "xmark.circle.fill")
                            .foregroundStyle(info.presentNames.contains(name) ? DSColor.statusGood : DSColor.statusBad)
                            .font(.system(size: 16))
                        Text(name)
                            .font(DSTypography.mono)
                        Spacer()
                        DSBadge(
                            text: info.presentNames.contains(name) ? L10n.presentBadge : L10n.missingBadge,
                            tone: info.presentNames.contains(name) ? .good : .bad
                        )
                    }
                    .padding(.vertical, DSSpacing.xs)
                    if name != info.required.last {
                        Divider()
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }

        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.secretFileLocation)
                    .font(DSTypography.heading)

                HStack(spacing: DSSpacing.sm) {
                    Image(systemName: "doc.text")
                        .foregroundStyle(DSColor.textSecondary)
                    Text(info.path)
                        .font(DSTypography.mono)
                        .foregroundStyle(DSColor.textPrimary)
                        .textSelection(.enabled)
                    Spacer()
                    Button(L10n.revealInFinder) {
                        NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: (info.path as NSString).deletingLastPathComponent)
                    }
                    .controlSize(.small)
                }

                Text(L10n.secretsRuntimeNote)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var emptyState: some View {
        VStack(spacing: DSSpacing.md) {
            Image(systemName: "key.slash")
                .font(.system(size: 40))
                .foregroundStyle(DSColor.textSecondary)
            Text(L10n.noSecretInfo)
                .font(DSTypography.body)
                .foregroundStyle(DSColor.textSecondary)
            Text(L10n.runDoctorForSecrets)
                .font(DSTypography.caption)
                .foregroundStyle(DSColor.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, DSSpacing.xxl)
    }
}
