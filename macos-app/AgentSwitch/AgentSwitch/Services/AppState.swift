// [INPUT]: SwiftUI, AgentSwitchService, AgentModels
// [OUTPUT]: AppState — observable root state object
// [POS]: Services — single source of truth for app-wide state
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

@MainActor
class AppState: ObservableObject {
    @Published var report: DoctorReport?
    @Published var config: ConfigInfo?
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
            lastRefresh = Date()
        } catch {
            lastError = error.localizedDescription
        }
        isLoading = false
    }
}
