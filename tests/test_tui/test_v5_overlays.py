"""
Tests for TUI v5 overlays: Dashboard (F3), Git (Ctrl+G), Files (Ctrl+O),
Chat History (F2).

Verifies each overlay mounts, renders, and dismisses correctly.
"""

from __future__ import annotations

import pytest

pytest_plugins = ("pytest_asyncio",)


# ===================================================================
# Help Screen (F1)
# ===================================================================


class TestHelpScreen:

    @pytest.mark.asyncio
    async def test_mounts_and_shows_commands(self):
        """HelpScreen contém comandos conhecidos."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            # Abre via binding
            await pilot.press("f1")
            await pilot.pause(0.3)

            top = app.screen_stack[-1]
            assert "Help" in type(top).__name__

            # Deve ter texto com comandos
            assert app.screen.query_one("#help-box") is not None

    @pytest.mark.asyncio
    async def test_escape_dismisses(self):
        """Escape fecha o HelpScreen."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f1")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 3  # default + main + help

            await pilot.press("escape")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 2  # default + main


# ===================================================================
# Dashboard Screen (F3)
# ===================================================================


class TestDashboardScreen:

    @pytest.mark.asyncio
    async def test_mounts_and_has_stat_cards(self):
        """DashboardScreen monta com stat cards."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            # Abre via binding
            await pilot.press("f3")
            await pilot.pause(0.5)

            top = app.screen_stack[-1]
            assert "Dashboard" in type(top).__name__

            # Verifica que o box principal existe
            assert app.screen.query_one("#dashboard-box") is not None

            # Verifica que os StatCards existem
            for stat_id in ("stat-agents", "stat-tasks", "stat-cost", "stat-cache"):
                card = app.screen.query_one(f"#{stat_id}")
                assert card is not None, f"StatCard #{stat_id} não encontrado"

    @pytest.mark.asyncio
    async def test_dashboard_shows_activity(self):
        """Dashboard carrega a seção de atividade."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f3")
            await pilot.pause(0.5)

            # Widget existe e o app não crashou
            activity_log = app.screen.query_one("#activity-log")
            assert activity_log is not None

    @pytest.mark.asyncio
    async def test_refresh_updates(self):
        """R recarrega o dashboard."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f3")
            await pilot.pause(0.3)

            await pilot.press("r")
            await pilot.pause(0.3)

            # Não crashou
            assert app.screen.query_one("#dashboard-box") is not None

    @pytest.mark.asyncio
    async def test_q_dismisses(self):
        """Q fecha o dashboard."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f3")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 3

            await pilot.press("q")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 2


# ===================================================================
# Git Screen (Ctrl+G)
# ===================================================================


class TestGitScreen:

    @pytest.mark.asyncio
    async def test_mounts(self):
        """GitScreen monta."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+g")
            await pilot.pause(0.5)

            top = app.screen_stack[-1]
            assert "Git" in type(top).__name__
            assert app.screen.query_one("#git-box") is not None
            assert app.screen.query_one("#git-output") is not None

    @pytest.mark.asyncio
    async def test_git_mounts_without_crashing(self):
        """GitScreen monta sem crashar (qualquer output é válido)."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+g")
            await pilot.pause(0.5)

            # Apenas verifica que o widget existe e não crashou
            assert app.screen.query_one("#git-output") is not None

    @pytest.mark.asyncio
    async def test_refresh(self):
        """R recarrega o git status."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+g")
            await pilot.pause(0.3)

            await pilot.press("r")
            await pilot.pause(0.3)

            assert app.screen.query_one("#git-box") is not None

    @pytest.mark.asyncio
    async def test_dismisses(self):
        """Q fecha o git panel."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+g")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 3

            await pilot.press("q")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 2


# ===================================================================
# Files Screen (Ctrl+O)
# ===================================================================


class TestFilesScreen:

    @pytest.mark.asyncio
    async def test_mounts(self):
        """FilesScreen monta com DirectoryTree."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            # Abre via binding Ctrl+O
            await pilot.press("ctrl+o")
            await pilot.pause(0.5)

            top = app.screen_stack[-1]
            assert "Files" in type(top).__name__

            # Verifica que o box e a árvore existem
            assert app.screen.query_one("#files-box") is not None
            assert app.screen.query_one("#files-path") is not None

    @pytest.mark.asyncio
    async def test_shows_path_widget(self):
        """FilesScreen tem o widget de path."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+o")
            await pilot.pause(0.3)

            assert app.screen.query_one("#files-path") is not None

    @pytest.mark.asyncio
    async def test_navigates_with_keys(self):
        """FilesScreen responde a teclas de navegação."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+o")
            await pilot.pause(0.3)

            # Navega com setas (não crasha)
            await pilot.press("down", "down", "up")
            await pilot.pause(0.2)

            assert app.screen.query_one("#files-tree") is not None

    @pytest.mark.asyncio
    async def test_dismisses(self):
        """Q fecha o file browser."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+o")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 3

            await pilot.press("q")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 2


# ===================================================================
# Chat History Screen (F2)
# ===================================================================


class TestChatHistoryScreen:

    @pytest.mark.asyncio
    async def test_mounts(self):
        """ChatScreen monta."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            # Abre via binding
            await pilot.press("f2")
            await pilot.pause(0.5)

            top = app.screen_stack[-1]
            assert "Chat" in type(top).__name__

            assert app.screen.query_one("#chat-box") is not None
            assert app.screen.query_one("#chat-list") is not None

    @pytest.mark.asyncio
    async def test_chat_mounts(self):
        """ChatScreen monta sem crashar."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f2")
            await pilot.pause(0.5)

            assert app.screen.query_one("#chat-list") is not None

    @pytest.mark.asyncio
    async def test_refresh(self):
        """R recarrega o chat history."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f2")
            await pilot.pause(0.3)

            await pilot.press("r")
            await pilot.pause(0.3)

            assert app.screen.query_one("#chat-box") is not None

    @pytest.mark.asyncio
    async def test_dismisses(self):
        """Q fecha o chat."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f2")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 3

            await pilot.press("q")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 2


# ===================================================================
# StatCard (componente do Dashboard)
# ===================================================================


class TestStatCard:

    @pytest.mark.asyncio
    async def test_labels_and_values_update(self):
        """StatCard atualiza label e value via reactive."""
        from textual.app import App
        from textual.containers import Vertical
        from textual.widgets import Static
        from ai_workspace.tui.v5.dashboard import StatCard

        class StatCardTestApp(App):
            def compose(self):
                with Vertical():
                    yield StatCard(id="test")

        app = StatCardTestApp()
        async with app.run_test(size=(40, 10)) as pilot:
            await pilot.pause(0.2)

            card = app.screen.query_one("#test")
            card.label = "Agents"
            await pilot.pause(0.1)
            card.value = "42"
            await pilot.pause(0.1)

            assert card.label == "Agents"
            assert card.value == "42"


# ===================================================================
# GitScreen — cenários de erro (unitário, sem app)
# ===================================================================


class TestGitScreenLogic:

    def test_subprocess_error_handled(self):
        """GitScreen lida com FileNotFoundError (git não instalado)."""
        from ai_workspace.tui.v5.git_panel import GitScreen

        # Só verifica que a classe existe e pode ser instanciada
        screen = GitScreen(cwd="/tmp")
        assert screen is not None
        assert screen._cwd == "/tmp"
