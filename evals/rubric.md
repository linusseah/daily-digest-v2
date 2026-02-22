# Scoring Rubric for Daily Digest Evaluation

Eight dimensions, each scored 1–5. The rubric is the source of truth — write it to `evals/rubric.md` and inject it verbatim into every judge prompt. Weights are used only for the overall score calculation in the pipeline, not shown to the judge.

## Dimension 1: Interest Priority Adherence (weight: 0.25)

*Does the digest reflect the priority tiers in `user_profile.yaml`? High-priority topics (AI agents, LLM architecture, developer tools, AI research, robotics) should dominate. Medium-priority (VC funding, PM practices, product launches) should appear occasionally. Low-priority (general tech, SF events) should appear rarely or not at all unless exceptional.*

| Score | Meaning |
|---|---|
| 5 | High-priority topics fill 70%+ of the digest. Medium appear selectively. Low-priority only if genuinely exceptional. Every item maps to a stated interest. |
| 4 | Strong alignment. High-priority dominates, minor presence of medium-priority. At most 1 low-priority item. |
| 3 | Adequate alignment. Mix of high and medium feels roughly balanced, or 2-3 items feel off-profile. |
| 2 | Weak alignment. Medium-priority content is overrepresented. Multiple items feel like generic tech news. |
| 1 | Poor alignment. Digest resembles a generic tech roundup with little connection to stated interest priorities. |

## Dimension 2: Summary Quality (weight: 0.20)

*Do summaries capture the actual insight, argument, or finding — not just the headline rewritten? The agent's system prompt demands it write "like a knowledgeable friend who tells you only what actually matters." Does it?*

| Score | Meaning |
|---|---|
| 5 | Nearly every summary adds clear value beyond the title: explains why the story matters, captures the key finding, or provides useful context. Reader learns something from the summary alone. |
| 4 | Most summaries are insightful. One or two feel thin or headline-adjacent. |
| 3 | Uneven. Some summaries are genuinely useful; others are headline rewrites. |
| 2 | Most summaries restate the title or lede with different words. Low information density. |
| 1 | Summaries consistently fail to add value. Could be replaced by the headline alone. |

## Dimension 3: Source Diversity & Tool Use (weight: 0.15)

*Given the agent has access to 6 known sources (Simon Willison, TLDR, TechCrunch, Product Hunt, Lenny's, Funcheap SF) plus web search via Exa, does the digest draw from a sensibly diverse set rather than over-indexing on one or two? Were the right sources used for the right content?*

**Quantitative thresholds:** Calculate the percentage of items from the single most-used source. A well-balanced digest should have no source contributing more than 40% of total items.

| Score | Meaning |
|---|---|
| 5 | Content draws from 4+ sources. No single source exceeds 30% of items. Web search used appropriately to fill gaps. Good balance across RSS and newsletter sources. |
| 4 | 3-4 sources represented. One source may contribute up to 40% of items, but others are meaningfully present. Web search used where relevant. |
| 3 | 2-3 sources represented. One source contributes 40-60% of items. Noticeable clustering but some variety exists. |
| 2 | Heavy reliance on 1-2 sources. A single source contributes 60-80% of items. Other sources are token gestures. |
| 1 | Single-source digest. One source contributes 80%+ of items. Little evidence of cross-source curation. |

## Dimension 4: Signal-to-Noise Ratio (weight: 0.15)

*The agent is configured for 10-20 items max. Is every included item worth its slot? The `min_relevance_score: 0.6` rule implies the agent should be filtering ruthlessly. Does it?*

| Score | Meaning |
|---|---|
| 5 | Every item clearly earns its place. No filler, no padding, no obligatory inclusions. Digest respects the reader's time. |
| 4 | Mostly high-signal. 1-2 items could have been cut without meaningful loss. |
| 3 | Noticeable filler. 3-4 items feel like they were included for completeness, not quality. |
| 2 | Quantity over quality. Half the items feel marginal. The agent didn't filter ruthlessly enough. |
| 1 | Firehose. The digest includes too much, with little apparent curation. |

## Dimension 5: Theme Detection & Editorial Voice (weight: 0.10)

*The system prompt explicitly asks the agent to: (a) identify the day's connecting theme, and (b) write a 2-3 sentence editorial intro framing it. Does the agent do this well? Is the theme insightful or generic? Does the structure reflect "group by theme, not source"?*

| Score | Meaning |
|---|---|
| 5 | Clear, non-obvious daily theme identified. Editorial intro is specific and insightful — names the theme, explains why it matters today. Items are genuinely grouped by theme, not by source. |
| 4 | Theme is present and reasonable. Intro is good. Grouping mostly theme-based with minor inconsistencies. |
| 3 | Theme exists but feels generic ("lots of AI news today"). Intro is flat. Grouping is partially thematic. |
| 2 | Theme is vague or absent. Intro reads like a table of contents. Structure is more source-based than theme-based. |
| 1 | No coherent theme. No editorial voice. Feels like a list, not a briefing. |

## Dimension 6: Content Freshness (weight: 0.10)

*`content_rules.stale_after_hours: 48` in `user_profile.yaml` means items older than 48 hours should be excluded unless exceptional. Does the digest feel current?*

| Score | Meaning |
|---|---|
| 5 | All items from the past 24-48 hours. Digest captures the current moment. |
| 4 | Most items recent. 1-2 older items with clear justification (evergreen quality, follow-up to recent story). |
| 3 | Mixed recency. Several items are older than 48h with no obvious reason for inclusion. |
| 2 | Notably stale. Multiple items from 3-7+ days ago. |
| 1 | No sense of currency. Could have been written last week. |

## Dimension 7: Source Failure Recovery (weight: 0.03)

*When sources fail (available in the run log as `sources_failed`), does the agent recover gracefully — using web search or other sources to fill the gap — rather than producing a thin digest? This dimension is only meaningful when failures are logged. If no sources failed, default to 5.*

| Score | Meaning |
|---|---|
| 5 | Source failures had no visible impact on digest quality. Agent used web search or alternative sources to fill gaps, or no failures occurred. |
| 4 | Minor impact from failures. 1 gap is visible but the overall digest is solid. |
| 3 | Failures left a noticeable hole in one content area (e.g., no Product Hunt section when source failed). |
| 2 | Multiple failures led to a thin or unbalanced digest. Recovery attempts were inadequate. |
| 1 | Significant failures with no meaningful recovery. Digest is missing major expected content areas. |

## Dimension 8: Novelty (weight: 0.02)

*Does the digest surface anything the reader is unlikely to have already seen — a non-obvious source, an underreported angle, or a fresh take — rather than just aggregating the day's most-forwarded posts? Also considers whether items were already featured in the previous 1-2 digests.*

**Repetition penalty:** Check if any items (same story/development) appeared in the past 2 days' digests. Each repeated item reduces the score by 1 point.

| Score | Meaning |
|---|---|
| 5 | Several items feel genuinely non-obvious. At least one "hidden gem" the reader probably didn't see elsewhere. No repetition from recent digests (past 2 days). |
| 4 | A few non-obvious picks. Mostly solid if familiar, with pleasant surprises. At most 1 item repeated from past 2 days with meaningful new development. |
| 3 | Mostly covers the expected stories. Little curation edge over a standard news feed. May include 1-2 repeated items from recent digests without new angles. |
| 2 | Everything here was already in the reader's Twitter/X feed before this digest ran. Or contains 3+ repeated items from past 2 days. |
| 1 | The digest is a pure rehash of trending posts. No discovery value. Or heavily duplicates content from yesterday's digest (4+ repeated items). |
