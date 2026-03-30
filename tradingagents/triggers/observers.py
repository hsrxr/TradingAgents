from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional, Protocol
import xml.etree.ElementTree as ET
import html
import json
import re

import numpy as np
import pandas as pd
import requests
from langchain_core.tools import tool

from tradingagents.dataflows.calculate_indicators import generate_builtin_quant_signals
from tradingagents.dataflows.geckoterminal_price import get_dex_ohlcv

try:
    from .models import TriggerEvent
except ImportError:  # pragma: no cover - allows direct script execution
    from tradingagents.triggers.models import TriggerEvent


class BaseTriggerObserver(Protocol):
    """Observer contract for producing trigger events."""

    def poll(self, now: datetime, pairs: List[str]) -> List[TriggerEvent]:
        ...


class HourlyBoundaryObserver:
    """Emit one event per pair at each top-of-hour boundary."""

    def __init__(self, trigger_second_window: int = 20) -> None:
        self.trigger_second_window = max(1, trigger_second_window)
        self._last_fired_key: Dict[str, str] = {}

    def poll(self, now: datetime, pairs: List[str]) -> List[TriggerEvent]:
        if now.minute != 0 or now.second >= self.trigger_second_window:
            return []

        hour_key = now.strftime("%Y-%m-%d-%H")
        events: List[TriggerEvent] = []
        for pair in pairs:
            if self._last_fired_key.get(pair) == hour_key:
                continue
            self._last_fired_key[pair] = hour_key
            events.append(
                TriggerEvent(
                    event_type="scheduled.hourly",
                    pair=pair,
                    source="scheduler",
                    occurred_at=now,
                    confidence=1.0,
                    payload={"rule": "hourly_top_of_hour"},
                )
            )
        return events


@dataclass
class NewsItem:
    item_id: str
    source: str
    title: str
    summary: str
    published_at: Optional[datetime] = None
    url: Optional[str] = None


class NewsSource(Protocol):
    def fetch_items(self, since: datetime) -> List[NewsItem]:
        ...


class SecPressReleaseSource:
    """SEC press release RSS source."""

    def __init__(self, url: str = "https://www.sec.gov/news/pressreleases.rss") -> None:
        self.url = url

    def fetch_items(self, since: datetime) -> List[NewsItem]:
        headers = {
            "User-Agent": "TradingAgents/0.2.1 (market-shock-trigger)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }

        resp = requests.get(self.url, headers=headers, timeout=10)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        out: List[NewsItem] = []
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()

            if not title:
                continue

            published_at = _parse_rss_datetime(pub_date)
            if published_at is not None and published_at < since:
                continue

            item_id = (item.findtext("guid") or link or title).strip()
            out.append(
                NewsItem(
                    item_id=item_id,
                    source="sec",
                    title=title,
                    summary=description,
                    published_at=published_at,
                    url=link or None,
                )
            )
        return out


DEFAULT_NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.1d4.us",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
]


