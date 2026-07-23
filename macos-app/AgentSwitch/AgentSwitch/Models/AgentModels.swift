// [INPUT]: Foundation, AgentSwitch Python CLI
// [OUTPUT]: Data models mirroring Python doctor, Agent, CLI, Skill, and configuration reports
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
    let storedNames: [String]
    let consumers: [String: [String]]?
}

struct AgentReport: Codable {
    let agents: [AgentInfo]
}

struct AgentInfo: Codable, Identifiable {
    let id: String
    let name: String
    let detected: Bool
    let managed: Bool
    let inSync: Bool
    let configPath: String
    let instructionPath: String
}

struct CLIReport: Codable {
    let clis: [CLIInfo]
}

struct CLIInfo: Codable, Identifiable {
    let id: String
    let name: String
    let command: String
    let manager: String
    let versionArgs: [String]
    let installed: Bool
    let path: String?
    let version: String?
}

struct SkillReport: Codable {
    let hubPath: String
    let sources: [SkillSourceInfo]
    let profiles: [SkillProfileInfo]
    let skills: [SkillInfo]
    let dormantCount: Int
}

struct SkillSourceInfo: Codable, Identifiable {
    let id: String
    let type: String
    let path: String
    let ref: String?
    let revision: String?
    let updatedAt: String?
    let installed: Bool
}

struct SkillProfileInfo: Codable, Identifiable {
    let id: String
    let project: String
    let skillCount: Int
}

struct SkillInfo: Codable, Identifiable {
    let id: String
    let name: String
    let source: String
    let path: String
    let absolutePath: String
    let sourceType: String
    let ref: String?
    let revision: String?
    let profiles: [String]
    let globalActive: Bool
    let status: String
    let exists: Bool
}

struct ToolInfo: Codable, Identifiable {
    let id: String
    let name: String
    let command: String
    let args: [String]
    let requiredSecrets: [String]
    let apps: AppFlags
    let envNames: [String]
    let env: [String: String]
    let description: String?
    let enabled: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case command
        case args
        case requiredSecrets
        case apps
        case envNames
        case env
        case description
        case enabled
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decodeIfPresent(String.self, forKey: .name) ?? id
        command = try container.decode(String.self, forKey: .command)
        args = try container.decodeIfPresent([String].self, forKey: .args) ?? []
        requiredSecrets = try container.decodeIfPresent([String].self, forKey: .requiredSecrets) ?? []
        apps = try container.decodeIfPresent(AppFlags.self, forKey: .apps) ?? AppFlags()
        env = try container.decodeIfPresent([String: String].self, forKey: .env) ?? [:]
        envNames = try container.decodeIfPresent([String].self, forKey: .envNames) ?? env.keys.sorted()
        description = try container.decodeIfPresent(String.self, forKey: .description)
        enabled = try container.decodeIfPresent(Bool.self, forKey: .enabled) ?? true
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

struct MCPImportPreview: Codable {
    let dryRun: Bool
    let discovered: Int
    let supported: Int
    let imported: [String]
    let merged: [String]
    let secretNames: [String]
    let skipped: [SkippedMCPImport]
}

struct SkippedMCPImport: Codable {
    let app: String
    let id: String
    let reason: String
}
