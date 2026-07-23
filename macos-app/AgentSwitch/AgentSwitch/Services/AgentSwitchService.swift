// [INPUT]: Foundation, Process, AgentModels
// [OUTPUT]: AgentSwitchService — async interface to the Python CLI backend and private secret reveal
// [POS]: Services — bridges Swift app to Python agent-switch CLI
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import Foundation
import Darwin

actor AgentSwitchService {
    private let pythonPath: String
    private let projectRoot: String?
    private let cliPath: String?

    init() {
        self.projectRoot = Self.findProjectRoot()
        self.pythonPath = Self.findPythonPath()
        self.cliPath = Self.findCLIPath()
    }

    private static func findProjectRoot() -> String? {
        let candidates = [
            NSHomeDirectory() + "/Agent-Workspace/agent-switch",
            "/usr/local/share/agent-switch",
        ]
        for path in candidates {
            if FileManager.default.fileExists(atPath: path + "/src/agent_switch/cli.py") {
                return path
            }
        }
        return nil
    }

    private static func findCLIPath() -> String? {
        let environment = ProcessInfo.processInfo.environment
        let home = NSHomeDirectory()
        let candidates = [
            environment["AGENT_SWITCH_CLI"],
            home + "/.local/bin/agent-switch",
            "/opt/homebrew/bin/agent-switch",
            "/usr/local/bin/agent-switch",
        ].compactMap { $0 }
        return candidates.first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    private static func findPythonPath() -> String {
        let environment = ProcessInfo.processInfo.environment
        let candidates = [
            environment["AGENT_SWITCH_PYTHON"],
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ].compactMap { $0 }

        for path in candidates where FileManager.default.isExecutableFile(atPath: path) {
            return path
        }
        return "/usr/bin/python3"
    }

    func runDoctor(includeCCSwitch: Bool = false) async throws -> DoctorReport {
        var arguments = ["doctor", "--json"]
        if !includeCCSwitch { arguments.append("--no-ccswitch") }
        let output = try await runCLI(arguments)
        return try JSONDecoder().decode(DoctorReport.self, from: Data(output.utf8))
    }

    func runReconcile(includeCCSwitch: Bool = false) async throws -> String {
        var arguments = ["reconcile", "--json"]
        if !includeCCSwitch { arguments.append("--no-ccswitch") }
        return try await runCLI(arguments)
    }

    func getConfig() async throws -> ConfigInfo {
        let configPath = NSHomeDirectory() + "/.config/agent-switch/config.json"
        if !FileManager.default.fileExists(atPath: configPath) {
            _ = try await runCLI(["write-default-config"])
        }
        if let data = FileManager.default.contents(atPath: configPath) {
            return try JSONDecoder().decode(ConfigInfo.self, from: data)
        }
        throw ServiceError.configNotFound
    }

    func getAgents() async throws -> [AgentInfo] {
        let output = try await runCLI(["agents", "--json"])
        return try JSONDecoder().decode(AgentReport.self, from: Data(output.utf8)).agents
    }

    func getCLIs() async throws -> [CLIInfo] {
        let output = try await runCLI(["clis", "--json"])
        return try JSONDecoder().decode(CLIReport.self, from: Data(output.utf8)).clis
    }

    func getSkills() async throws -> SkillReport {
        let output = try await runCLI(["skills", "--json"])
        return try JSONDecoder().decode(SkillReport.self, from: Data(output.utf8))
    }

    func updateSkills() async throws -> SkillReport {
        _ = try await runCLI(["skills", "update", "--json"])
        return try await getSkills()
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
    ) async throws {
        var arguments = ["mcp", "set", id, "--name", name, "--command", command]
        arguments += args.map { "--arg=\($0)" }
        arguments += secrets.map { "--secret=\($0)" }
        arguments += env.sorted { $0.key < $1.key }.map { "--env=\($0.key)=\($0.value)" }
        if apps.claude { arguments += ["--app", "claude"] }
        if apps.claude_desktop { arguments += ["--app", "claude_desktop"] }
        if apps.codex { arguments += ["--app", "codex"] }
        if apps.hermes { arguments += ["--app", "hermes"] }
        if let description, !description.isEmpty { arguments += ["--description", description] }
        if !enabled { arguments.append("--disabled") }
        arguments.append("--json")
        _ = try await runCLI(arguments)
    }

    func removeMCP(id: String) async throws {
        _ = try await runCLI(["mcp", "remove", id, "--json"])
    }

    func setMCPEnabled(id: String, enabled: Bool) async throws {
        _ = try await runCLI(["mcp", enabled ? "enable" : "disable", id, "--json"])
    }

    func importMCPs(includeCCSwitch: Bool = false) async throws {
        var arguments = ["mcp", "import", "--adopt", "--json"]
        if !includeCCSwitch { arguments.append("--no-ccswitch") }
        _ = try await runCLI(arguments)
    }

    func previewMCPImport() async throws -> MCPImportPreview {
        let output = try await runCLI(["mcp", "import", "--dry-run", "--json"])
        return try JSONDecoder().decode(MCPImportPreview.self, from: Data(output.utf8))
    }

    func setSecret(name: String, value: String) async throws {
        _ = try await runCLI(["secret", "set", "--stdin", name], stdin: Data(value.utf8))
    }

    func deleteSecret(name: String) async throws {
        _ = try await runCLI(["secret", "delete", name])
    }

    func revealSecret(name: String) async throws -> String {
        return try await readSecretThroughPrivateFIFO(name: name)
    }

    private func readSecretThroughPrivateFIFO(name: String) async throws -> String {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("agent-switch-secret-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700]
        )
        let fifo = directory.appendingPathComponent("value.pipe")
        guard mkfifo(fifo.path, S_IRUSR | S_IWUSR) == 0 else {
            try? FileManager.default.removeItem(at: directory)
            throw ServiceError.fifoCreationFailed(String(cString: strerror(errno)))
        }
        defer { try? FileManager.default.removeItem(at: directory) }

        let readTask = Task.detached(priority: .userInitiated) {
            let handle = try FileHandle(forReadingFrom: fifo)
            defer { try? handle.close() }
            return try handle.readToEnd() ?? Data()
        }
        do {
            let useInstalledCLI = projectRoot == nil && cliPath != nil
            let executable = useInstalledCLI ? cliPath! : pythonPath
            let command: String
            let arguments: [String]
            if useInstalledCLI {
                command = "exec \"$1\" secret get --fd 3 \"$2\" 3>\"$3\""
                arguments = ["-c", command, "agent-switch-secret", executable, name, fifo.path]
            } else {
                command = "exec \"$1\" -m agent_switch secret get --fd 3 \"$2\" 3>\"$3\""
                arguments = ["-c", command, "agent-switch-secret", executable, name, fifo.path]
            }
            _ = try await runProcess(
                executable: "/bin/zsh",
                arguments: arguments
            )
            let data = try await readTask.value
            guard let value = String(data: data, encoding: .utf8), !value.isEmpty else {
                throw ServiceError.invalidSecretResponse
            }
            return value
        } catch {
            readTask.cancel()
            throw error
        }
    }

    private func runCLI(_ arguments: [String], stdin: Data? = nil) async throws -> String {
        if projectRoot == nil, let cliPath {
            return try await runProcess(executable: cliPath, arguments: arguments, stdin: stdin)
        }
        return try await runProcess(executable: pythonPath, arguments: ["-m", "agent_switch"] + arguments, stdin: stdin)
    }

    private func runProcess(executable: String, arguments: [String], stdin: Data? = nil) async throws -> String {
        let process = Process()
        let stdout = Pipe()
        let stderr = Pipe()
        let input = stdin.map { _ in Pipe() }

        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = arguments
        process.currentDirectoryURL = URL(fileURLWithPath: projectRoot ?? NSHomeDirectory())

        var environment = ProcessInfo.processInfo.environment
        if let projectRoot {
            environment["PYTHONPATH"] = projectRoot + "/src"
        }
        let home = NSHomeDirectory()
        environment["PATH"] = [
            home + "/.local/bin",
            home + "/.npm-global/bin",
            home + "/.bun/bin",
            home + "/.cargo/bin",
            home + "/Library/pnpm",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ].joined(separator: ":")
        process.environment = environment
        process.standardOutput = stdout
        process.standardError = stderr
        process.standardInput = input

        try process.run()

        if let stdin, let input {
            input.fileHandleForWriting.write(stdin)
            try input.fileHandleForWriting.close()
        }

        let outputData = try stdout.fileHandleForReading.readToEnd() ?? Data()
        let errorData = try stderr.fileHandleForReading.readToEnd() ?? Data()
        process.waitUntilExit()

        let output = String(data: outputData, encoding: .utf8) ?? ""
        let errorOutput = String(data: errorData, encoding: .utf8) ?? ""

        guard process.terminationStatus == 0 else {
            let detail = errorOutput.isEmpty ? output : errorOutput
            throw ServiceError.cliError(code: Int(process.terminationStatus), output: detail)
        }

        return output
    }
}

enum ServiceError: LocalizedError {
    case cliError(code: Int, output: String)
    case configNotFound
    case fifoCreationFailed(String)
    case invalidSecretResponse

    var errorDescription: String? {
        switch self {
        case .cliError(let code, let output):
            return "CLI exited with code \(code): \(output)"
        case .configNotFound:
            return "Config file not found at ~/.config/agent-switch/config.json"
        case .fifoCreationFailed(let detail):
            return "Unable to create private secret channel: \(detail)"
        case .invalidSecretResponse:
            return "Secret response was empty or invalid"
        }
    }
}