class TwitterAccountsRssSource:
    """Fetch watched X accounts through Nitter RSS mirrors (no official API)."""

    def __init__(
        self,
        handles: List[str],
        nitter_instances: Optional[List[str]] = None,
        timeout_seconds: int = 10,
    ) -> None:
        self.handles = [self._normalize_handle(h) for h in handles if h.strip()]
        self.nitter_instances = [x.rstrip("/") for x in (nitter_instances or DEFAULT_NITTER_INSTANCES)]
        self.timeout_seconds = max(3, timeout_seconds)

    def fetch_items(self, since: datetime) -> List[NewsItem]:
        out: List[NewsItem] = []
        seen_ids: set[str] = set()
        for handle in self.handles:
            xml_bytes = self._fetch_first_available_account_rss(handle)
            if xml_bytes is None:
                continue

            try:
                root = ET.fromstring(xml_bytes)
            except ET.ParseError:
                continue

            for item in root.findall("./channel/item"):
                title = self._clean_text(item.findtext("title") or "")
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = self._clean_text(item.findtext("description") or "")

                if not title:
                    continue

                published_at = _parse_rss_datetime(pub_date)
                if published_at is not None and published_at < since:
                    continue

                guid = (item.findtext("guid") or "").strip()
                item_id = f"twitter:{handle}:{guid or link or title}"
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                out.append(
                    NewsItem(
                        item_id=item_id,
                        source="twitter",
                        title=f"@{handle}: {title}",
                        summary=description,
                        published_at=published_at,
                        url=link or None,
                    )
                )
        return out

    def _fetch_first_available_account_rss(self, handle: str) -> Optional[bytes]:
        headers = {
            "User-Agent": "TradingAgents/0.2.1 (market-shock-trigger)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }
        for base_url in self.nitter_instances:
            rss_url = f"{base_url}/{handle}/rss"
            try:
                resp = requests.get(rss_url, headers=headers, timeout=self.timeout_seconds)
                if resp.status_code == 200 and resp.content:
                    return resp.content
            except Exception:
                continue
        return None

    def _normalize_handle(self, handle: str) -> str:
        normalized = handle.strip()
        if normalized.startswith("@"):
            normalized = normalized[1:]
        return normalized.lower()

    def _clean_text(self, value: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", value)
        return html.unescape(no_tags).strip()


class PollingNewsObserver:
    """Poll configured news sources and emit symbol-matched trigger events."""

    def __init__(
        self,
        sources: List[NewsSource],
        pair_keywords: Optional[Dict[str, List[str]]] = None,
        source_allowlist: Optional[List[str]] = None,
        lookback_minutes: int = 30,
        max_seen_ids: int = 5000,
    ) -> None:
        self.sources = sources
        self.pair_keywords = {k: [x.lower() for x in v] for k, v in (pair_keywords or {}).items()}
        self.source_allowlist = set(x.lower() for x in source_allowlist) if source_allowlist else None
        self.lookback_minutes = max(1, lookback_minutes)
        self.max_seen_ids = max(500, max_seen_ids)
        self._seen_ids: Dict[str, datetime] = {}

    def poll(self, now: datetime, pairs: List[str]) -> List[TriggerEvent]:
        if not self.sources:
            return []

        since = now - timedelta(minutes=self.lookback_minutes)
        events: List[TriggerEvent] = []

        for source in self.sources:
            try:
                news_items = source.fetch_items(since=since)
            except Exception:
                continue

            for item in news_items:
                source_name = (item.source or "unknown").lower()
                if self.source_allowlist and source_name not in self.source_allowlist:
                    continue
                if item.item_id in self._seen_ids:
                    continue

                matched_pairs = self._match_pairs(item, pairs)
                if not matched_pairs:
                    continue

                self._seen_ids[item.item_id] = now
                for pair in matched_pairs:
                    events.append(
                        TriggerEvent(
                            event_type="news.breaking",
                            pair=pair,
                            source=source_name,
                            occurred_at=now,
                            confidence=0.85,
                            payload={
                                "title": item.title,
                                "summary": item.summary,
                                "url": item.url,
                                "published_at": item.published_at.isoformat() if item.published_at else None,
                                "origin": item.source,
                            },
                        )
                    )

        if len(self._seen_ids) > self.max_seen_ids:
            self._shrink_seen_ids(now)

        return events

    def _match_pairs(self, item: NewsItem, pairs: List[str]) -> List[str]:
        searchable = f"{item.title} {item.summary}".lower()
        matched: List[str] = []

        for pair in pairs:
            keywords = self.pair_keywords.get(pair) or _default_keywords_for_pair(pair)
            if any(keyword in searchable for keyword in keywords):
                matched.append(pair)
        return matched

    def _shrink_seen_ids(self, now: datetime) -> None:
        cutoff = now - timedelta(hours=24)
        self._seen_ids = {k: v for k, v in self._seen_ids.items() if v >= cutoff}


class PriceActionObserver:
    """Price/volume/quant-factor driven trigger detector."""

    def __init__(
        self,
        sigma_multiplier: float = 2.0,
        atr_multiplier: float = 1.8,
        quant_strength_threshold: float = 0.7,
        min_price_change_pct: float = 0.002,
        min_volume_change_pct: float = 0.2,
    ) -> None:
        self.sigma_multiplier = sigma_multiplier
        self.atr_multiplier = atr_multiplier
        self.quant_strength_threshold = quant_strength_threshold
        self.min_price_change_pct = min_price_change_pct
        self.min_volume_change_pct = min_volume_change_pct
        self._active_flags: Dict[str, Dict[str, bool]] = {}

    def poll(self, now: datetime, pairs: List[str]) -> List[TriggerEvent]:
        events: List[TriggerEvent] = []
        for pair in pairs:
            pair_events = self._poll_pair(now, pair)
            events.extend(pair_events)
        return events

    def _poll_pair(self, now: datetime, pair: str) -> List[TriggerEvent]:
        events: List[TriggerEvent] = []
        minute_df = self._fetch_minute_ohlcv(pair=pair, now=now, needed_rows=1500)
        if minute_df.empty:
            return events

        flags = self._active_flags.setdefault(pair, {})

        sigma_event_1m = self._detect_sigma_breakout(minute_df, window=24 * 60)
        events.extend(self._emit_on_rising_edge(
            now=now,
            pair=pair,
            trigger_key="price.sigma_breakout.1m",
            active=sigma_event_1m is not None,
            payload=sigma_event_1m,
            confidence=0.7,
            flags=flags,
        ))

        df_5m = self._to_5m(minute_df)
        sigma_event_5m = self._detect_sigma_breakout(df_5m, window=24 * 12)
        events.extend(self._emit_on_rising_edge(
            now=now,
            pair=pair,
            trigger_key="price.sigma_breakout.5m",
            active=sigma_event_5m is not None,
            payload=sigma_event_5m,
            confidence=0.75,
            flags=flags,
        ))

        atr_event = self._detect_atr_breakout(df_5m, period=14)
        events.extend(self._emit_on_rising_edge(
            now=now,
            pair=pair,
            trigger_key="price.atr_breakout",
            active=atr_event is not None,
            payload=atr_event,
            confidence=0.72,
            flags=flags,
        ))

        divergence_event = self._detect_volume_price_divergence(df_5m, bars=12)
        events.extend(self._emit_on_rising_edge(
            now=now,
            pair=pair,
            trigger_key="price.volume_divergence",
            active=divergence_event is not None,
            payload=divergence_event,
            confidence=0.68,
            flags=flags,
        ))

        quant_event = self._detect_quant_factor_signal(pair)
        events.extend(self._emit_on_rising_edge(
            now=now,
            pair=pair,
            trigger_key="quant.strong_signal",
            active=quant_event is not None,
            payload=quant_event,
            confidence=0.8,
            flags=flags,
        ))

        return events

    def _emit_on_rising_edge(
        self,
        now: datetime,
        pair: str,
        trigger_key: str,
        active: bool,
        payload: Optional[Dict[str, Any]],
        confidence: float,
        flags: Dict[str, bool],
    ) -> List[TriggerEvent]:
        previous = flags.get(trigger_key, False)
        flags[trigger_key] = active
        if not active or previous:
            return []

        return [
            TriggerEvent(
                event_type=trigger_key,
                pair=pair,
                source="price_observer",
                occurred_at=now,
                confidence=confidence,
                payload=payload or {},
            )
        ]

    def _fetch_minute_ohlcv(self, pair: str, now: datetime, needed_rows: int) -> pd.DataFrame:
        parts: List[pd.DataFrame] = []
        remaining = needed_rows
        cursor = now

        while remaining > 0:
            limit = min(1000, remaining)
            try:
                frame = get_dex_ohlcv.invoke(
                    {
                        "pair": pair,
                        "tradedate": cursor.strftime("%Y-%m-%d %H:%M:%S"),
                        "timeframe": "minute",
                        "limit": limit,
                    }
                )
            except Exception:
                break

            if frame is None or len(frame) == 0:
                break

            frame = frame.copy()
            frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
            frame = frame.dropna(subset=["datetime"])
            if frame.empty:
                break

            parts.append(frame)
            remaining -= len(frame)

            oldest = frame["datetime"].min()
            cursor = (oldest - timedelta(seconds=1)).to_pydatetime()
            if len(frame) < limit:
                break

        if not parts:
            return pd.DataFrame()

        df = pd.concat(parts, ignore_index=True)
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp")
            df = df.drop_duplicates(subset=["timestamp"], keep="last")
        else:
            df = df.sort_values("datetime")
            df = df.drop_duplicates(subset=["datetime"], keep="last")

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close", "volume", "datetime"])
        return df.reset_index(drop=True)

    def _to_5m(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = (
            df.set_index("datetime")
            .resample("5min")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .dropna()
            .reset_index()
        )
        return out

    def _detect_sigma_breakout(self, df: pd.DataFrame, window: int) -> Optional[Dict[str, Any]]:
        if df.empty or len(df) < window + 2:
            return None

        ret = df["close"].pct_change()
        rolling_std = ret.rolling(window=window).std(ddof=0)
        last_ret = float(ret.iloc[-1])
        last_std = float(rolling_std.iloc[-1])

        if np.isnan(last_ret) or np.isnan(last_std) or last_std <= 0:
            return None

        trigger_value = self.sigma_multiplier * last_std
        if abs(last_ret) <= trigger_value:
            return None

        return {
            "last_return": last_ret,
            "rolling_std": last_std,
            "sigma_multiplier": self.sigma_multiplier,
            "trigger_threshold": trigger_value,
            "direction": "up" if last_ret > 0 else "down",
            "bars": window,
        }

    def _detect_atr_breakout(self, df: pd.DataFrame, period: int) -> Optional[Dict[str, Any]]:
        if df.empty or len(df) < period + 2:
            return None

        prev_close = df["close"].shift(1)
        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - prev_close).abs()
        tr3 = (df["low"] - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False).mean()

        last_atr = float(atr.iloc[-1])
        last_move = float((df["close"].iloc[-1] - df["close"].iloc[-2]))

        if np.isnan(last_atr) or last_atr <= 0:
            return None

        threshold = self.atr_multiplier * last_atr
        if abs(last_move) <= threshold:
            return None

        return {
            "last_close_move": last_move,
            "atr": last_atr,
            "atr_multiplier": self.atr_multiplier,
            "trigger_threshold": threshold,
            "direction": "up" if last_move > 0 else "down",
            "period": period,
        }

    def _detect_volume_price_divergence(self, df: pd.DataFrame, bars: int) -> Optional[Dict[str, Any]]:
        if df.empty or len(df) < bars + 1:
            return None

        start_close = float(df["close"].iloc[-bars - 1])
        end_close = float(df["close"].iloc[-1])
        start_vol = float(df["volume"].iloc[-bars - 1])
        end_vol = float(df["volume"].iloc[-1])

        if start_close <= 0 or start_vol <= 0:
            return None

        price_change_pct = (end_close - start_close) / start_close
        volume_change_pct = (end_vol - start_vol) / start_vol

        opposite_direction = price_change_pct * volume_change_pct < 0
        if not opposite_direction:
            return None

        if abs(price_change_pct) < self.min_price_change_pct:
            return None
        if abs(volume_change_pct) < self.min_volume_change_pct:
            return None

        return {
            "price_change_pct": price_change_pct,
            "volume_change_pct": volume_change_pct,
            "bars": bars,
        }

    def _detect_quant_factor_signal(self, pair: str) -> Optional[Dict[str, Any]]:
        try:
            quant_result = generate_builtin_quant_signals(pair)
        except Exception:
            return None

        blended = quant_result.get("blended", {})
        signal = blended.get("signal")
        strength = float(blended.get("strength_0_to_1") or 0.0)
        if signal in (None, "NEUTRAL"):
            return None
        if strength < self.quant_strength_threshold:
            return None

        return {
            "signal": signal,
            "strength_0_to_1": strength,
            "threshold": self.quant_strength_threshold,
            "latest_datetime": quant_result.get("latest_datetime"),
            "factors": quant_result.get("factors", []),
        }


def _default_keywords_for_pair(pair: str) -> List[str]:
    tokens = [x.strip().lower() for x in pair.replace("-", "/").split("/") if x.strip()]
    extras = {
        "weth": ["eth", "ethereum"],
        "usdc": ["usd coin", "circle"],
        "btc": ["bitcoin"],
        "wbtc": ["btc", "bitcoin"],
    }

    keywords = set(tokens)
    for token in tokens:
        for alias in extras.get(token, []):
            keywords.add(alias)
    return sorted(keywords)


def _parse_rss_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = pd.to_datetime(value, utc=True)
        return ts.to_pydatetime()
    except Exception:
        return None


@tool
def fetch_trigger_watch_news(
    limit: Annotated[int, "Maximum number of combined SEC + watched X posts to return"] = 60,
) -> str:
    """Fetch SEC press releases and watched X-account posts used by trigger runtime."""
    from tradingagents.dataflows.config import get_config

    cfg = get_config()
    twitter_handles = cfg.get("trigger_twitter_accounts", [])
    nitter_instances = cfg.get("trigger_nitter_instances", DEFAULT_NITTER_INSTANCES)
    lookback_minutes = int(cfg.get("trigger_news_lookback_minutes", 240))

    since = datetime.utcnow() - timedelta(minutes=max(1, lookback_minutes))
    sources: List[NewsSource] = [SecPressReleaseSource()]
    if twitter_handles:
        sources.append(
            TwitterAccountsRssSource(
                handles=twitter_handles,
                nitter_instances=nitter_instances,
            )
        )

    items: List[NewsItem] = []
    for source in sources:
        try:
            items.extend(source.fetch_items(since=since))
        except Exception:
            continue

    deduped: Dict[str, NewsItem] = {}
    for item in items:
        deduped[item.item_id] = item

    sorted_items = sorted(
        deduped.values(),
        key=lambda x: x.published_at or datetime.min,
        reverse=True,
    )[: max(1, limit)]

    payload = [
        {
            "id": item.item_id,
            "source": item.source,
            "title": item.title,
            "summary": item.summary,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "url": item.url,
        }
        for item in sorted_items
    ]

    return json.dumps(payload, ensure_ascii=False, indent=2)
