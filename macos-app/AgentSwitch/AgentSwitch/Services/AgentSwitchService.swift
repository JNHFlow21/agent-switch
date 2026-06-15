// [INPUT]: Foundation, Process (shell execution), AgentModels
// [OUTPUT]: AgentSwitchService — async interface to the Python CLI backend
// [POS]: Services — bridges Swift app to Python agent-switch CLI
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import Foundation

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

    private func runCLI(_ arguments: [String]) async throws -> String {
        let process = Process()
        let stdout = Pipe()
        let stderr = Pipe()

        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = ["-m", "agent_switch"] + arguments
        process.currentDirectoryURL = URL(fileURLWithPath: projectRoot)

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = projectRoot + "/src"
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        process.environment = environment
        process.standardOutput = stdout
        process.standardError = stderr

        try process.run()

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

    var errorDescription: String? {
        switch self {
        case .cliError(let code, let output):
            return "CLI exited with code \(code): \(output)"
        case .configNotFound:
            return "Config file not found at ~/.config/agent-switch/config.json"
        }
    }
}
