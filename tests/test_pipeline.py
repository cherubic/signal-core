from unittest.mock import MagicMock, patch
from pathlib import Path
from signal_core.pipeline import run_pipeline


def test_pipeline_runs_without_error(tmp_path: Path):
    mock_items = [MagicMock(id=f"id{i}", url=f"https://ex.com/{i}") for i in range(3)]
    mock_summarized = [MagicMock(id=f"id{i}", is_top5=(i == 0)) for i in range(3)]

    with (
        patch("signal_core.pipeline.load_sources", return_value=[
            MagicMock(type="hackernews_api", name="HN", category="open_source", url=""),
        ]),
        patch("signal_core.pipeline.Database") as MockDB,
        patch("signal_core.pipeline.HackerNewsFetcher") as MockHN,
        patch("signal_core.pipeline.deduplicate", return_value=mock_items),
        patch("signal_core.pipeline.create_summarizer") as MockSummarizer,
        patch("signal_core.pipeline.EmailDeliverer") as MockEmail,
        patch("signal_core.pipeline.TelegramDeliverer") as MockTG,
        patch("signal_core.pipeline.FeishuDeliverer") as MockFS,
    ):
        MockHN.return_value.fetch.return_value = mock_items
        mock_sum = MagicMock()
        mock_sum.summarize.return_value = mock_summarized
        mock_sum.pick_top5.return_value = mock_summarized
        MockSummarizer.return_value = mock_sum

        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")

        MockHN.return_value.fetch.assert_called_once()
        mock_sum.summarize.assert_called_once()
        MockEmail.return_value.send.assert_called_once()
        MockTG.return_value.send.assert_called_once()
        MockFS.return_value.send.assert_called_once()


def test_pipeline_skips_failed_fetcher(tmp_path: Path):
    with (
        patch("signal_core.pipeline.load_sources", return_value=[
            MagicMock(type="hackernews_api", name="HN", category="open_source", url=""),
        ]),
        patch("signal_core.pipeline.Database"),
        patch("signal_core.pipeline.HackerNewsFetcher") as MockHN,
        patch("signal_core.pipeline.deduplicate", return_value=[]),
        patch("signal_core.pipeline.create_summarizer"),
        patch("signal_core.pipeline.EmailDeliverer"),
        patch("signal_core.pipeline.TelegramDeliverer"),
        patch("signal_core.pipeline.FeishuDeliverer"),
    ):
        MockHN.return_value.fetch.side_effect = Exception("network error")
        # Should not raise
        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")
