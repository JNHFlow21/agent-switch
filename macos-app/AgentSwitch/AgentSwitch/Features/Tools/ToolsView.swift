// [INPUT]: SwiftUI, AppState, DSComponents, DSTokens, L10n
// [OUTPUT]: ToolsView — lists managed MCP tools with status
// [POS]: Features/Tools — shows tool list, wrapper health, target apps
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct ToolsView: View {
    @EnvironmentObject var appState: AppState
    @State private var showingEditor = false
    @State private var editingToolID: String?
    @State private var pendingDelete: String?
    @State private var showingImportConfirmation = false

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
                hasDrift: report.changes.contains { $0.target == "wrappers" && $0.detail.contains(tool.id) },
                enabled: tool.enabled
            )
        }
    }

    private var editingTool: ToolInfo? {
        appState.config?.tools.first { $0.id == editingToolID }
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
                        ToolRow(
                            tool: tool,
                            onEdit: {
                                editingToolID = tool.id
                                showingEditor = true
                            },
                            onToggle: {
                                Task { _ = await appState.setMCPEnabled(id: tool.id, enabled: !tool.enabled) }
                            },
                            onDelete: { pendingDelete = tool.id }
                        )
                    }
                }
            }
        }
        .toolbar {
            ToolbarItemGroup {
                Button {
                    Task {
                        if await appState.previewMCPImport() {
                            showingImportConfirmation = true
                        }
                    }
                } label: {
                    Label(L10n.importMCPs, systemImage: "square.and.arrow.down")
                }
                .disabled(appState.isLoading)

                Button {
                    editingToolID = nil
                    showingEditor = true
                } label: {
                    Label(L10n.addMCP, systemImage: "plus")
                }
            }
        }
        .sheet(isPresented: $showingEditor) {
            MCPEditorSheet(existing: editingTool) { draft in
                await appState.saveMCP(
                    id: draft.id,
                    name: draft.name,
                    command: draft.command,
                    args: draft.args,
                    secrets: draft.secrets,
                    env: draft.env,
                    apps: draft.apps,
                    description: draft.description,
                    enabled: draft.enabled
                )
            }
        }
        .confirmationDialog(
            L10n.removeMCP,
            isPresented: Binding(
                get: { pendingDelete != nil },
                set: { if !$0 { pendingDelete = nil } }
            ),
            presenting: pendingDelete
        ) { id in
            Button(L10n.removeMCP, role: .destructive) {
                Task {
                    _ = await appState.removeMCP(id: id)
                    pendingDelete = nil
                }
            }
            Button(L10n.cancel, role: .cancel) { pendingDelete = nil }
        } message: { id in
            Text("\(L10n.removeMCPConfirmation) \(id)")
        }
        .confirmationDialog(
            L10n.importMCPs,
            isPresented: $showingImportConfirmation
        ) {
            Button(L10n.importAndAdoptMCPs) {
                Task { _ = await appState.importMCPs() }
            }
            Button(L10n.cancel, role: .cancel) {}
        } message: {
            Text(importPreviewMessage)
        }
    }

    private var importPreviewMessage: String {
        guard let preview = appState.importPreview else { return L10n.importMCPConfirmation }
        let ids = Array(Set(preview.imported + preview.merged)).sorted()
        let idText = ids.isEmpty ? L10n.none : ids.joined(separator: ", ")
        let secretText = preview.secretNames.isEmpty ? L10n.none : preview.secretNames.joined(separator: ", ")
        let skippedText = preview.skipped.isEmpty
            ? L10n.none
            : preview.skipped.map { "\($0.app):\($0.id)" }.joined(separator: ", ")
        return "\(L10n.importMCPConfirmation)\n\n\(L10n.discoveredMCPs): \(preview.discovered)\n\(L10n.supportedMCPs): \(preview.supported)\nMCP IDs: \(idText)\n\(L10n.secretNamesOnly): \(secretText)\n\(L10n.skippedMCPs): \(skippedText)"
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
    let enabled: Bool
}

