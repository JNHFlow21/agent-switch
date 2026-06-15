// [INPUT]: Foundation
// [OUTPUT]: L10n — centralized UI strings with Chinese/English support
// [POS]: Resources — single source for all user-facing text
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import Foundation

enum L10n {
    // MARK: - Sidebar
    static let appName = String(localized: "Agent Switch", comment: "App name")
    static let dashboard = String(localized: "仪表板", comment: "Sidebar: Dashboard")
    static let mcpTools = String(localized: "MCP 工具", comment: "Sidebar: MCP Tools")
    static let secrets = String(localized: "密钥管理", comment: "Sidebar: Secrets")
    static let settings = String(localized: "设置", comment: "Sidebar: Settings")
    static let healthy = String(localized: "运行正常", comment: "Status: healthy")
    static let needsAttention = String(localized: "需要关注", comment: "Status: needs attention")
    static let checking = String(localized: "检查中", comment: "Status: checking")

    // MARK: - Dashboard
    static let lastRefreshed = String(localized: "上次刷新：", comment: "Dashboard header")
    static let refresh = String(localized: "刷新", comment: "Toolbar: Refresh")
    static let reconcile = String(localized: "修复同步", comment: "Toolbar: Reconcile")
    static let blocked = String(localized: "已阻塞", comment: "State: blocked")
    static let ready = String(localized: "就绪", comment: "State: ready")
    static let drift = String(localized: "漂移", comment: "Drift suffix")
    static let runtimeState = String(localized: "运行状态", comment: "Metric: runtime state")
    static let driftChanges = String(localized: "漂移变更", comment: "Metric: drift changes")
    static let findingsLabel = String(localized: "检查结果", comment: "Metric: findings")
    static let secretsLabel = String(localized: "密钥状态", comment: "Metric: secrets")
    static let noDriftDetected = String(localized: "无漂移", comment: "Metric note")
    static let reviewPlannedChanges = String(localized: "请检查计划变更", comment: "Metric note")
    static let allTargetsInSync = String(localized: "所有目标已同步", comment: "Metric note")
    static let runReconcileToFix = String(localized: "运行修复以解决", comment: "Metric note")
    static let noIssuesFound = String(localized: "无问题", comment: "Metric note")
    static let errors = String(localized: "个错误", comment: "Error count suffix")
    static let allPresent = String(localized: "全部就位", comment: "Metric note")
    static let missing = String(localized: "缺失", comment: "Missing suffix")
    static let loadFailed = String(localized: "加载失败", comment: "Dashboard error")

    // MARK: - Routes
    static let accessRoutes = String(localized: "访问路由", comment: "Section: Access Routes")
    static let searchDefault = String(localized: "搜索默认", comment: "Route: search default")
    static let xReader = String(localized: "X 阅读器", comment: "Route: X reader")
    static let xFallback = String(localized: "X 备用", comment: "Route: X fallback")

    // MARK: - Findings
    static let findings = String(localized: "检查发现", comment: "Section: Findings")
    static let noFindingsHealthy = String(localized: "无异常发现，所有托管资源运行正常。", comment: "Empty findings")
    static let plannedChanges = String(localized: "计划变更", comment: "Section: Planned Changes")
    static let noPlannedChanges = String(localized: "无计划变更，修复同步当前为空操作。", comment: "Empty changes")

    // MARK: - Tools
    static let managedMCPTools = String(localized: "托管 MCP 工具", comment: "Page: Tools")
    static let loadingTools = String(localized: "加载工具中…", comment: "Loading state")
    static let targets = String(localized: "目标应用", comment: "Tool row: targets")
    static let secretsSection = String(localized: "所需密钥", comment: "Tool row: secrets")
    static let command = String(localized: "命令", comment: "Tool row: command")
    static let readyState = String(localized: "就绪", comment: "Tool badge")
    static let missingSecrets = String(localized: "缺少密钥", comment: "Tool badge")
    static let driftState = String(localized: "漂移", comment: "Tool badge: drift")

    // MARK: - Secrets
    static let secretsInventory = String(localized: "密钥清单", comment: "Page: Secrets")
    static let secretFile = String(localized: "密钥文件", comment: "Metric: secret file")
    static let found = String(localized: "已找到", comment: "Secret file found")
    static let missingFile = String(localized: "文件缺失", comment: "Secret file missing")
    static let present = String(localized: "已配置", comment: "Metric: present")
    static let ofRequired = String(localized: "共需", comment: "of N required prefix")
    static let requiredSuffix = String(localized: "项", comment: "required suffix")
    static let allSecretsConfigured = String(localized: "所有密钥已配置", comment: "Metric note")
    static let requiredSecrets = String(localized: "所需密钥列表", comment: "Section: Required Secrets")
    static let presentBadge = String(localized: "已配置", comment: "Badge: present")
    static let missingBadge = String(localized: "缺失", comment: "Badge: missing")
    static let secretFileLocation = String(localized: "密钥文件位置", comment: "Section: Secret File Location")
    static let revealInFinder = String(localized: "在访达中显示", comment: "Button: Reveal in Finder")
    static let secretsRuntimeNote = String(localized: "密钥由 wrapper 脚本在运行时加载，不会嵌入应用配置文件中。", comment: "Note")
    static let noSecretInfo = String(localized: "无密钥信息", comment: "Empty state title")
    static let runDoctorForSecrets = String(localized: "运行 Doctor 以检查密钥状态", comment: "Empty state subtitle")

    // MARK: - Settings
    static let general = String(localized: "通用", comment: "Settings: General")
    static let autoRefreshOnLaunch = String(localized: "启动时自动刷新", comment: "Settings toggle")
    static let includeCCSwitch = String(localized: "Doctor 检查时包含 CC Switch 数据库", comment: "Settings toggle")
    static let runtimePaths = String(localized: "运行时路径", comment: "Settings: Runtime Paths")
    static let config = String(localized: "配置文件", comment: "Settings label")
    static let secretsPath = String(localized: "密钥文件", comment: "Settings label")
    static let wrappers = String(localized: "Wrapper 脚本", comment: "Settings label")
    static let backups = String(localized: "备份目录", comment: "Settings label")
    static let targetConfigs = String(localized: "目标配置文件", comment: "Settings: Target Configs")
    static let about = String(localized: "关于", comment: "Settings: About")
    static let version = String(localized: "版本", comment: "Settings label")
    static let repository = String(localized: "仓库地址", comment: "Settings label")

    // MARK: - Actions (menu)
    static let runDoctor = String(localized: "运行 Doctor", comment: "Menu: Run Doctor")
    static let actions = String(localized: "操作", comment: "Menu: Actions")
}
