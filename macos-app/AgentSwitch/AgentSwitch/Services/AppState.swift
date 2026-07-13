// [INPUT]: SwiftUI, AgentSwitchService, AgentModels
// [OUTPUT]: AppState — observable root state and safe Agent, CLI, Skill, and secret operations
// [POS]: Services — single source of truth for app-wide state
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

@MainActor
class AppState: ObservableObject {
    @Published var report: DoctorReport?
    @Published var config: ConfigInfo?
    @Published var agents: [AgentInfo] = []
    @Published var clis: [CLIInfo] = []
    @Published var skillReport: SkillReport?
    @Published var isLoading = false
    @Published var lastError: String?
    @Published var lastRefresh: Date?

    private let service = AgentSwitchService()

    var isHealthy: Bool {
        if lastError != nil {
            return false
        }
        guard let report else { return true }
        return !report.blocked && report.driftCount == 0
    }

    var sidebarStatusText: String {
        if isLoading {
            return L10n.checking
        }
        return isHealthy ? L10n.healthy : L10n.needsAttention
    }

    var toolCount: Int {
        report?.secrets.required.count ?? 0
    }

    func refresh() async {
        isLoading = true
        lastError = nil
        do {
            config = try await service.getConfig()
            report = try await service.runDoctor()
            agents = try await service.getAgents()
            clis = try await service.getCLIs()
            skillReport = try await service.getSkills()
            lastRefresh = Date()
        } catch {
            lastError = error.localizedDescription
        }
        isLoading = false
    }

    func runDoctor() async {
        await refresh()
    }

    func runReconcile() async {
        isLoading = true
        lastError = nil
        do {
            _ = try await service.runReconcile()
            config = try await service.getConfig()
            report = try await service.runDoctor()
            agents = try await service.getAgents()
            clis = try await service.getCLIs()
            skillReport = try await service.getSkills()
            lastRefresh = Date()
        } catch {
            lastError = error.localizedDescription
        }
        isLoading = false
    }

    func setSecret(name: String, value: String) async -> Bool {
        isLoading = true
        lastError = nil
        do {
            try await service.setSecret(name: name, value: value)
            report = try await service.runDoctor()
            lastRefresh = Date()
            isLoading = false
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func revealSecret(name: String) async -> String? {
        lastError = nil
        do {
            return try await service.revealSecret(name: name)
        } catch {
            lastError = error.localizedDescription
            return nil
        }
    }

    func deleteSecret(name: String) async -> Bool {
        isLoading = true
        lastError = nil
        do {
            try await service.deleteSecret(name: name)
            report = try await service.runDoctor()
            lastRefresh = Date()
            isLoading = false
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func updateSkills() async -> Bool {
        isLoading = true
        lastError = nil
        do {
            skillReport = try await service.updateSkills()
            lastRefresh = Date()
            isLoading = false
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }
}
