// [INPUT]: SwiftUI, AppState, CLIInfo, shared design system
// [OUTPUT]: Installed CLI inventory with live versions and file actions
// [POS]: Features/CLIs — visible local command-line tool control surface
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct CLIsView: View {
    @EnvironmentObject var appState: AppState

    private var installed: [CLIInfo] { appState.clis.filter(\.installed) }

    var body: some View {
        DSPage(
            title: L10n.cliManagement,
            subtitle: L10n.cliManagementSubtitle,
            badges: [
                DSPageBadge(text: "\(installed.count)/\(appState.clis.count) \(L10n.installed)", tone: .good),
            ]
        ) {
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: DSSpacing.md), count: 3), spacing: DSSpacing.md) {
                DSMetricCard(label: L10n.installedCLIs, value: "\(installed.count)", note: L10n.cliManagementSubtitle)
                DSMetricCard(label: L10n.notInstalled, value: "\(appState.clis.count - installed.count)", note: L10n.cliInventory)
                DSMetricCard(label: L10n.version, value: "\(installed.filter { $0.version != nil }.count)", note: L10n.cliUpdateNote)
            }

            DSCard {
                VStack(alignment: .leading, spacing: 0) {
                    Text(L10n.cliInventory)
                        .font(DSTypography.heading)
                        .padding(.bottom, DSSpacing.md)

                    ForEach(Array(appState.clis.enumerated()), id: \.element.id) { index, cli in
                        CLIRow(cli: cli)
                        if index < appState.clis.count - 1 {
                            Divider().overlay(DSColor.separator)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            Text(L10n.cliUpdateNote)
                .font(DSTypography.caption)
                .foregroundStyle(DSColor.textMuted)
        }
    }
}

private struct CLIRow: View {
    let cli: CLIInfo

    var body: some View {
        HStack(alignment: .center, spacing: DSSpacing.lg) {
            Image(systemName: "terminal")
                .font(.system(size: 16))
                .foregroundStyle(cli.installed ? DSColor.textPrimary : DSColor.textMuted)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: DSSpacing.xs) {
                HStack(spacing: DSSpacing.sm) {
                    Text(cli.name).font(DSTypography.heading)
                    DSBadge(text: cli.installed ? L10n.installed : L10n.notInstalled, tone: cli.installed ? .good : .neutral)
                }
                Text(cli.version ?? cli.command)
                    .font(DSTypography.mono)
                    .foregroundStyle(cli.installed ? DSColor.textSecondary : DSColor.textMuted)
                    .lineLimit(1)
                Text("\(L10n.packageManager)：\(cli.manager)")
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textMuted)
            }

            Spacer()

            if let path = cli.path {
                Text(path)
                    .font(DSTypography.mono)
                    .foregroundStyle(DSColor.textSecondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .frame(maxWidth: 360, alignment: .trailing)
                    .textSelection(.enabled)
                DSPathActions(path: path)
            }
        }
        .padding(.vertical, DSSpacing.compact)
    }
}
