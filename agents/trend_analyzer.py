"""
Trend Analyzer
Calculates trend metrics and classifies repository momentum
"""
from dataclasses import dataclass
from enum import Enum

from agents import db


class TrendStatus(Enum):
    RISING = "rising"         # Accelerating growth
    STEADY = "steady"         # Consistent growth
    DECLINING = "declining"   # Slowing down
    NEW = "new"               # < 7 days of data


@dataclass
class TrendMetrics:
    repo_name: str
    repo_id: int
    current_stars: int
    stars_7d_ago: int | None
    stars_14d_ago: int | None
    growth_7d: int              # Absolute growth
    growth_7d_pct: float        # Percentage growth
    growth_trend: float         # Acceleration (positive = speeding up)
    hn_mentions_7d: int
    reddit_mentions_7d: int
    total_mentions_7d: int
    status: TrendStatus
    times_featured: int


def calculate_trend_metrics(repo_id: int, repo_name: str) -> TrendMetrics | None:
    """Calculate full trend metrics for a repository."""
    # Get star growth data
    growth_7d = db.get_star_growth(repo_id, days=7)
    growth_14d = db.get_star_growth(repo_id, days=14)

    if not growth_7d:
        return None

    current_stars, stars_7d_ago = growth_7d
    stars_14d_ago = growth_14d[1] if growth_14d else None

    # Calculate growth metrics
    if stars_7d_ago is not None:
        abs_growth_7d = current_stars - stars_7d_ago
        pct_growth_7d = (abs_growth_7d / stars_7d_ago * 100) if stars_7d_ago > 0 else 0
    else:
        abs_growth_7d = 0
        pct_growth_7d = 0

    # Calculate trend (acceleration)
    # Positive = speeding up, negative = slowing down
    growth_trend = 0.0
    if stars_7d_ago is not None and stars_14d_ago is not None:
        growth_first_week = stars_7d_ago - stars_14d_ago
        growth_second_week = current_stars - stars_7d_ago
        if growth_first_week != 0:
            growth_trend = (growth_second_week - growth_first_week) / abs(growth_first_week)

    # Get mention counts
    mentions = db.get_mention_counts(repo_id, days=7)
    hn_mentions = mentions.get("hn", 0)
    reddit_mentions = mentions.get("reddit", 0)

    # Get feature count
    times_featured = db.get_feature_count(repo_id)

    # Classify trend status
    status = classify_trend(abs_growth_7d, growth_trend, stars_7d_ago)

    return TrendMetrics(
        repo_name=repo_name,
        repo_id=repo_id,
        current_stars=current_stars,
        stars_7d_ago=stars_7d_ago,
        stars_14d_ago=stars_14d_ago,
        growth_7d=abs_growth_7d,
        growth_7d_pct=round(pct_growth_7d, 2),
        growth_trend=round(growth_trend, 2),
        hn_mentions_7d=hn_mentions,
        reddit_mentions_7d=reddit_mentions,
        total_mentions_7d=hn_mentions + reddit_mentions,
        status=status,
        times_featured=times_featured
    )


def classify_trend(growth_7d: int, growth_trend: float, stars_7d_ago: int | None) -> TrendStatus:
    """Classify repo as rising/steady/declining based on metrics."""
    # If we don't have historical data, it's new
    if stars_7d_ago is None:
        return TrendStatus.NEW

    # Rising: significant growth and accelerating
    if growth_7d > 100 and growth_trend > 0.2:
        return TrendStatus.RISING

    # Declining: negative growth or significant slowdown
    if growth_7d < 0 or growth_trend < -0.5:
        return TrendStatus.DECLINING

    # Steady: everything else
    return TrendStatus.STEADY


