"""Generate PDF report for an analysis run."""
import io
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AnalysisRun, Competitor, Insight, DifferentiationOpportunity
from app.models.analysis import AnalysisCompetitor
from app.models.news import NewsMention, MarketPresence, WebContent


class PDFGenerator:
    """Build a PDF with Executive Summary, Market Presence, Competitor Comparison, News & Sentiment, Insights."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, analysis_id: int) -> bytes:
        """Produce PDF bytes for the given analysis run."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

        run_result = await self.db.execute(
            select(AnalysisRun).where(AnalysisRun.id == analysis_id).options(
                selectinload(AnalysisRun.competitor_links).selectinload(AnalysisCompetitor.competitor),
            )
        )
        run = run_result.scalar_one_or_none()
        if not run:
            raise ValueError("Analysis not found")
        competitors = [link.competitor for link in run.competitor_links]
        news_result = await self.db.execute(select(NewsMention).where(NewsMention.analysis_run_id == analysis_id))
        news = list(news_result.scalars().all())
        mp_result = await self.db.execute(select(MarketPresence).where(MarketPresence.analysis_run_id == analysis_id))
        market = list(mp_result.scalars().all())
        insights_result = await self.db.execute(select(Insight).where(Insight.analysis_run_id == analysis_id))
        insights = list(insights_result.scalars().all())
        opp_result = await self.db.execute(select(DifferentiationOpportunity).where(DifferentiationOpportunity.analysis_run_id == analysis_id))
        opportunities = list(opp_result.scalars().all())

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(name="Title", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
        story.append(Paragraph("Competitor Analysis Report", title_style))
        story.append(Paragraph(f"<b>Run:</b> {run.name} | <b>Status:</b> {run.status} | <b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        story.append(Paragraph(f"This report covers {len(competitors)} competitor(s), {len(news)} news mention(s), and {len(insights)} insight(s).", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Market Presence", styles["Heading2"]))
        if market:
            data = [["Competitor", "Mentions", "Sentiment (avg)", "Visibility", "Trend"]]
            comp_map = {c.id: c.name for c in competitors}
            for m in market:
                data.append([
                    comp_map.get(m.competitor_id, str(m.competitor_id)),
                    str(m.mention_count or 0),
                    f"{m.sentiment_average:.2f}" if m.sentiment_average is not None else "—",
                    f"{m.visibility_score:.0f}" if m.visibility_score is not None else "—",
                    m.trend_direction or "—",
                ])
            t = Table(data, colWidths=[1.5 * inch, 0.8 * inch, 1 * inch, 0.8 * inch, 0.8 * inch])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
            story.append(t)
        else:
            story.append(Paragraph("No market presence data for this run.", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Competitor Comparison", styles["Heading2"]))
        data = [["Name", "Industry", "Website"]]
        for c in competitors:
            data.append([c.name or "—", c.industry or "—", (c.website_url or "—")[:50]])
        t = Table(data, colWidths=[2 * inch, 1.5 * inch, 2.5 * inch])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("News & Sentiment", styles["Heading2"]))
        if news:
            data = [["Competitor ID", "Title", "Source", "Sentiment"]]
            for n in news[:30]:
                data.append([str(n.competitor_id), (n.title or "")[:40], (n.source or "—")[:20], f"{n.sentiment_score:.2f}" if n.sentiment_score is not None else "—"])
            t = Table(data, colWidths=[0.8 * inch, 2.2 * inch, 1.2 * inch, 0.8 * inch])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
            story.append(t)
        else:
            story.append(Paragraph("No news mentions for this run.", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Insights", styles["Heading2"]))
        for i in insights:
            story.append(Paragraph(f"<b>{i.title}</b> [{i.insight_type}]", styles["Normal"]))
            if i.description:
                story.append(Paragraph(i.description[:500], styles["Normal"]))
            if i.actionable_recommendation:
                story.append(Paragraph(f"Recommendation: {i.actionable_recommendation[:300]}", styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))
        if not insights:
            story.append(Paragraph("No insights generated yet.", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Differentiation Opportunities", styles["Heading2"]))
        for o in opportunities:
            story.append(Paragraph(f"<b>{o.title}</b>", styles["Normal"]))
            if o.description:
                story.append(Paragraph(o.description[:400], styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))
        if not opportunities:
            story.append(Paragraph("No opportunities generated yet.", styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()
