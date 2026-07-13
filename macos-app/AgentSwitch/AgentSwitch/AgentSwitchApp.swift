// [INPUT]: AppKit lifecycle, SwiftUI content, AppState, L10n
// [OUTPUT]: macOS app entry point with one stable registered application window
// [POS]: Root app lifecycle; owns window creation and menu structure
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import AppKit
import SwiftUI

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let appState = AppState()
    private var windowController: NSWindowController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        configureMenu()
        showMainWindow()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showMainWindow()
        return true
    }

    func applicationDidBecomeActive(_ notification: Notification) {
        showMainWindow()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    private func showMainWindow() {
        if let window = windowController?.window {
            placeWindowIfNeeded(window)
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        let controller = NSHostingController(
            rootView:
                ContentView()
                .environmentObject(appState)
                .frame(minWidth: 820, minHeight: 560)
        )
        let window = NSWindow(contentViewController: controller)
        window.appearance = NSAppearance(named: .aqua)
        window.title = L10n.appName
        window.styleMask = [.titled, .closable, .miniaturizable, .resizable]
        window.minSize = NSSize(width: 820, height: 560)
        window.isReleasedWhenClosed = false
        placeWindowIfNeeded(window)

        let windowController = NSWindowController(window: window)
        self.windowController = windowController
        windowController.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func placeWindowIfNeeded(_ window: NSWindow) {
        let visibleFrame = NSScreen.main?.visibleFrame ?? NSRect(x: 80, y: 80, width: 1440, height: 900)
        let targetSize = NSSize(width: min(1180, visibleFrame.width - 80), height: min(820, visibleFrame.height - 80))
        let targetOrigin = NSPoint(
            x: visibleFrame.minX + max((visibleFrame.width - targetSize.width) / 2, 40),
            y: visibleFrame.minY + max((visibleFrame.height - targetSize.height) / 2, 40)
        )
        let targetFrame = NSRect(origin: targetOrigin, size: targetSize)
        if !visibleFrame.intersects(window.frame) || window.frame.width < 820 || window.frame.height < 560 {
            window.setFrame(targetFrame, display: true)
        } else if window.frame.origin.y > visibleFrame.maxY || window.frame.origin.y < visibleFrame.minY - 40 {
            window.setFrame(targetFrame, display: true)
        } else if window.frame.origin.x > visibleFrame.maxX || window.frame.origin.x < visibleFrame.minX - 40 {
            window.setFrame(targetFrame, display: true)
        }
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
        actionsMenu.addItem(menuItem(title: L10n.syncAndCheck, action: #selector(syncAndCheck), key: "R"))
        actionsMenuItem.submenu = actionsMenu
        mainMenu.addItem(actionsMenuItem)

        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(menuItem(title: "Show \(L10n.appName)", action: #selector(showMainWindowFromMenu), key: "0"))
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

    @objc private func showMainWindowFromMenu() {
        showMainWindow()
    }

    @objc private func syncAndCheck() {
        Task { await appState.runReconcile() }
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
