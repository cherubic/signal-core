from unittest.mock import MagicMock, patch
from pathlib import Path
from signal_core.pipeline import run_pipeline


def _make_pending(n: int = 3) -> list:
    return [MagicMock(id=f"id{i}", url=f"https://ex.com/{i}", is_top5=(i == 0)) for i in range(n)]


def test_pipeline_delivers_when_one_channel_succeeds(tmp_path: Path):
    mock_items = [MagicMock(id=f"id{i}", url=f"https://ex.com/{i}") for i in range(3)]
    mock_summarized = [MagicMock(id=f"id{i}", is_top5=(i == 0)) for i in range(3)]
    pending = _make_pending()

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
        db_instance = MockDB.return_value
        db_instance.get_pending_delivery.return_value = pending

        MockHN.return_value.fetch.return_value = mock_items
        mock_sum = MagicMock()
        mock_sum.summarize.return_value = mock_summarized
        mock_sum.pick_top5.return_value = mock_summarized
        MockSummarizer.return_value = mock_sum

        # Email fails, Telegram succeeds, Feishu fails
        MockEmail.return_value.send.side_effect = Exception("smtp error")
        MockFS.return_value.send.side_effect = Exception("feishu error")

        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")

        mock_sum.summarize.assert_called_once()
        db_instance.mark_summarized.assert_called_once()
        # delivered because Telegram succeeded
        db_instance.mark_delivered.assert_called_once()


def test_pipeline_does_not_mark_delivered_when_all_channels_fail(tmp_path: Path):
    mock_items = [MagicMock(id=f"id{i}", url=f"https://ex.com/{i}") for i in range(3)]
    mock_summarized = [MagicMock(id=f"id{i}", is_top5=(i == 0)) for i in range(3)]
    pending = _make_pending()

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
        db_instance = MockDB.return_value
        db_instance.get_pending_delivery.return_value = pending

        MockHN.return_value.fetch.return_value = mock_items
        mock_sum = MagicMock()
        mock_sum.summarize.return_value = mock_summarized
        mock_sum.pick_top5.return_value = mock_summarized
        MockSummarizer.return_value = mock_sum

        # All three channels fail
        MockEmail.return_value.send.side_effect = Exception("smtp error")
        MockTG.return_value.send.side_effect = Exception("tg error")
        MockFS.return_value.send.side_effect = Exception("feishu error")

        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")

        # summaries cached but NOT marked delivered
        db_instance.mark_summarized.assert_called_once()
        db_instance.mark_delivered.assert_not_called()


def test_pipeline_skips_failed_fetcher(tmp_path: Path):
    with (
        patch("signal_core.pipeline.load_sources", return_value=[
            MagicMock(type="hackernews_api", name="HN", category="open_source", url=""),
        ]),
        patch("signal_core.pipeline.Database") as MockDB,
        patch("signal_core.pipeline.HackerNewsFetcher") as MockHN,
        patch("signal_core.pipeline.deduplicate", return_value=[]),
        patch("signal_core.pipeline.create_summarizer"),
        patch("signal_core.pipeline.EmailDeliverer"),
        patch("signal_core.pipeline.TelegramDeliverer"),
        patch("signal_core.pipeline.FeishuDeliverer"),
    ):
        MockDB.return_value.get_pending_delivery.return_value = []
        MockHN.return_value.fetch.side_effect = Exception("network error")
        # Should not raise
        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")
