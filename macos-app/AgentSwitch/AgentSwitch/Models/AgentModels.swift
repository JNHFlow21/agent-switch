// [INPUT]: Foundation, AgentSwitch Python CLI
// [OUTPUT]: Data models mirroring Python DoctorReport, ToolSpec, SecretReport
// [POS]: Models layer — shared data structures decoded from CLI JSON output
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import Foundation

struct DoctorReport: Codable {
    let blocked: Bool
    let driftCount: Int
    let findings: [Finding]
    let changes: [PlannedChange]
    let secrets: SecretInfo
}

struct Finding: Codable, Identifiable {
    let severity: String
    let target: String
    let message: String

    var id: String { "\(target)-\(message)" }
}

struct PlannedChange: Codable, Identifiable {
    let target: String
    let action: String
    let path: String?
    let detail: String

    var id: String { "\(target)-\(action)-\(detail)" }
}

struct SecretInfo: Codable {
    let path: String
    let exists: Bool
    let required: [String]
    let missing: [String]
    let presentNames: [String]
}

struct ToolInfo: Codable, Identifiable {
    let id: String
    let name: String
    let command: String
    let args: [String]
    let requiredSecrets: [String]
    let apps: AppFlags
    let envNames: [String]
    let description: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case command
        case args
        case requiredSecrets
        case apps
        case envNames
        case description
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decodeIfPresent(String.self, forKey: .name) ?? id
        command = try container.decode(String.self, forKey: .command)
        args = try container.decodeIfPresent([String].self, forKey: .args) ?? []
        requiredSecrets = try container.decodeIfPresent([String].self, forKey: .requiredSecrets) ?? []
        apps = try container.decodeIfPresent(AppFlags.self, forKey: .apps) ?? AppFlags()
        envNames = try container.decodeIfPresent([String].self, forKey: .envNames) ?? []
        description = try container.decodeIfPresent(String.self, forKey: .description)
    }

    var displayCommand: String {
        ([command] + args).joined(separator: " ")
    }
}

struct AppFlags: Codable {
    let claude: Bool
    let claude_desktop: Bool
    let codex: Bool
    let hermes: Bool

    init(claude: Bool = true, claude_desktop: Bool = true, codex: Bool = true, hermes: Bool = true) {
        self.claude = claude
        self.claude_desktop = claude_desktop
        self.codex = codex
        self.hermes = hermes
    }

    enum CodingKeys: String, CodingKey {
        case claude
        case claude_desktop
        case codex
        case hermes
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        claude = try container.decodeIfPresent(Bool.self, forKey: .claude) ?? true
        claude_desktop = try container.decodeIfPresent(Bool.self, forKey: .claude_desktop) ?? true
        codex = try container.decodeIfPresent(Bool.self, forKey: .codex) ?? true
        hermes = try container.decodeIfPresent(Bool.self, forKey: .hermes) ?? true
    }

    var enabledApps: [String] {
        var result: [String] = []
        if claude { result.append("Claude Code") }
        if claude_desktop { result.append("Claude Desktop") }
        if codex { result.append("Codex") }
        if hermes { result.append("Hermes") }
        return result
    }
}

struct ConfigInfo: Codable {
    let tools: [ToolInfo]
    let routes: RouteInfo
    let secretFile: String
}

struct RouteInfo: Codable {
    let searchDefault: String
    let xReadDefault: String
    let xReadFallback: String
}

struct ReconcileSummary: Codable {
    let changed: Int
    let unchanged: Int
    let blocked: Int
}
