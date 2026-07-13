// [INPUT]: Foundation, Process, AgentModels
// [OUTPUT]: AgentSwitchService — async interface to the Python CLI backend and private secret reveal
// [POS]: Services — bridges Swift app to Python agent-switch CLI
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import Foundation
import Darwin

actor AgentSwitchService {
    private let pythonPath: String
    private let projectRoot: String

    init() {
        self.projectRoot = Self.findProjectRoot()
        self.pythonPath = Self.findPythonPath()
    }

    private static func findProjectRoot() -> String {
        let candidates = [
            NSHomeDirectory() + "/Agent-Workspace/agent-switch",
            "/usr/local/share/agent-switch",
        ]
        for path in candidates {
            if FileManager.default.fileExists(atPath: path + "/src/agent_switch/cli.py") {
                return path
            }
        }
        return candidates[0]
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

    func runDoctor() async throws -> DoctorReport {
        let output = try await runCLI(["doctor", "--json", "--no-ccswitch"])
        return try JSONDecoder().decode(DoctorReport.self, from: Data(output.utf8))
    }

    func runReconcile() async throws -> String {
        return try await runCLI(["reconcile", "--json", "--no-ccswitch"])
    }

    func getConfig() async throws -> ConfigInfo {
        let configPath = NSHomeDirectory() + "/.config/agent-switch/config.json"
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
            let command = "exec \"$1\" -m agent_switch secret get --fd 3 \"$2\" 3>\"$3\""
            _ = try await runProcess(
                executable: "/bin/zsh",
                arguments: ["-c", command, "agent-switch-secret", pythonPath, name, fifo.path]
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
        try await runProcess(
            executable: pythonPath,
            arguments: ["-m", "agent_switch"] + arguments,
            stdin: stdin
        )
    }

    private func runProcess(executable: String, arguments: [String], stdin: Data? = nil) async throws -> String {
        let process = Process()
        let stdout = Pipe()
        let stderr = Pipe()
        let input = stdin.map { _ in Pipe() }

        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = arguments
        process.currentDirectoryURL = URL(fileURLWithPath: projectRoot)

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = projectRoot + "/src"
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
