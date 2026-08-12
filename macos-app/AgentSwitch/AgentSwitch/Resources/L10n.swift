// [INPUT]: Foundation
// [OUTPUT]: L10n — centralized UI strings with Chinese/English support
// [POS]: Resources — single source for all user-facing text
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import Foundation

enum AppVersion {
    static let current = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.3.0"
}

enum L10n {
    private static func localized(_ key: String.LocalizationValue) -> String {
#if SWIFT_PACKAGE
        String(localized: key, bundle: .module)
#else
        String(localized: key, bundle: .main)
#endif
    }

    // MARK: - Sidebar
    static let appName = localized("appName")
    static let dashboard = localized("dashboard")
    static let agents = localized("agents")
    static let clis = localized("clis")
    static let skills = localized("skills")
    static let mcpTools = localized("mcpTools")
    static let secrets = localized("secrets")
    static let settings = localized("settings")
    static let healthy = localized("healthy")
    static let needsAttention = localized("needsAttention")
    static let checking = localized("checking")

    // MARK: - Dashboard
    static let lastRefreshed = localized("lastRefreshed")
    static let blocked = localized("blocked")
    static let ready = localized("ready")
    static let drift = localized("drift")
    static let runtimeState = localized("runtimeState")
    static let driftChanges = localized("driftChanges")
    static let findingsLabel = localized("findingsLabel")
    static let secretsLabel = localized("secretsLabel")
    static let noDriftDetected = localized("noDriftDetected")
    static let reviewPlannedChanges = localized("reviewPlannedChanges")
    static let allTargetsInSync = localized("allTargetsInSync")
    static let runReconcileToFix = localized("runReconcileToFix")
    static let noIssuesFound = localized("noIssuesFound")
    static let errors = localized("errors")
    static let allPresent = localized("allPresent")
    static let missing = localized("missing")
    static let loadFailed = localized("loadFailed")

    // MARK: - Routes
    static let accessRoutes = localized("accessRoutes")
    static let searchDefault = localized("searchDefault")
    static let xReader = localized("xReader")
    static let xFallback = localized("xFallback")

    // MARK: - Findings
    static let findings = localized("findings")
    static let noFindingsHealthy = localized("noFindingsHealthy")
    static let plannedChanges = localized("plannedChanges")
    static let noPlannedChanges = localized("noPlannedChanges")

    // MARK: - Tools
    static let managedMCPTools = localized("managedMCPTools")
    static let loadingTools = localized("loadingTools")
    static let targets = localized("targets")
    static let secretsSection = localized("secretsSection")
    static let command = localized("command")
    static let readyState = localized("readyState")
    static let missingSecrets = localized("missingSecrets")
    static let driftState = localized("driftState")
    static let addMCP = localized("addMCP")
    static let editMCP = localized("editMCP")
    static let removeMCP = localized("removeMCP")
    static let removeMCPConfirmation = localized("removeMCPConfirmation")
    static let enableMCP = localized("enableMCP")
    static let disableMCP = localized("disableMCP")
    static let disabledMCP = localized("disabledMCP")
    static let importMCPs = localized("importMCPs")
    static let importAndAdoptMCPs = localized("importAndAdoptMCPs")
    static let importMCPConfirmation = localized("importMCPConfirmation")
    static let discoveredMCPs = localized("discoveredMCPs")
    static let supportedMCPs = localized("supportedMCPs")
    static let skippedMCPs = localized("skippedMCPs")
    static let secretNamesOnly = localized("secretNamesOnly")
    static let none = localized("none")
    static let saveMCP = localized("saveMCP")
    static let mcpID = localized("mcpID")
    static let mcpName = localized("mcpName")
    static let mcpCommand = localized("mcpCommand")
    static let mcpDescription = localized("mcpDescription")
    static let mcpArguments = localized("mcpArguments")
    static let mcpRequiredSecrets = localized("mcpRequiredSecrets")
    static let mcpEnvironment = localized("mcpEnvironment")
    static let mcpEditorNote = localized("mcpEditorNote")

