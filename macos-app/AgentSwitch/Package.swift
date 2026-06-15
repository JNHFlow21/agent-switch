// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AgentSwitch",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "AgentSwitch",
            path: "AgentSwitch"
        ),
    ]
)
