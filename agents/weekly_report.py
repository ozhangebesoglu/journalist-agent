"""
Weekly/Monthly Report Generator
Uzun vadeli trend analizi ve haftalık/aylık raporlar

Özellikler:
    - Haftalık trend raporu
    - Aylık özet raporu
    - Teknoloji yükseliş/düşüş analizi
    - Dil bazlı trend analizi
"""

import json
from datetime import date, datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

from agents import db


@dataclass
class WeeklyTrendData:
    """Haftalık trend verisi."""
    week_start: str
    week_end: str
    
    # Repo istatistikleri
    total_repos_tracked: int
    new_repos: int
    rising_repos: list
    declining_repos: list
    
    # Dil trendleri
    language_trends: dict  # {"Python": {"count": 10, "growth": 15.2}, ...}
    top_languages: list
    
    # Konu trendleri
    hot_topics: list  # ["ai", "llm", "rust"]
    
    # Sosyal medya
    hn_top_stories: list
    reddit_hot_posts: list
    most_discussed_repos: list
    
    # Özet istatistikler
    avg_star_growth: float
    total_stars_gained: int
    total_mentions: int


def generate_weekly_report(chat_id: str = None) -> dict:
    """
    Haftalık trend raporu oluştur.
    
    Returns:
        Haftalık rapor verisi
    """
    today = date.today()
    week_start = today - timedelta(days=7)
    
    report = {
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "generated_at": datetime.now().isoformat(),
        "rising_stars": [],
        "declining_repos": [],
        "language_trends": {},
        "hot_topics": [],
        "most_discussed": [],
        "summary": {},
        "insights": []
    }
    
    # Tüm repo'ları al
    repos = db.get_all_repos_with_snapshots()
    
    if not repos:
        report["summary"] = {"message": "Henüz yeterli veri yok. Birkaç gün veri toplandıktan sonra rapor oluşturulabilir."}
        return report
    
    # Trend metrikleri hesapla
    from agents.trend_analyzer import calculate_trend_metrics, TrendStatus
    
    all_metrics = []
    language_stats = defaultdict(lambda: {"count": 0, "total_growth": 0, "repos": []})
    topic_counts = defaultdict(int)
    total_growth = 0
    
    for repo in repos:
        metrics = calculate_trend_metrics(repo["id"], repo["full_name"])
        if metrics:
            all_metrics.append(metrics)
            total_growth += metrics.growth_7d
            
            # Dil istatistikleri
            lang = repo.get("language", "Other") or "Other"
            language_stats[lang]["count"] += 1
            language_stats[lang]["total_growth"] += metrics.growth_7d
            language_stats[lang]["repos"].append(repo["full_name"])
    
    # Rising/Declining repo'ları ayır
    rising = [m for m in all_metrics if m.status == TrendStatus.RISING]
    declining = [m for m in all_metrics if m.status == TrendStatus.DECLINING]
    
    rising.sort(key=lambda x: x.growth_7d, reverse=True)
    declining.sort(key=lambda x: x.growth_7d)
    
    report["rising_stars"] = [
        {
            "name": m.repo_name,
            "stars": m.current_stars,
            "growth_7d": m.growth_7d,
            "growth_pct": m.growth_7d_pct,
            "mentions": m.total_mentions_7d
        }
        for m in rising[:10]
    ]
    
    report["declining_repos"] = [
        {
            "name": m.repo_name,
            "stars": m.current_stars,
            "growth_7d": m.growth_7d,
            "growth_pct": m.growth_7d_pct
        }
        for m in declining[:5]
    ]
    
    # Dil trendleri
    for lang, stats in language_stats.items():
        if stats["count"] > 0:
            report["language_trends"][lang] = {
                "count": stats["count"],
                "avg_growth": round(stats["total_growth"] / stats["count"], 1),
                "total_growth": stats["total_growth"]
            }
    
    # Top diller
    sorted_langs = sorted(
        report["language_trends"].items(),
        key=lambda x: x[1]["total_growth"],
        reverse=True
    )
    report["top_languages"] = [{"language": k, **v} for k, v in sorted_langs[:5]]
    
    # En çok tartışılan
    discussed = sorted(all_metrics, key=lambda x: x.total_mentions_7d, reverse=True)
    report["most_discussed"] = [
        {
            "name": m.repo_name,
            "hn_mentions": m.hn_mentions_7d,
            "reddit_mentions": m.reddit_mentions_7d,
            "total": m.total_mentions_7d
        }
        for m in discussed[:5] if m.total_mentions_7d > 0
    ]
    
    # Özet
    report["summary"] = {
        "total_repos": len(all_metrics),
        "rising_count": len(rising),
        "declining_count": len(declining),
        "avg_growth": round(total_growth / len(all_metrics), 1) if all_metrics else 0,
        "total_stars_gained": total_growth,
        "top_language": sorted_langs[0][0] if sorted_langs else "N/A"
    }
    
    # İçgörüler oluştur
    report["insights"] = generate_insights(report, all_metrics)
    
    # Veritabanına kaydet
    if chat_id:
        db.save_weekly_report(chat_id, week_start, today, report)
    
    return report