struct ToolRow: View {
    let tool: ToolDisplayItem
    let onEdit: () -> Void
    let onToggle: () -> Void
    let onDelete: () -> Void

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
                            if !tool.enabled {
                                DSBadge(text: L10n.disabledMCP, tone: .neutral)
                            }
                        }
                        Text(tool.id)
                            .font(DSTypography.mono)
                            .foregroundStyle(DSColor.textSecondary)
                    }
                    Spacer()
                    DSBadge(
                        text: !tool.enabled ? L10n.disabledMCP : tool.secretsOk ? L10n.readyState : L10n.missingSecrets,
                        tone: !tool.enabled ? .neutral : tool.secretsOk ? .good : .bad
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
                    Spacer()
                    Button(tool.enabled ? L10n.disableMCP : L10n.enableMCP, action: onToggle)
                        .buttonStyle(.bordered)
                    DSIconButton(systemName: "pencil", help: L10n.editMCP, action: onEdit)
                    DSIconButton(systemName: "trash", help: L10n.removeMCP, action: onDelete)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct MCPDraft {
    let id: String
    let name: String
    let command: String
    let args: [String]
    let secrets: [String]
    let env: [String: String]
    let apps: AppFlags
    let description: String?
    let enabled: Bool
}

private struct MCPEditorSheet: View {
    @Environment(\.dismiss) private var dismiss
    let existing: ToolInfo?
    let onSave: (MCPDraft) async -> Bool

    @State private var id: String
    @State private var name: String
    @State private var command: String
    @State private var argsText: String
    @State private var secretsText: String
    @State private var envText: String
    @State private var descriptionText: String
    @State private var claude: Bool
    @State private var claudeDesktop: Bool
    @State private var codex: Bool
    @State private var hermes: Bool
    @State private var enabled: Bool
    @State private var saving = false

    init(existing: ToolInfo?, onSave: @escaping (MCPDraft) async -> Bool) {
        self.existing = existing
        self.onSave = onSave
        _id = State(initialValue: existing?.id ?? "")
        _name = State(initialValue: existing?.name ?? "")
        _command = State(initialValue: existing?.command ?? "")
        _argsText = State(initialValue: existing?.args.joined(separator: "\n") ?? "")
        _secretsText = State(initialValue: existing?.requiredSecrets.joined(separator: "\n") ?? "")
        _envText = State(initialValue: existing?.env.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }.joined(separator: "\n") ?? "")
        _descriptionText = State(initialValue: existing?.description ?? "")
        _claude = State(initialValue: existing?.apps.claude ?? true)
        _claudeDesktop = State(initialValue: existing?.apps.claude_desktop ?? true)
        _codex = State(initialValue: existing?.apps.codex ?? true)
        _hermes = State(initialValue: existing?.apps.hermes ?? true)
        _enabled = State(initialValue: existing?.enabled ?? true)
    }

    private var normalizedID: String {
        let value = id.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return value.hasPrefix("agent-") ? value : "agent-\(value)"
    }

    private var valid: Bool {
        normalizedID.range(of: "^agent-[a-z0-9][a-z0-9-]*$", options: .regularExpression) != nil
            && !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !command.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && (claude || claudeDesktop || codex || hermes)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: DSSpacing.xl) {
            Text(existing == nil ? L10n.addMCP : L10n.editMCP)
                .font(DSTypography.title)
            Text(L10n.mcpEditorNote)
                .font(DSTypography.caption)
                .foregroundStyle(DSColor.textSecondary)

            Form {
                TextField(L10n.mcpID, text: $id)
                    .disabled(existing != nil)
                TextField(L10n.mcpName, text: $name)
                TextField(L10n.mcpCommand, text: $command)
                TextField(L10n.mcpDescription, text: $descriptionText)
                VStack(alignment: .leading) {
                    Text(L10n.mcpArguments).font(DSTypography.caption)
                    TextEditor(text: $argsText).font(DSTypography.mono).frame(minHeight: 72)
                }
                VStack(alignment: .leading) {
                    Text(L10n.mcpRequiredSecrets).font(DSTypography.caption)
                    TextEditor(text: $secretsText).font(DSTypography.mono).frame(minHeight: 64)
                }
                VStack(alignment: .leading) {
                    Text(L10n.mcpEnvironment).font(DSTypography.caption)
                    TextEditor(text: $envText).font(DSTypography.mono).frame(minHeight: 64)
                }
                Section(L10n.targets) {
                    Toggle("Claude Code", isOn: $claude)
                    Toggle("Claude Desktop", isOn: $claudeDesktop)
                    Toggle("Codex", isOn: $codex)
                    Toggle("Hermes", isOn: $hermes)
                }
                Toggle(L10n.enableMCP, isOn: $enabled)
            }
            .formStyle(.grouped)

            HStack {
                Button(L10n.cancel) { dismiss() }
                    .buttonStyle(.plain)
                Spacer()
                Button(existing == nil ? L10n.addMCP : L10n.saveMCP) {
                    saving = true
                    let args = argsText.split(whereSeparator: \.isNewline).map(String.init).filter { !$0.isEmpty }
                    let separators = CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ","))
                    let secrets = secretsText.components(separatedBy: separators).filter { !$0.isEmpty }.map { $0.uppercased() }
                    var environment: [String: String] = [:]
                    for line in envText.split(whereSeparator: \.isNewline) {
                        let parts = line.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                        if parts.count == 2, !parts[0].isEmpty {
                            environment[String(parts[0])] = String(parts[1])
                        }
                    }
                    let draft = MCPDraft(
                        id: normalizedID,
                        name: name.trimmingCharacters(in: .whitespacesAndNewlines),
                        command: command.trimmingCharacters(in: .whitespacesAndNewlines),
                        args: args,
                        secrets: Array(Set(secrets)).sorted(),
                        env: environment,
                        apps: AppFlags(claude: claude, claude_desktop: claudeDesktop, codex: codex, hermes: hermes),
                        description: descriptionText.trimmingCharacters(in: .whitespacesAndNewlines),
                        enabled: enabled
                    )
                    Task {
                        if await onSave(draft) { dismiss() }
                        saving = false
                    }
                }
                .buttonStyle(.bordered)
                .disabled(!valid || saving)
            }
        }
        .padding(DSSpacing.xxl)
        .frame(width: 640, height: 720)
        .background(DSColor.background)
    }
}
