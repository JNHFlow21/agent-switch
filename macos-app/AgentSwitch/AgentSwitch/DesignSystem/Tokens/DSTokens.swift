// [INPUT]: SwiftUI
// [OUTPUT]: Graphite-on-paper DSColor, DSTypography, DSSpacing, DSRadius tokens
// [POS]: DesignSystem/Tokens — consumed by all feature views and components
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

// MARK: - Color Tokens

enum DSColor {
    static let background = Color.white
    static let sidebar = Color(red: 0.976, green: 0.976, blue: 0.976)
    static let surface = Color.white
    static let surfaceRaised = Color.white
    static let primary = graphite
    static let accent = graphite
    static let textPrimary = graphite
    static let textSecondary = Color(red: 0.365, green: 0.365, blue: 0.365)
    static let textMuted = Color(red: 0.561, green: 0.561, blue: 0.561)
    static let separator = Color.black.opacity(0.10)
    static let hover = Color.black.opacity(0.05)
    static let pressed = Color.black
    static let edge = Color(red: 0.902, green: 0.902, blue: 0.902)

    private static let graphite = Color(red: 0.051, green: 0.051, blue: 0.051)

    static let statusGood = graphite
    static let statusGoodBg = sidebar
    static let statusWarn = textSecondary
    static let statusWarnBg = sidebar
    static let statusBad = graphite
    static let statusBadBg = edge
    static let statusInfo = textSecondary
    static let statusInfoBg = sidebar
}

// MARK: - Typography

enum DSTypography {
    static let title = Font.system(size: 24, weight: .semibold, design: .default)
    static let heading = Font.system(size: 16, weight: .semibold, design: .default)
    static let body = Font.system(size: 16, weight: .regular, design: .default)
    static let caption = Font.system(size: 14, weight: .regular, design: .default)
    static let mono = Font.system(size: 13, weight: .regular, design: .monospaced)
}

// MARK: - Spacing

enum DSSpacing {
    static let xs: CGFloat = 6
    static let sm: CGFloat = 8
    static let md: CGFloat = 10
    static let compact: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 20
    static let xxl: CGFloat = 24
}

// MARK: - Radius

enum DSRadius {
    static let small: CGFloat = 10
    static let medium: CGFloat = 10
    static let large: CGFloat = 10
}
