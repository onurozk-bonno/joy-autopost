import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import insights  # noqa: E402

NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)


class R:
    def __init__(self, data, status=200):
        self._d, self.status_code, self.text = data, status, str(data)

    def json(self):
        return self._d


def fake_get(url, params=None, timeout=None):
    if url.endswith("/me/media"):
        return R({"data": [{"id": "1", "permalink": "https://www.instagram.com/reel/AAA/", "media_product_type": "REELS"}]})
    if url.endswith("/me"):
        return R({"followers_count": 42})
    if url.endswith("/insights"):
        m = params["metric"]
        if "/1/" in url:
            return R({"data": [{"name": m, "values": [{"value": 7}]}]})
        if m == "follower_count":
            return R({"data": [{"name": m, "values": [{"value": 1}, {"value": 2}]}]})
        return R({"data": [{"name": m, "total_value": {"value": 10}}]})
    raise AssertionError(url)


def test_collect_and_report():
    hist = [{"draft_id": "d1", "scene_id": "s", "permalink": "https://www.instagram.com/reel/AAA/"},
            {"draft_id": "d2", "scene_id": "x", "permalink": "https://www.instagram.com/p/ZZZ/"}]
    with mock.patch("insights.requests.get", fake_get):
        data = insights.collect("t", "u", "v23.0", hist, NOW)
    assert data["account"]["reach"] == 10 and data["account"]["follower_gain_7d"] == 3
    assert len(data["posts"]) == 1 and data["posts"][0]["metrics"]["ig_reels_avg_watch_time"] == 7
    assert "d1" in insights.render_report(data, NOW)


def test_permission_missing_exits_zero(monkeypatch, capsys, tmp_path):
    err = R({"error": {"code": 10, "message": "Application does not have permission for this action"}}, 400)
    monkeypatch.setenv("IG_ACCESS_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "u")
    monkeypatch.setenv("INSIGHTS_OUT_DIR", str(tmp_path))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr("insights.requests.get", lambda *a, **k: err)
    assert insights.main() == 0
    assert "instagram_business_manage_insights" in capsys.readouterr().out
    assert not list(tmp_path.iterdir())


def test_other_error_on_metric_is_tolerated():
    bad = R({"error": {"code": 100, "message": "metric not supported"}}, 400)
    with mock.patch("insights.requests.get", return_value=bad):
        assert insights.fetch_media_insights("t", {"id": "1"}, "v23.0")["reach"] is None


def test_shortcode():
    assert insights.shortcode("https://www.instagram.com/p/Dehg5hwmk6-/") == "Dehg5hwmk6-"
