// [INPUT]: SwiftUI, DSTokens
// [OUTPUT]: Flat graphite-on-paper page, card, badge, metric, icon, and file-path components
// [POS]: DesignSystem/Components — product-level reusable views
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI
import AppKit

// MARK: - Page

struct DSPageBadge {
    let text: String
    let tone: BadgeTone
}

struct DSPage<Content: View>: View {
    let title: String
    let subtitle: String?
    let badges: [DSPageBadge]
    let content: Content

    init(
        title: String,
        subtitle: String? = nil,
        badges: [DSPageBadge] = [],
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.subtitle = subtitle
        self.badges = badges
        self.content = content()
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DSSpacing.xl) {
                DSPageHeader(title: title, subtitle: subtitle, badges: badges)
                content
            }
            .padding(DSSpacing.xl)
            .frame(maxWidth: 1200, alignment: .leading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(DSColor.background)
    }
}

struct DSPageHeader: View {
    let title: String
    let subtitle: String?
    let badges: [DSPageBadge]

    var body: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: DSSpacing.xs) {
                Text(title)
                    .font(DSTypography.title)
                    .foregroundStyle(DSColor.textPrimary)
                if let subtitle {
                    Text(subtitle)
                        .font(DSTypography.caption)
                        .foregroundStyle(DSColor.textSecondary)
                }
            }

            Spacer()

            HStack(spacing: DSSpacing.sm) {
                ForEach(Array(badges.enumerated()), id: \.offset) { _, badge in
                    DSBadge(text: badge.text, tone: badge.tone)
                }
            }
        }
    }
}

// MARK: - Card

struct DSCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(DSSpacing.lg)
            .background(
                RoundedRectangle(cornerRadius: DSRadius.medium, style: .continuous)
                    .fill(DSColor.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: DSRadius.medium, style: .continuous)
                    .stroke(DSColor.separator, lineWidth: 1)
            )
    }
}

// MARK: - Badge

enum BadgeTone {
    case good, warn, bad, info, neutral, route, app
}

struct DSBadge: View {
    let text: String
    let tone: BadgeTone

    private var foreground: Color {
        switch tone {
        case .good: return DSColor.textPrimary
        case .warn: return DSColor.textSecondary
        case .bad: return DSColor.textPrimary
        case .info: return DSColor.textSecondary
        case .neutral: return DSColor.textSecondary
        case .route: return DSColor.statusInfo
        case .app: return DSColor.textPrimary
        }
    }

    private var background: Color {
        switch tone {
        case .good: return DSColor.statusGoodBg
        case .warn: return DSColor.statusWarnBg
        case .bad: return DSColor.statusBadBg
        case .info: return DSColor.statusInfoBg
        case .neutral: return Color(nsColor: .quaternaryLabelColor).opacity(0.3)
        case .route: return DSColor.statusInfoBg
        case .app: return DSColor.sidebar
        }
    }

    var body: some View {
        Text(text)
            .font(.system(size: 14, weight: .medium))
            .foregroundStyle(foreground)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(background)
    }
}

// MARK: - Metric Card

struct DSMetricCard: View {
    let label: String
    let value: String
    let note: String
    var tone: BadgeTone = .neutral

    var body: some View {
        DSCard {
            VStack(alignment: .leading, spacing: DSSpacing.sm) {
                Text(label.uppercased())
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textSecondary)
                    .tracking(0.5)

                Text(value)
                    .font(.system(size: 24, weight: .semibold, design: .default))
                    .foregroundStyle(DSColor.textPrimary)

                Text(note)
                    .font(DSTypography.caption)
                    .foregroundStyle(DSColor.textSecondary)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

// MARK: - Compact Icon Button

struct DSIconButton: View {
    let systemName: String
    let help: String
    var disabled = false
    let action: () -> Void
    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 16, weight: .regular))
                .foregroundStyle(disabled ? DSColor.textMuted : DSColor.textPrimary)
                .padding(.horizontal, 8)
                .padding(.vertical, 6)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .background(isHovering && !disabled ? DSColor.hover : Color.clear, in: RoundedRectangle(cornerRadius: DSRadius.medium))
        .disabled(disabled)
        .help(help)
        .onHover { isHovering = $0 }
    }
}

// MARK: - Key Value

struct DSInfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: DSSpacing.lg) {
            Text(label)
                .font(DSTypography.body)
                .foregroundStyle(DSColor.textSecondary)
                .frame(width: 140, alignment: .leading)

            Text(value)
                .font(DSTypography.mono)
                .foregroundStyle(DSColor.textPrimary)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.vertical, DSSpacing.xs)
    }
}

// MARK: - File Path

struct DSPathRow: View {
    let label: String
    let path: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: DSSpacing.lg) {
            Text(label)
                .font(DSTypography.body)
                .foregroundStyle(DSColor.textSecondary)
                .frame(width: 140, alignment: .leading)
            Text(path)
                .font(DSTypography.mono)
                .foregroundStyle(DSColor.textPrimary)
                .textSelection(.enabled)
                .lineLimit(2)
                .truncationMode(.middle)
                .frame(maxWidth: .infinity, alignment: .leading)
            DSPathActions(path: path)
        }
        .padding(.vertical, DSSpacing.xs)
    }
}

struct DSPathActions: View {
    let path: String

    private var expandedPath: String {
        NSString(string: path).expandingTildeInPath
    }

    var body: some View {
        HStack(spacing: 0) {
            DSIconButton(systemName: "arrow.up.right.square", help: L10n.openFile) {
                NSWorkspace.shared.open(URL(fileURLWithPath: expandedPath))
            }
            DSIconButton(systemName: "folder", help: L10n.revealInFinder) {
                revealInFinder()
            }
        }
    }

    private func revealInFinder() {
        var url = URL(fileURLWithPath: expandedPath)
        while !FileManager.default.fileExists(atPath: url.path), url.path != "/" {
            url.deleteLastPathComponent()
        }
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }
}
