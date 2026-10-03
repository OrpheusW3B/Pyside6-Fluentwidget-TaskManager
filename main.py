from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from qfluentwidgets import (
    FluentIcon,
    FluentWindow,
    NavigationItemPosition,
    NavigationToolButton,
    QConfig,
    Theme,
    isDarkTheme,
    qconfig,
    setTheme,
)

from models import Status, TaskStore
from pages import DashboardPage, TaskListPage

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"

PAGE_BG_LIGHT = "#FFFFFF"
PAGE_BG_DARK = "#1F1F1F"


class AppConfig(QConfig):
    pass


cfg = AppConfig()


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.store = TaskStore()
        self.setWindowTitle("Gestionnaire de tâches")

        self.dashboard = DashboardPage(self.store, self)
        self.allPage = TaskListPage(
            self.store,
            "Toutes les tâches",
            "Toutes vos tâches, quel que soit leur statut.",
            parent=self,
        )
        self.progressPage = TaskListPage(
            self.store,
            "En cours",
            "Tâches actuellement en cours de réalisation.",
            status_filter=Status.IN_PROGRESS,
            parent=self,
        )
        self.overduePage = TaskListPage(
            self.store,
            "En retard",
            "Tâches dont l'échéance est dépassée.",
            overdue_only=True,
            parent=self,
        )
        self.donePage = TaskListPage(
            self.store,
            "Terminées",
            "Tâches terminées.",
            status_filter=Status.DONE,
            parent=self,
        )

        self.dashboard.setObjectName("dashboardPage")
        self.allPage.setObjectName("allTasksPage")
        self.progressPage.setObjectName("inProgressPage")
        self.overduePage.setObjectName("overduePage")
        self.donePage.setObjectName("donePage")

        self.addSubInterface(self.dashboard, FluentIcon.HOME, "Tableau de bord")
        self.addSubInterface(self.allPage, FluentIcon.DOCUMENT, "Toutes")
        self.addSubInterface(self.progressPage, FluentIcon.PLAY, "En cours")
        self.addSubInterface(self.overduePage, FluentIcon.STOP_WATCH, "En retard")
        self.addSubInterface(self.donePage, FluentIcon.COMPLETED, "Terminées")

        self.themeButton = NavigationToolButton(FluentIcon.BRIGHTNESS, self)
        self.themeButton.setToolTip("Changer de thème (clair / sombre / auto)")
        self.themeButton.clicked.connect(self._cycle_theme)
        self.navigationInterface.addWidget(
            "theme",
            self.themeButton,
            position=NavigationItemPosition.BOTTOM,
        )

        qconfig.themeChanged.connect(self._on_theme_changed)

        self.pages = (
            self.dashboard,
            self.allPage,
            self.progressPage,
            self.overduePage,
            self.donePage,
        )
        self._apply_theme()

        self.resize(1120, 740)

    def _apply_theme(self):
        background = PAGE_BG_DARK if isDarkTheme() else PAGE_BG_LIGHT
        for page in self.pages:
            page.setStyleSheet(
                f"#{page.objectName()} {{ background-color: {background}; }}"
            )
            page.refresh()

    def _cycle_theme(self):
        order = [Theme.LIGHT, Theme.DARK, Theme.AUTO]
        current = cfg.themeMode.value
        index = order.index(current) if current in order else -1
        setTheme(order[(index + 1) % len(order)], save=True)

    def _on_theme_changed(self, theme: Theme | None = None):
        self._apply_theme()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gestionnaire de tâches")
    qconfig.load(str(CONFIG_FILE), cfg)
    setTheme(cfg.themeMode.value)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