def generate_insights(report: dict, metrics: list) -> list:
    """Rapor verilerinden içgörüler çıkar."""
    insights = []
    
    # En hızlı yükselen
    if report["rising_stars"]:
        top = report["rising_stars"][0]
        insights.append(f"🚀 Bu haftanın yıldızı: **{top['name']}** (+{top['growth_7d']} ⭐, %{top['growth_pct']} artış)")
    
    # Dil trendi
    if report["top_languages"]:
        top_lang = report["top_languages"][0]
        insights.append(f"📈 En popüler dil: **{top_lang['language']}** ({top_lang['count']} repo, +{top_lang['total_growth']} ⭐)")
    
    # Sosyal medya buzz
    if report["most_discussed"]:
        top_disc = report["most_discussed"][0]
        insights.append(f"🔥 En çok konuşulan: **{top_disc['name']}** (HN: {top_disc['hn_mentions']}, Reddit: {top_disc['reddit_mentions']})")
    
    # Genel trend
    summary = report["summary"]
    if summary.get("avg_growth", 0) > 100:
        insights.append(f"📊 Güçlü bir hafta! Ortalama repo başına +{summary['avg_growth']} yıldız")
    elif summary.get("avg_growth", 0) < 0:
        insights.append("📉 Yavaş bir hafta. Genel ilgi düşük.")
    
    return insights


def generate_monthly_report(chat_id: str = None) -> dict:
    """
    Aylık trend raporu oluştur.
    """
    today = date.today()
    month_start = today - timedelta(days=30)
    
    # Son 4 haftalık raporu al
    weekly_reports = db.get_weekly_reports(chat_id, limit=4)
    
    report = {
        "month_start": month_start.isoformat(),
        "month_end": today.isoformat(),
        "generated_at": datetime.now().isoformat(),
        "weekly_summaries": [],
        "monthly_rising_stars": [],
        "language_evolution": {},
        "trend_insights": [],
        "predictions": []
    }
    
    if not weekly_reports:
        report["message"] = "Aylık rapor için yeterli veri yok. En az 2 haftalık veri gerekli."
        return report
    
    # Haftalık özetleri ekle
    for wr in weekly_reports:
        data = wr.get("report_data", {})
        report["weekly_summaries"].append({
            "week": wr["week_start"],
            "rising_count": data.get("summary", {}).get("rising_count", 0),
            "avg_growth": data.get("summary", {}).get("avg_growth", 0),
            "top_language": data.get("summary", {}).get("top_language", "N/A")
        })
    
    # Dil evrimi (diller zaman içinde nasıl değişti)
    lang_over_time = defaultdict(list)
    for wr in weekly_reports:
        data = wr.get("report_data", {})
        for lang, stats in data.get("language_trends", {}).items():
            lang_over_time[lang].append(stats.get("total_growth", 0))
    
    for lang, growths in lang_over_time.items():
        avg = sum(growths) / len(growths)
        trend = "rising" if growths[-1] > growths[0] else "declining" if growths[-1] < growths[0] else "stable"
        report["language_evolution"][lang] = {
            "avg_weekly_growth": round(avg, 1),
            "trend": trend,
            "weeks_tracked": len(growths)
        }
    
    # Aylık yükselen yıldızlar (tüm haftalarda sık görünen)
    repo_appearances = defaultdict(int)
    for wr in weekly_reports:
        data = wr.get("report_data", {})
        for repo in data.get("rising_stars", []):
            repo_appearances[repo["name"]] += 1
    
    consistent_risers = [
        {"name": name, "weeks_rising": count}
        for name, count in sorted(repo_appearances.items(), key=lambda x: x[1], reverse=True)
        if count >= 2
    ]
    report["monthly_rising_stars"] = consistent_risers[:10]
    
    # Trend içgörüleri
    if report["monthly_rising_stars"]:
        top = report["monthly_rising_stars"][0]
        report["trend_insights"].append(
            f"🏆 Ayın en tutarlı yükseleni: **{top['name']}** ({top['weeks_rising']} hafta üst üste yükselişte)"
        )
    
    # Dil bazlı içgörü
    rising_langs = [
        (lang, data) for lang, data in report["language_evolution"].items()
        if data["trend"] == "rising"
    ]
    if rising_langs:
        rising_langs.sort(key=lambda x: x[1]["avg_weekly_growth"], reverse=True)
        top_lang = rising_langs[0]
        report["trend_insights"].append(
            f"📈 Yükselen dil: **{top_lang[0]}** (haftalık ortalama +{top_lang[1]['avg_weekly_growth']} ⭐)"
        )
    
    return report


