// [INPUT]: SwiftUI
// [OUTPUT]: DSColor, DSTypography, DSSpacing, DSRadius, DSDepth semantic tokens
// [POS]: DesignSystem/Tokens — consumed by all feature views and components
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

// MARK: - Color Tokens

enum DSColor {
    static let background = Color(nsColor: .windowBackgroundColor)
    static let surface = Color(nsColor: .controlBackgroundColor)
    static let surfaceRaised = Color.white.opacity(0.92)
    static let primary = Color.accentColor
    static let accent = Color.blue
    static let textPrimary = Color(nsColor: .labelColor)
    static let textSecondary = Color(nsColor: .secondaryLabelColor)
    static let separator = Color(nsColor: .separatorColor)

    static let statusGood = Color(red: 0.03, green: 0.45, blue: 0.26)
    static let statusGoodBg = Color(red: 0.91, green: 0.97, blue: 0.93)
    static let statusWarn = Color(red: 0.71, green: 0.28, blue: 0.03)
    static let statusWarnBg = Color(red: 1.0, green: 0.95, blue: 0.87)
    static let statusBad = Color(red: 0.70, green: 0.14, blue: 0.09)
    static let statusBadBg = Color(red: 1.0, green: 0.89, blue: 0.88)
    static let statusInfo = Color(red: 0.20, green: 0.29, blue: 0.76)
    static let statusInfoBg = Color(red: 0.93, green: 0.95, blue: 1.0)
}

// MARK: - Typography

enum DSTypography {
    static let title = Font.system(size: 22, weight: .bold, design: .default)
    static let heading = Font.system(size: 16, weight: .semibold, design: .default)
    static let body = Font.system(size: 13, weight: .regular, design: .default)
    static let caption = Font.system(size: 11, weight: .medium, design: .default)
    static let mono = Font.system(size: 12, weight: .regular, design: .monospaced)
}

// MARK: - Spacing

enum DSSpacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 24
    static let xxl: CGFloat = 32
}

// MARK: - Radius

enum DSRadius {
    static let small: CGFloat = 6
    static let medium: CGFloat = 10
    static let large: CGFloat = 14
}

// MARK: - Depth (shadows)

enum DSDepth {
    static let card = ShadowStyle(color: .black.opacity(0.06), radius: 8, x: 0, y: 3)
    static let raised = ShadowStyle(color: .black.opacity(0.1), radius: 12, x: 0, y: 4)
}

struct ShadowStyle {
    let color: Color
    let radius: CGFloat
    let x: CGFloat
    let y: CGFloat
}
