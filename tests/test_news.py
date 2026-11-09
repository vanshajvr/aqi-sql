"""Tests for the headline strip's feed parsing (api/news.py): no network."""
from api.news import parse_feed

FEED = b"""<?xml version="1.0"?><rss><channel>
<item><title>Delhi AQI turns severe after Diwali - The Hindu</title><link>https://a</link>
  <pubDate>Mon, 09 Nov 2026 05:00:00 GMT</pubDate><source url="https://thehindu.com">The Hindu</source></item>
<item><title>Older Hindu smog story - The Hindu</title><link>https://b</link>
  <pubDate>Mon, 09 Nov 2026 01:00:00 GMT</pubDate><source url="https://thehindu.com">The Hindu</source></item>
<item><title>Video | Delhi pollution crisis - NDTV</title><link>https://c</link>
  <pubDate>Mon, 09 Nov 2026 06:00:00 GMT</pubDate><source url="https://ndtv.com">NDTV</source></item>
<item><title>5 SUVs with built-in purifiers - Livemint</title><link>https://d</link>
  <pubDate>Mon, 09 Nov 2026 07:00:00 GMT</pubDate><source url="https://livemint.com">Livemint</source></item>
<item><title>Why air quality readings differ - The Indian Express</title><link>https://e</link>
  <pubDate>Mon, 09 Nov 2026 08:00:00 GMT</pubDate><source url="https://indianexpress.com">The Indian Express</source></item>
</channel></rss>"""


def test_keeps_newest_on_topic_headline_per_publisher():
    items = parse_feed(FEED)
    assert [x["source"] for x in items] == ["The Indian Express", "The Hindu"]   # newest first
    assert items[1]["title"] == "Delhi AQI turns severe after Diwali"            # " - The Hindu" stripped
    assert items[1]["url"] == "https://a"


def test_skips_video_and_off_topic_items_and_respects_the_limit():
    titles = [x["title"] for x in parse_feed(FEED)]
    assert not any(t.startswith("Video") or "SUVs" in t for t in titles)
    assert len(parse_feed(FEED, limit=1)) == 1
