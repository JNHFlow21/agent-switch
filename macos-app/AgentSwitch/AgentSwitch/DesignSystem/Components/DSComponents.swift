// [INPUT]: SwiftUI, DSTokens
// [OUTPUT]: DSPage, DSCard, DSBadge, DSMetricCard reusable components
// [POS]: DesignSystem/Components — product-level reusable views
// [PROTOCOL]: When this file changes, update this header, then check CLAUDE.md

import SwiftUI

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
                    .fill(.background)
                    .shadow(color: DSDepth.card.color, radius: DSDepth.card.radius, x: DSDepth.card.x, y: DSDepth.card.y)
            )
            .overlay(
                RoundedRectangle(cornerRadius: DSRadius.medium, style: .continuous)
                    .stroke(DSColor.separator.opacity(0.5), lineWidth: 0.5)
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
        case .good: return DSColor.statusGood
        case .warn: return DSColor.statusWarn
        case .bad: return DSColor.statusBad
        case .info: return DSColor.statusInfo
        case .neutral: return DSColor.textSecondary
        case .route: return DSColor.statusInfo
        case .app: return Color(red: 0.22, green: 0.25, blue: 0.32)
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
        case .app: return Color(red: 0.93, green: 0.97, blue: 0.96)
        }
    }

    var body: some View {
        Text(text)
            .font(.system(size: 11, weight: .semibold))
            .foregroundStyle(foreground)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(background, in: Capsule())
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
                    .font(.system(size: 28, weight: .bold, design: .rounded))
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
