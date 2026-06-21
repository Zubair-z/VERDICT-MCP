import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFrame, QScrollArea,
    QSizePolicy, QStackedWidget, QStyleFactory,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon


class GlassCard(QFrame):
    """A glassmorphic card widget with frosted background."""

    def __init__(self, parent=None):
        """Initialize the glass card with a vertical layout."""
        super().__init__(parent)
        self.setObjectName("glassCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class SidebarButton(QPushButton):
    """A stylable sidebar navigation button with checkable state."""

    def __init__(self, text: str, parent=None):
        """Initialize the sidebar button with given text."""
        super().__init__(text, parent)
        self.setObjectName("sidebarButton")
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)


class DashboardWindow(QMainWindow):
    """Main dashboard window with sidebar navigation and glassmorphic UI."""

    def __init__(self):
        """Initialize the dashboard window with sidebar and content area."""
        super().__init__()
        self.setWindowTitle("Verdict Dashboard")
        self.setMinimumSize(1100, 700)
        self.setObjectName("mainWindow")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        content_area = self._build_content_area()
        main_layout.addWidget(content_area, 1)

        self._apply_stylesheet()

    def _build_sidebar(self) -> QWidget:
        """Build the sidebar navigation panel."""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(8)

        brand = QLabel("VERDICT")
        brand.setObjectName("brandLabel")
        brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand)

        separator = QFrame()
        separator.setObjectName("sidebarSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("navLabel")
        layout.addWidget(nav_label)

        self.btn_dashboard = SidebarButton(" Dashboard")
        self.btn_analytics = SidebarButton(" Analytics")
        self.btn_settings = SidebarButton(" Settings")
        self.btn_users = SidebarButton(" Users")

        layout.addWidget(self.btn_dashboard)
        layout.addWidget(self.btn_analytics)
        layout.addWidget(self.btn_users)
        layout.addWidget(self.btn_settings)
        layout.addStretch()

        logout_btn = QPushButton(" Logout")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(logout_btn)

        return sidebar

    def _build_content_area(self) -> QWidget:
        """Build the main content area with cards and activity feed."""
        content = QWidget()
        content.setObjectName("contentArea")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("Dashboard Overview")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        card1 = GlassCard()
        card1_layout = card1.layout()
        lbl1_title = QLabel("Total Users")
        lbl1_title.setObjectName("cardTitle")
        lbl1_value = QLabel("1,284")
        lbl1_value.setObjectName("cardValue")
        card1_layout.addWidget(lbl1_title)
        card1_layout.addWidget(lbl1_value)
        cards_layout.addWidget(card1)

        card2 = GlassCard()
        card2_layout = card2.layout()
        lbl2_title = QLabel("Active Sessions")
        lbl2_title.setObjectName("cardTitle")
        lbl2_value = QLabel("342")
        lbl2_value.setObjectName("cardValue")
        card2_layout.addWidget(lbl2_title)
        card2_layout.addWidget(lbl2_value)
        cards_layout.addWidget(card2)

        card3 = GlassCard()
        card3_layout = card3.layout()
        lbl3_title = QLabel("Revenue")
        lbl3_title.setObjectName("cardTitle")
        lbl3_value = QLabel("$48,290")
        lbl3_value.setObjectName("cardValue")
        card3_layout.addWidget(lbl3_title)
        card3_layout.addWidget(lbl3_value)
        cards_layout.addWidget(card3)

        layout.addLayout(cards_layout)

        section_label = QLabel("Recent Activity")
        section_label.setObjectName("sectionLabel")
        layout.addWidget(section_label)

        scroll = QScrollArea()
        scroll.setObjectName("activityScroll")
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("activityWidget")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        for i in range(5):
            row = QFrame()
            row.setObjectName("activityRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)

            icon = QLabel("●")
            icon.setObjectName("activityIcon")
            icon.setFixedWidth(20)
            row_layout.addWidget(icon)

            text = QLabel(f"User action performed at {10 + i}:{30 + i * 7:02d} AM")
            text.setObjectName("activityText")
            row_layout.addWidget(text, 1)

            time_label = QLabel(f"{i + 1}m ago")
            time_label.setObjectName("activityTime")
            row_layout.addWidget(time_label)

            scroll_layout.addWidget(row)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        return content

    def _apply_stylesheet(self):
        """Apply the premium glassmorphic dark theme stylesheet."""
        self.setStyleSheet("""
            QWidget#mainWindow {
                background-color: #0a0a0f;
            }
            QWidget#sidebar {
                background-color: rgba(18, 18, 30, 0.85);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
            QLabel#brandLabel {
                color: #00f0ff;
                font-size: 20px;
                font-weight: 700;
                padding: 16px 0px;
                letter-spacing: 4px;
            }
            QFrame#sidebarSeparator {
                background-color: rgba(255, 255, 255, 0.06);
                max-height: 1px;
            }
            QLabel#navLabel {
                color: #555566;
                font-size: 11px;
                font-weight: 600;
                padding: 12px 8px 4px 8px;
                letter-spacing: 1px;
            }
            QPushButton#sidebarButton {
                background-color: transparent;
                color: #8888aa;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton#sidebarButton:hover {
                background-color: rgba(0, 240, 255, 0.08);
                color: #f0f0f5;
            }
            QPushButton#sidebarButton:checked {
                background-color: rgba(0, 240, 255, 0.15);
                color: #00f0ff;
            }
            QPushButton#logoutButton {
                background-color: rgba(255, 51, 85, 0.12);
                color: #ff3355;
                border: 1px solid rgba(255, 51, 85, 0.25);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton#logoutButton:hover {
                background-color: rgba(255, 51, 85, 0.2);
            }
            QWidget#contentArea {
                background-color: transparent;
            }
            QLabel#pageHeader {
                color: #f0f0f5;
                font-size: 24px;
                font-weight: 700;
                padding-bottom: 4px;
            }
            QFrame#glassCard {
                background-color: rgba(18, 18, 30, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                padding: 16px;
            }
            QLabel#cardTitle {
                color: #8888aa;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QLabel#cardValue {
                color: #f0f0f5;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#sectionLabel {
                color: #8888aa;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 0px 4px 0px;
                letter-spacing: 0.5px;
            }
            QScrollArea#activityScroll {
                border: none;
                background-color: transparent;
            }
            QWidget#activityWidget {
                background-color: transparent;
            }
            QFrame#activityRow {
                background-color: rgba(18, 18, 30, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
            }
            QFrame#activityRow:hover {
                background-color: rgba(18, 18, 30, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QLabel#activityIcon {
                color: #00ff88;
                font-size: 10px;
            }
            QLabel#activityText {
                color: #f0f0f5;
                font-size: 13px;
            }
            QLabel#activityTime {
                color: #555566;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background-color: rgba(18, 18, 30, 0.3);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)


def create_dashboard():
    """Create and return a DashboardWindow instance with Fusion style."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create("Fusion"))
    window = DashboardWindow()
    window.show()
    return window


def run():
    """Create and display the dashboard, then start the event loop."""
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
