// [INPUT]: AppKit lifecycle, SwiftUI content, AppState, L10n
// [OUTPUT]: macOS app entry point with a guaranteed main window and menu commands
// [POS]: Root app lifecycle; owns window creation and menu structure
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI
import AppKit

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let appState = AppState()
    private var window: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        configureMenu()
        DispatchQueue.main.async { [weak self] in
            self?.openMainWindow()
            NSApp.activate(ignoringOtherApps: true)
        }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            openMainWindow()
        }
        return true
    }

    func applicationDidBecomeActive(_ notification: Notification) {
        openMainWindow()
    }

    private func openMainWindow() {
        if let window {
            window.makeKeyAndOrderFront(nil)
            window.orderFrontRegardless()
            NSRunningApplication.current.activate(options: [.activateAllWindows])
            return
        }

        let rootView = NSHostingController(
            rootView:
            ContentView()
                .environmentObject(appState)
                .frame(minWidth: 820, minHeight: 560)
        )

        let window = NSWindow(contentViewController: rootView)
        window.title = L10n.appName
        window.setContentSize(NSSize(width: 1080, height: 760))
        window.minSize = NSSize(width: 820, height: 560)
        window.styleMask = [.titled, .closable, .miniaturizable, .resizable]
        window.titlebarAppearsTransparent = false
        window.isReleasedWhenClosed = false
        window.center()
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()
        self.window = window
        NSRunningApplication.current.activate(options: [.activateAllWindows])
    }

    private func configureMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu(title: L10n.appName)
        appMenu.addItem(NSMenuItem(title: "About \(L10n.appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit \(L10n.appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        let actionsMenuItem = NSMenuItem()
        let actionsMenu = NSMenu(title: L10n.actions)
        actionsMenu.addItem(menuItem(title: L10n.runDoctor, action: #selector(runDoctor), key: "D"))
        actionsMenu.addItem(menuItem(title: L10n.reconcile, action: #selector(reconcile), key: "R"))
        actionsMenu.addItem(NSMenuItem.separator())
        actionsMenu.addItem(menuItem(title: L10n.refresh, action: #selector(refresh), key: "r"))
        actionsMenuItem.submenu = actionsMenu
        mainMenu.addItem(actionsMenuItem)

        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(NSMenuItem(title: "Minimize", action: #selector(NSWindow.miniaturize(_:)), keyEquivalent: "m"))
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)
        NSApp.windowsMenu = windowMenu

        NSApp.mainMenu = mainMenu
    }

    private func menuItem(title: String, action: Selector, key: String) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = self
        return item
    }

    @objc private func runDoctor() {
        Task { await appState.runDoctor() }
    }

    @objc private func reconcile() {
        Task { await appState.runReconcile() }
    }

    @objc private func refresh() {
        Task { await appState.refresh() }
    }
}

@main
enum AgentSwitchMain {
    @MainActor private static var delegate: AppDelegate?

    @MainActor
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        let appDelegate = AppDelegate()
        delegate = appDelegate
        app.delegate = appDelegate
        app.run()
    }
}
