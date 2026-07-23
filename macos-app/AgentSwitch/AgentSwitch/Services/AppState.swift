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
    @Published var importPreview: MCPImportPreview?
    @Published var isLoading = false
    @Published var lastError: String?
    @Published var lastRefresh: Date?

    private let service = AgentSwitchService()

    private var includeCCSwitch: Bool {
        UserDefaults.standard.bool(forKey: "includeCCSwitch")
    }

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
            report = try await service.runDoctor(includeCCSwitch: includeCCSwitch)
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
            _ = try await service.runReconcile(includeCCSwitch: includeCCSwitch)
            config = try await service.getConfig()
            report = try await service.runDoctor(includeCCSwitch: includeCCSwitch)
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
            report = try await service.runDoctor(includeCCSwitch: includeCCSwitch)
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
            report = try await service.runDoctor(includeCCSwitch: includeCCSwitch)
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

    func saveMCP(
        id: String,
        name: String,
        command: String,
        args: [String],
        secrets: [String],
        env: [String: String],
        apps: AppFlags,
        description: String?,
        enabled: Bool
    ) async -> Bool {
        isLoading = true
        lastError = nil
        do {
            try await service.saveMCP(
                id: id,
                name: name,
                command: command,
                args: args,
                secrets: secrets,
                env: env,
                apps: apps,
                description: description,
                enabled: enabled
            )
            isLoading = false
            await refresh()
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func removeMCP(id: String) async -> Bool {
        isLoading = true
        lastError = nil
        do {
            try await service.removeMCP(id: id)
            isLoading = false
            await refresh()
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func setMCPEnabled(id: String, enabled: Bool) async -> Bool {
        isLoading = true
        lastError = nil
        do {
            try await service.setMCPEnabled(id: id, enabled: enabled)
            isLoading = false
            await refresh()
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func importMCPs() async -> Bool {
        isLoading = true
        lastError = nil
        do {
            try await service.importMCPs(includeCCSwitch: includeCCSwitch)
            isLoading = false
            await refresh()
            return true
        } catch {
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func previewMCPImport() async -> Bool {
        isLoading = true
        lastError = nil
        do {
            importPreview = try await service.previewMCPImport()
            isLoading = false
            return true
        } catch {
            importPreview = nil
            lastError = error.localizedDescription
            isLoading = false
            return false
        }
    }
}
