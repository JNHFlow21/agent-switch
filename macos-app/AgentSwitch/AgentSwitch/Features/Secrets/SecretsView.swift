// [INPUT]: SwiftUI, AppKit, AppState, shared design system
// [OUTPUT]: Local secret create, update, one-click reveal, copy, delete, and file actions
// [POS]: Features/Secrets — operational UI over Agent Switch fd/stdin secret contracts
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import AppKit
import SwiftUI

struct SecretsView: View {
    @EnvironmentObject var appState: AppState
    @State private var editorName: String?
    @State private var showingEditor = false
    @State private var pendingDelete: String?
    @State private var revealed: [String: String] = [:]

    private var secretInfo: SecretInfo? { appState.report?.secrets }

    private var allNames: [String] {
        guard let info = secretInfo else { return [] }
        return Array(Set(info.storedNames).union(info.required)).sorted()
    }

    var body: some View {
        DSPage(title: L10n.secretsInventory, subtitle: L10n.secretManagementSubtitle, badges: pageBadges) {
            if let error = appState.lastError {
                DSCard {
                    Text(error)
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textSecondary)
                        .textSelection(.enabled)
                }
            }

            if let info = secretInfo {
                summary(info)
                secretList(info)
                storageNote(info)
            } else if appState.isLoading {
                ProgressView(L10n.loadingTools)
                    .padding(.top, DSSpacing.xxl)
            } else {
                emptyState
            }
        }
        .toolbar {
            ToolbarItem {
                Button {
                    editorName = nil
                    showingEditor = true
                } label: {
                    Label(L10n.addSecret, systemImage: "plus")
                }
            }
        }
        .sheet(isPresented: $showingEditor) {
            SecretEditorSheet(existingName: editorName) { name, value in
                await appState.setSecret(name: name, value: value)
            }
        }
        .confirmationDialog(
            L10n.deleteSecret,
            isPresented: Binding(
                get: { pendingDelete != nil },
                set: { if !$0 { pendingDelete = nil } }
            ),
            presenting: pendingDelete
        ) { name in
            Button(L10n.deleteSecret, role: .destructive) {
                Task {
                    _ = await appState.deleteSecret(name: name)
                    hideSecret(name)
                    pendingDelete = nil
                }
            }
            Button(L10n.cancel, role: .cancel) { pendingDelete = nil }
        } message: { name in
            Text("\(L10n.deleteSecretConfirmation) \(name)")
        }
        .onDisappear {
            revealed.removeAll()
        }
    }

    private var pageBadges: [DSPageBadge] {
        guard let info = secretInfo else { return [] }
        return [
            DSPageBadge(text: "\(info.storedNames.count) \(L10n.stored)", tone: .neutral),
            DSPageBadge(text: info.missing.isEmpty ? L10n.ready : "\(info.missing.count) \(L10n.missing)", tone: info.missing.isEmpty ? .good : .warn),
        ]
    }

    private func summary(_ info: SecretInfo) -> some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: DSSpacing.md), count: 3), spacing: DSSpacing.md) {
            DSMetricCard(label: L10n.storedSecrets, value: "\(info.storedNames.count)", note: L10n.storedSecretsNote)
            DSMetricCard(label: L10n.requiredSecrets, value: "\(info.required.count)", note: L10n.requiredSecretsNote)
            DSMetricCard(label: L10n.missing, value: "\(info.missing.count)", note: info.missing.isEmpty ? L10n.allSecretsConfigured : info.missing.joined(separator: ", "))
        }
    }

    private func secretList(_ info: SecretInfo) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: 0) {
                HStack {
                    Text(L10n.allSecrets)
                        .font(DSTypography.heading)
                    Spacer()
                    Button(L10n.addSecret) {
                        editorName = nil
                        showingEditor = true
                    }
                    .buttonStyle(.bordered)
                    .tint(DSColor.textPrimary)
                }
                .padding(.bottom, DSSpacing.md)

                ForEach(Array(allNames.enumerated()), id: \.element) { index, name in
                    secretRow(name, info: info)
                    if index < allNames.count - 1 {
                        Divider().overlay(DSColor.separator)
                    }
                }

                if allNames.isEmpty {
                    Text(L10n.noStoredSecrets)
                        .font(DSTypography.body)
                        .foregroundStyle(DSColor.textMuted)
                        .padding(.vertical, DSSpacing.lg)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func secretRow(_ name: String, info: SecretInfo) -> some View {
        let isStored = info.storedNames.contains(name)
        let isRequired = info.required.contains(name)
        return HStack(alignment: .center, spacing: DSSpacing.lg) {
            Image(systemName: isStored ? "key" : "key.slash")
                .font(.system(size: 16))
                .foregroundStyle(isStored ? DSColor.textPrimary : DSColor.textMuted)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: DSSpacing.xs) {
                HStack(spacing: DSSpacing.sm) {
                    Text(name)
                        .font(DSTypography.mono)
                    if isRequired {
                        DSBadge(text: L10n.requiredBadge, tone: .neutral)
                    }
                    if !isStored {
                        DSBadge(text: L10n.missingBadge, tone: .warn)
                    }
                }
                if let value = revealed[name] {
                    Text(value)
                        .font(DSTypography.mono)
                        .foregroundStyle(DSColor.textPrimary)
                        .textSelection(.enabled)
                        .lineLimit(2)
                } else {
                    Text(isStored ? "••••••••••••" : L10n.notConfigured)
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textMuted)
                }
                if let consumers = info.consumers?[name], !consumers.isEmpty {
                    Text("\(L10n.usedByMCP): \(consumers.joined(separator: ", "))")
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textMuted)
                        .lineLimit(2)
                }
            }

            Spacer()

            DSIconButton(
                systemName: revealed[name] == nil ? "eye" : "eye.slash",
                help: revealed[name] == nil ? L10n.revealSecret : L10n.hideSecret,
                disabled: !isStored
            ) {
                if revealed[name] == nil {
                    revealSecret(name)
                } else {
                    hideSecret(name)
                }
            }

            DSIconButton(systemName: "doc.on.doc", help: L10n.copySecret, disabled: revealed[name] == nil) {
                if let value = revealed[name] { copySecret(value) }
            }

            DSIconButton(systemName: "pencil", help: isStored ? L10n.updateSecret : L10n.configureSecret) {
                editorName = name
                showingEditor = true
            }

            DSIconButton(systemName: "trash", help: L10n.deleteSecret, disabled: !isStored) {
                pendingDelete = name
            }
        }
        .padding(.vertical, DSSpacing.compact)
    }

    private func storageNote(_ info: SecretInfo) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(L10n.secretFileLocation).font(DSTypography.heading)
                DSPathRow(label: L10n.secretFile, path: info.path)
                Text(L10n.secretsRuntimeNote)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textMuted)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var emptyState: some View {
        VStack(spacing: DSSpacing.md) {
            Image(systemName: "key.slash")
                .font(.system(size: 24))
                .foregroundStyle(DSColor.textMuted)
            Text(L10n.noSecretInfo).font(DSTypography.body)
            Text(L10n.runDoctorForSecrets)
                .font(DSTypography.caption)
                .foregroundStyle(DSColor.textMuted)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, DSSpacing.xxl)
    }

    private func revealSecret(_ name: String) {
        Task {
            guard let value = await appState.revealSecret(name: name) else { return }
            revealed[name] = value
        }
    }

    private func hideSecret(_ name: String) {
        revealed.removeValue(forKey: name)
    }

    private func copySecret(_ value: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(value, forType: .string)
    }
}