def generate_trend_report(repos: list[dict]) -> dict:
    """
    Generate weekly trend report.

    Returns:
        {
            "rising_stars": [...],      # Top 5 accelerating repos
            "steady_performers": [...], # Consistent growth
            "cooling_down": [...],      # Declining interest
            "most_discussed": [...],    # Highest HN/Reddit mentions
            "newcomers": [...],         # New this week
            "repeat_performers": [...], # Featured multiple times
            "previously_featured": [...], # Names of repos featured before
            "summary_stats": {...}
        }
    """
    result = {
        "rising_stars": [],
        "steady_performers": [],
        "cooling_down": [],
        "most_discussed": [],
        "newcomers": [],
        "repeat_performers": [],
        "previously_featured": list(db.get_previously_featured(days=7)),
        "summary_stats": {
            "total_repos_tracked": 0,
            "new_repos_this_week": 0,
            "avg_star_growth": 0.0,
            "total_mentions": 0
        }
    }

    all_metrics = []
    total_growth = 0
    new_count = 0
    total_mentions = 0

    for repo in repos:
        repo_record = db.get_repo_by_name(repo["name"])
        if not repo_record:
            continue

        metrics = calculate_trend_metrics(repo_record["id"], repo["name"])
        if not metrics:
            continue

        all_metrics.append(metrics)
        total_growth += metrics.growth_7d
        total_mentions += metrics.total_mentions_7d

        if metrics.status == TrendStatus.NEW:
            new_count += 1

    # Sort and categorize
    for metrics in all_metrics:
        item = {
            "name": metrics.repo_name,
            "current_stars": metrics.current_stars,
            "growth_7d": metrics.growth_7d,
            "growth_7d_pct": metrics.growth_7d_pct,
            "growth_trend": metrics.growth_trend,
            "hn_mentions_7d": metrics.hn_mentions_7d,
            "reddit_mentions_7d": metrics.reddit_mentions_7d,
            "total_mentions_7d": metrics.total_mentions_7d,
            "status": metrics.status.value,
            "times_featured": metrics.times_featured,
            "trend_summary": get_repo_trend_summary(metrics)
        }

        # Categorize by status
        if metrics.status == TrendStatus.RISING:
            result["rising_stars"].append(item)
        elif metrics.status == TrendStatus.STEADY:
            result["steady_performers"].append(item)
        elif metrics.status == TrendStatus.DECLINING:
            result["cooling_down"].append(item)
        elif metrics.status == TrendStatus.NEW:
            result["newcomers"].append(item)

        # Check for repeat performers
        if metrics.times_featured > 1:
            result["repeat_performers"].append(item)

    # Sort each category
    result["rising_stars"].sort(key=lambda x: x["growth_7d"], reverse=True)
    result["steady_performers"].sort(key=lambda x: x["current_stars"], reverse=True)
    result["cooling_down"].sort(key=lambda x: x["growth_7d"])

    # Most discussed (by total mentions)
    result["most_discussed"] = sorted(
        [m for m in all_metrics if m.total_mentions_7d > 0],
        key=lambda x: x.total_mentions_7d,
        reverse=True
    )[:5]
    result["most_discussed"] = [
        {
            "name": m.repo_name,
            "hn_mentions_7d": m.hn_mentions_7d,
            "reddit_mentions_7d": m.reddit_mentions_7d,
            "total_mentions_7d": m.total_mentions_7d,
            "trend_summary": f"HN'de {m.hn_mentions_7d}, Reddit'te {m.reddit_mentions_7d} kez bahsedildi."
        }
        for m in result["most_discussed"]
    ]

    # Limit lists
    result["rising_stars"] = result["rising_stars"][:5]
    result["steady_performers"] = result["steady_performers"][:5]
    result["cooling_down"] = result["cooling_down"][:3]
    result["newcomers"] = result["newcomers"][:5]
    result["repeat_performers"] = result["repeat_performers"][:3]

    # Summary stats
    result["summary_stats"] = {
        "total_repos_tracked": len(all_metrics),
        "new_repos_this_week": new_count,
        "avg_star_growth": round(total_growth / len(all_metrics), 1) if all_metrics else 0,
        "total_mentions": total_mentions
    }

    return result


def get_repo_trend_summary(metrics: TrendMetrics) -> str:
    """Generate human-readable trend summary for a repo."""
    parts = []

    # Star growth
    if metrics.status == TrendStatus.NEW:
        parts.append(f"Bu hafta keşfedildi ({metrics.current_stars} yıldız)")
    elif metrics.growth_7d > 0:
        parts.append(f"Geçen hafta +{metrics.growth_7d} yıldız ({metrics.growth_7d_pct}% artış)")
    elif metrics.growth_7d < 0:
        parts.append(f"Geçen hafta {metrics.growth_7d} yıldız kaybetti")

    # Trend direction
    if metrics.growth_trend > 0.5:
        parts.append("ivme kazanıyor")
    elif metrics.growth_trend < -0.5:
        parts.append("yavaşlıyor")

    # Mentions
    if metrics.total_mentions_7d > 0:
        mention_parts = []
        if metrics.hn_mentions_7d > 0:
            mention_parts.append(f"HN'de {metrics.hn_mentions_7d}x")
        if metrics.reddit_mentions_7d > 0:
            mention_parts.append(f"Reddit'te {metrics.reddit_mentions_7d}x")
        parts.append(f"bahsedildi: {', '.join(mention_parts)}")

    # Featured before
    if metrics.times_featured > 0:
        parts.append(f"daha önce {metrics.times_featured} kez öne çıktı")

    return ". ".join(parts) + "." if parts else "Henüz yeterli veri yok."


if __name__ == "__main__":
    # Test with sample repos
    import json

    repos_path = "data/repos.json"
    try:
        with open(repos_path, encoding="utf-8") as f:
            repos = json.load(f)

        report = generate_trend_report(repos)

        print("=== TREND REPORT ===")
        print(f"\nSummary: {report['summary_stats']}")

        print("\n--- Rising Stars ---")
        for r in report["rising_stars"]:
            print(f"  {r['name']}: {r['trend_summary']}")

        print("\n--- Most Discussed ---")
        for r in report["most_discussed"]:
            print(f"  {r['name']}: {r['trend_summary']}")

    except FileNotFoundError:
        print("repos.json bulunamadı. Önce collector çalıştırın.")
