// [INPUT]: SwiftUI, AppState, SkillReport, shared design system
// [OUTPUT]: Searchable Skill Hub warehouse with activation state, source update, and file actions
// [POS]: Features/Skills — Skill source inventory and dormant/project/global visibility
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

struct SkillsView: View {
    @EnvironmentObject var appState: AppState
    @State private var query = ""
    @State private var filter: SkillFilter = .all

    private var report: SkillReport? { appState.skillReport }

    private var filteredSkills: [SkillInfo] {
        guard let report else { return [] }
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return report.skills.filter { skill in
            let statusMatches = filter == .all || filter.rawValue == skill.status
            let queryMatches = needle.isEmpty || [skill.name, skill.source, skill.path, skill.profiles.joined(separator: " ")]
                .joined(separator: " ")
                .lowercased()
                .contains(needle)
            return statusMatches && queryMatches
        }
    }

    var body: some View {
        DSPage(title: L10n.skillWarehouse, subtitle: L10n.skillWarehouseSubtitle, badges: pageBadges) {
            if let report {
                summary(report)
                sourceSection(report)
                skillSection(report)
            } else if appState.isLoading {
                ProgressView(L10n.loadingTools)
            }
        }
        .toolbar {
            ToolbarItem {
                Button {
                    Task { _ = await appState.updateSkills() }
                } label: {
                    Label(L10n.updateGitSources, systemImage: "arrow.down.circle")
                }
                .disabled(appState.isLoading)
                .help(L10n.updateGitSourcesNote)
            }
        }
    }

    private var pageBadges: [DSPageBadge] {
        guard let report else { return [] }
        return [
            DSPageBadge(text: "\(report.skills.count) Skill", tone: .neutral),
            DSPageBadge(text: "\(report.dormantCount) \(L10n.dormant)", tone: .neutral),
        ]
    }

    private func summary(_ report: SkillReport) -> some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: DSSpacing.md), count: 4), spacing: DSSpacing.md) {
            DSMetricCard(label: L10n.skillSources, value: "\(report.sources.count)", note: report.hubPath)
            DSMetricCard(label: L10n.skillProfiles, value: "\(report.profiles.count)", note: L10n.skillWarehouseSubtitle)
            DSMetricCard(label: L10n.globalActive, value: "\(report.skills.filter { $0.status == "global" }.count)", note: "profiles/global.json")
            DSMetricCard(label: L10n.dormant, value: "\(report.dormantCount)", note: L10n.updateGitSourcesNote)
        }
    }

    private func sourceSection(_ report: SkillReport) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.md) {
                HStack {
                    Text(L10n.skillSources).font(DSTypography.heading)
                    Spacer()
                    DSPathActions(path: report.hubPath)
                }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 280), spacing: DSSpacing.md)], spacing: DSSpacing.md) {
                    ForEach(report.sources) { source in
                        HStack(spacing: DSSpacing.sm) {
                            VStack(alignment: .leading, spacing: DSSpacing.xs) {
                                HStack(spacing: DSSpacing.sm) {
                                    Text(source.id).font(DSTypography.body).fontWeight(.medium)
                                    DSBadge(text: source.type, tone: .neutral)
                                }
                                Text(source.revision ?? source.ref ?? L10n.ready)
                                    .font(DSTypography.mono)
                                    .foregroundStyle(DSColor.textMuted)
                            }
                            Spacer()
                            DSPathActions(path: source.path)
                        }
                        .padding(DSSpacing.md)
                        .background(DSColor.sidebar, in: RoundedRectangle(cornerRadius: DSRadius.medium))
                    }
                }
                Text(L10n.updateGitSourcesNote)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textMuted)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func skillSection(_ report: SkillReport) -> some View {
        DSCard {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: DSSpacing.md) {
                    Text(L10n.skillInventory).font(DSTypography.heading)
                    TextField(L10n.searchSkills, text: $query)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 320)
                    Picker("", selection: $filter) {
                        ForEach(SkillFilter.allCases) { item in
                            Text(item.label).tag(item)
                        }
                    }
                    .labelsHidden()
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 420)
                    Spacer()
                    Text("\(filteredSkills.count)/\(report.skills.count)")
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textMuted)
                }
                .padding(.bottom, DSSpacing.md)

                LazyVStack(spacing: 0) {
                    ForEach(Array(filteredSkills.enumerated()), id: \.element.id) { index, skill in
                        SkillRow(skill: skill)
                        if index < filteredSkills.count - 1 {
                            Divider().overlay(DSColor.separator)
                        }
                    }
                }

                if filteredSkills.isEmpty {
                    Text(L10n.noMatchingSkills)
                        .font(DSTypography.body)
                        .foregroundStyle(DSColor.textMuted)
                        .padding(.vertical, DSSpacing.xl)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private enum SkillFilter: String, CaseIterable, Identifiable {
    case all
    case dormant
    case project
    case global
    case missing

    var id: String { rawValue }
    var label: String {
        switch self {
        case .all: return "全部"
        case .dormant: return L10n.dormant
        case .project: return L10n.projectActive
        case .global: return L10n.globalActive
        case .missing: return L10n.missingSkill
        }
    }
}

private struct SkillRow: View {
    let skill: SkillInfo

    private var stateLabel: String {
        switch skill.status {
        case "global": return L10n.globalActive
        case "project": return L10n.projectActive
        case "missing": return L10n.missingSkill
        default: return L10n.dormant
        }
    }

    var body: some View {
        HStack(alignment: .center, spacing: DSSpacing.lg) {
            Image(systemName: skill.status == "dormant" ? "shippingbox" : skill.exists ? "checkmark.circle" : "exclamationmark.circle")
                .foregroundStyle(skill.exists ? DSColor.textPrimary : DSColor.textMuted)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: DSSpacing.xs) {
                HStack(spacing: DSSpacing.sm) {
                    Text(skill.name).font(DSTypography.heading)
                    DSBadge(text: stateLabel, tone: skill.status == "global" ? .good : .neutral)
                    DSBadge(text: skill.source, tone: .neutral)
                }
                Text(skill.profiles.isEmpty ? skill.path : skill.profiles.joined(separator: " · "))
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textMuted)
            }

            Spacer()

            if !skill.absolutePath.isEmpty {
                Text(skill.absolutePath)
                    .font(DSTypography.mono)
                    .foregroundStyle(DSColor.textSecondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .frame(maxWidth: 380, alignment: .trailing)
                    .textSelection(.enabled)
                DSPathActions(path: skill.absolutePath)
            }
        }
        .padding(.vertical, DSSpacing.compact)
    }
}