def format_weekly_report_text(report: dict) -> str:
    """Haftalık raporu okunabilir metin formatına çevir."""
    lines = []
    
    lines.append("📊 HAFTALIK TREND RAPORU")
    lines.append(f"📅 {report['week_start']} - {report['week_end']}")
    lines.append("━" * 30)
    
    # Özet
    summary = report.get("summary", {})
    if summary:
        lines.append(f"\n📈 ÖZET")
        lines.append(f"   Toplam repo: {summary.get('total_repos', 0)}")
        lines.append(f"   Yükselen: {summary.get('rising_count', 0)}")
        lines.append(f"   Düşen: {summary.get('declining_count', 0)}")
        lines.append(f"   Ortalama büyüme: +{summary.get('avg_growth', 0)} ⭐")
    
    # Rising Stars
    if report.get("rising_stars"):
        lines.append(f"\n🚀 YÜKSELEN YILDIZLAR")
        for i, repo in enumerate(report["rising_stars"][:5], 1):
            lines.append(f"   {i}. {repo['name']}")
            lines.append(f"      +{repo['growth_7d']} ⭐ (%{repo['growth_pct']})")
    
    # Top Languages
    if report.get("top_languages"):
        lines.append(f"\n💻 TOP DİLLER")
        for lang in report["top_languages"][:3]:
            lines.append(f"   • {lang['language']}: {lang['count']} repo, +{lang['total_growth']} ⭐")
    
    # Most Discussed
    if report.get("most_discussed"):
        lines.append(f"\n🔥 EN ÇOK KONUŞULAN")
        for repo in report["most_discussed"][:3]:
            lines.append(f"   • {repo['name']}")
            lines.append(f"     HN: {repo['hn_mentions']}, Reddit: {repo['reddit_mentions']}")
    
    # Insights
    if report.get("insights"):
        lines.append(f"\n💡 İÇGÖRÜLER")
        for insight in report["insights"]:
            lines.append(f"   {insight}")
    
    return "\n".join(lines)


def format_monthly_report_text(report: dict) -> str:
    """Aylık raporu okunabilir metin formatına çevir."""
    lines = []
    
    lines.append("📅 AYLIK TREND RAPORU")
    lines.append(f"🗓️ {report['month_start']} - {report['month_end']}")
    lines.append("━" * 30)
    
    # Haftalık özetler
    if report.get("weekly_summaries"):
        lines.append(f"\n📊 HAFTALIK ÖZET")
        for week in report["weekly_summaries"]:
            lines.append(f"   {week['week']}: {week['rising_count']} yükselen, +{week['avg_growth']} ortalama")
    
    # Aylık yükselen yıldızlar
    if report.get("monthly_rising_stars"):
        lines.append(f"\n🏆 AYIN YILDIZLARI")
        for repo in report["monthly_rising_stars"][:5]:
            lines.append(f"   • {repo['name']} ({repo['weeks_rising']} hafta yükselişte)")
    
    # Dil evrimi
    if report.get("language_evolution"):
        lines.append(f"\n📈 DİL EVRİMİ")
        for lang, data in list(report["language_evolution"].items())[:5]:
            emoji = "📈" if data["trend"] == "rising" else "📉" if data["trend"] == "declining" else "➡️"
            lines.append(f"   {emoji} {lang}: haftalık +{data['avg_weekly_growth']} ⭐")
    
    # İçgörüler
    if report.get("trend_insights"):
        lines.append(f"\n💡 İÇGÖRÜLER")
        for insight in report["trend_insights"]:
            lines.append(f"   {insight}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    report = generate_weekly_report()
    print(format_weekly_report_text(report))
