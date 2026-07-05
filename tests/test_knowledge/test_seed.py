"""Tests for seed.py — knowledge seeding with mock store."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_workspace.knowledge.seed import main, seed


class TestSeed:
    def test_seed_with_mock_store(self):
        """seed() accepts an optional store parameter — test with mock."""
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock()

        indexed, skipped = seed(store=mock_store, verbose=False)

        assert isinstance(indexed, int)
        assert isinstance(skipped, int)
        total = indexed + skipped
        assert total > 0
        assert mock_store.add_knowledge.call_count == indexed

    def test_seed_calls_add_knowledge_with_content(self):
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock()

        indexed, _ = seed(store=mock_store, verbose=False)

        if indexed > 0:
            call = mock_store.add_knowledge.call_args
            assert call is not None
            kwargs = call.kwargs or call[1]
            assert "content" in kwargs
            assert "content_type" in kwargs
            assert "title" in kwargs
            assert "tags" in kwargs

    def test_seed_returns_count(self):
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock()
        result = seed(store=mock_store, verbose=False)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)

    def test_seed_verbose_logs(self):
        """verbose=True triggers the logging calls."""
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock()
        with patch("ai_workspace.knowledge.seed.logger") as mock_log:
            seed(store=mock_store, verbose=True)
            assert mock_log.info.called
            # Should log "Indexed" messages
            indexed_calls = [
                c for c in mock_log.info.call_args_list
                if "Indexed" in str(c)
            ]
            assert len(indexed_calls) > 0

    def test_seed_handles_exception(self):
        """When add_knowledge raises, seed continues and skips the file."""
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock(side_effect=RuntimeError("DB error"))

        indexed, skipped = seed(store=mock_store, verbose=False)
        # All files should be skipped since add_knowledge always fails
        assert skipped > 0
        assert indexed == 0

    def test_seed_handles_exception_with_verbose(self):
        """With verbose=True, exceptions are logged."""
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock(side_effect=RuntimeError("DB error"))

        with patch("ai_workspace.knowledge.seed.logger") as mock_log:
            indexed, skipped = seed(store=mock_store, verbose=True)
            assert skipped > 0
            assert mock_log.error.called
            error_calls = [
                c for c in mock_log.error.call_args_list
                if "Failed to index" in str(c)
            ]
            assert len(error_calls) > 0

    def test_seed_verbose_true_logs_final_count(self):
        """With verbose=True, final indexed/skipped counts are logged."""
        mock_store = MagicMock()
        mock_store.add_knowledge = MagicMock()
        with patch("ai_workspace.knowledge.seed.logger") as mock_log:
            seed(store=mock_store, verbose=True)
            final_calls = [
                c for c in mock_log.info.call_args_list
                if "Indexed:" in str(c)
            ]
            assert len(final_calls) == 1


class TestMain:
    def test_main_calls_seed(self):
        """main() calls seed() and logs messages."""
        with patch("ai_workspace.knowledge.seed.seed") as mock_seed:
            with patch("ai_workspace.knowledge.seed.logger") as mock_log:
                main()
                mock_seed.assert_called_once()
                assert mock_log.info.call_count >= 2  # start + done

    def test_main_logs_start_and_done(self):
        """main() logs both start and completion messages."""
        with patch("ai_workspace.knowledge.seed.seed"):
            with patch("ai_workspace.knowledge.seed.logger") as mock_log:
                main()
                messages = [str(c) for c in mock_log.info.call_args_list]
                start_msgs = [m for m in messages if "Seeding" in m]
                done_msgs = [m for m in messages if "Done" in m]
                assert len(start_msgs) >= 1
                assert len(done_msgs) >= 1