private struct SecretEditorSheet: View {
    @Environment(\.dismiss) private var dismiss
    let existingName: String?
    let onSave: (String, String) async -> Bool
    @State private var name = ""
    @State private var value = ""
    @State private var saving = false
    @State private var showingValue = false

    private var normalizedName: String { (existingName ?? name).trimmingCharacters(in: .whitespacesAndNewlines).uppercased() }
    private var nameIsValid: Bool { normalizedName.range(of: "^[A-Z][A-Z0-9_]*$", options: .regularExpression) != nil }

    var body: some View {
        VStack(alignment: .leading, spacing: DSSpacing.xxl) {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                Text(existingName == nil ? L10n.addSecret : L10n.updateSecret)
                    .font(DSTypography.title)
                Text(L10n.secretEditorNote)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textSecondary)
            }

            VStack(alignment: .leading, spacing: DSSpacing.md) {
                if let existingName {
                    VStack(alignment: .leading, spacing: DSSpacing.xs) {
                        Text(L10n.secretNameLabel)
                            .font(DSTypography.caption)
                            .foregroundStyle(DSColor.textMuted)
                        Text(existingName)
                            .font(DSTypography.mono)
                            .foregroundStyle(DSColor.textPrimary)
                            .textSelection(.enabled)
                    }
                } else {
                    TextField(L10n.secretName, text: $name)
                        .textFieldStyle(.roundedBorder)
                }
                HStack(spacing: DSSpacing.sm) {
                    Group {
                        if showingValue {
                            TextField(L10n.secretValue, text: $value)
                        } else {
                            SecureField(L10n.secretValue, text: $value)
                        }
                    }
                    .textFieldStyle(.roundedBorder)
                    DSIconButton(
                        systemName: showingValue ? "eye.slash" : "eye",
                        help: showingValue ? L10n.hideSecret : L10n.revealSecret
                    ) {
                        showingValue.toggle()
                    }
                }
            }
            .onAppear { name = existingName ?? "" }

            Divider().overlay(DSColor.separator)

            HStack {
                Button(L10n.cancel) { dismiss() }
                    .buttonStyle(.plain)
                Spacer()
                Button(existingName == nil ? L10n.addSecret : L10n.updateSecret) {
                    saving = true
                    Task {
                        if await onSave(normalizedName, value) { dismiss() }
                        saving = false
                    }
                }
                .buttonStyle(.bordered)
                .tint(DSColor.textPrimary)
                .disabled(!nameIsValid || value.isEmpty || saving)
            }
        }
        .padding(DSSpacing.xxl)
        .frame(width: 500)
        .background(DSColor.background)
    }
}