    // MARK: - Secrets
    static let secretsInventory = localized("secretsInventory")
    static let secretManagementSubtitle = localized("secretManagementSubtitle")
    static let secretFile = localized("secretFile")
    static let found = localized("found")
    static let missingFile = localized("missingFile")
    static let present = localized("present")
    static let ofRequired = localized("ofRequired")
    static let requiredSuffix = localized("requiredSuffix")
    static let allSecretsConfigured = localized("allSecretsConfigured")
    static let requiredSecrets = localized("requiredSecrets")
    static let presentBadge = localized("presentBadge")
    static let missingBadge = localized("missingBadge")
    static let secretFileLocation = localized("secretFileLocation")
    static let revealInFinder = localized("revealInFinder")
    static let secretsRuntimeNote = localized("secretsRuntimeNote")
    static let noSecretInfo = localized("noSecretInfo")
    static let runDoctorForSecrets = localized("runDoctorForSecrets")
    static let stored = localized("stored")
    static let storedSecrets = localized("storedSecrets")
    static let storedSecretsNote = localized("storedSecretsNote")
    static let requiredSecretsNote = localized("requiredSecretsNote")
    static let allSecrets = localized("allSecrets")
    static let noStoredSecrets = localized("noStoredSecrets")
    static let addSecret = localized("addSecret")
    static let updateSecret = localized("updateSecret")
    static let deleteSecret = localized("deleteSecret")
    static let deleteSecretConfirmation = localized("deleteSecretConfirmation")
    static let revealSecret = localized("revealSecret")
    static let hideSecret = localized("hideSecret")
    static let copySecret = localized("copySecret")
    static let configureSecret = localized("configureSecret")
    static let notConfigured = localized("notConfigured")
    static let requiredBadge = localized("requiredBadge")
    static let secretEditorNote = localized("secretEditorNote")
    static let usedByMCP = localized("usedByMCP")
    static let secretName = localized("secretName")
    static let secretNameLabel = localized("secretNameLabel")
    static let secretValue = localized("secretValue")
    static let cancel = localized("cancel")

    // MARK: - CLI management
    static let cliManagement = localized("cliManagement")
    static let cliManagementSubtitle = localized("cliManagementSubtitle")
    static let installed = localized("installed")
    static let notInstalled = localized("notInstalled")
    static let packageManager = localized("packageManager")
    static let installedCLIs = localized("installedCLIs")
    static let cliInventory = localized("cliInventory")
    static let cliUpdateNote = localized("cliUpdateNote")

    // MARK: - Skill management
    static let skillWarehouse = localized("skillWarehouse")
    static let skillWarehouseSubtitle = localized("skillWarehouseSubtitle")
    static let skillSources = localized("skillSources")
    static let skillProfiles = localized("skillProfiles")
    static let skillInventory = localized("skillInventory")
    static let allSkills = localized("allSkills")
    static let dormant = localized("dormant")
    static let projectActive = localized("projectActive")
    static let globalActive = localized("globalActive")
    static let missingSkill = localized("missingSkill")
    static let searchSkills = localized("searchSkills")
    static let updateGitSources = localized("updateGitSources")
    static let updateGitSourcesNote = localized("updateGitSourcesNote")
    static let noMatchingSkills = localized("noMatchingSkills")

    // MARK: - File actions
    static let openFile = localized("openFile")
    static let syncAndCheck = localized("syncAndCheck")

    // MARK: - Agent management
    static let agentManagement = localized("agentManagement")
    static let agentManagementSubtitle = localized("agentManagementSubtitle")
    static let managed = localized("managed")
    static let detected = localized("detected")
    static let notDetected = localized("notDetected")
    static let notManaged = localized("notManaged")
    static let synchronized = localized("synchronized")
    static let needsSync = localized("needsSync")
    static let manageDetectedAgents = localized("manageDetectedAgents")
    static let manageDetectedAgentsNote = localized("manageDetectedAgentsNote")
    static let howManagementWorks = localized("howManagementWorks")
    static let howManagementWorksBody = localized("howManagementWorksBody")
    static let welcomeHeading = localized("welcomeHeading")
    static let welcomeBody = localized("welcomeBody")
    static let startManagement = localized("startManagement")
    static let notNow = localized("notNow")

    // MARK: - Settings
    static let general = localized("general")
    static let autoRefreshOnLaunch = localized("autoRefreshOnLaunch")
    static let includeCCSwitch = localized("includeCCSwitch")
    static let runtimePaths = localized("runtimePaths")
    static let config = localized("config")
    static let secretsPath = localized("secretsPath")
    static let wrappers = localized("wrappers")
    static let backups = localized("backups")
    static let targetConfigs = localized("targetConfigs")
    static let about = localized("about")
    static let version = localized("version")
    static let repository = localized("repository")

    // MARK: - Actions (menu)
    static let actions = localized("actions")
    static let aboutAgentSwitch = localized("aboutAgentSwitch")
    static let quitAgentSwitch = localized("quitAgentSwitch")
    static let window = localized("window")
    static let showAgentSwitch = localized("showAgentSwitch")
    static let minimize = localized("minimize")
}
