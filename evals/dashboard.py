# evals/dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCORES_CSV = ROOT / "evals" / "data" / "scores.csv"
DIGESTS_DIR = ROOT / "evals" / "data" / "digests"
THRESHOLD = 3.0

DIMENSIONS = {
    "interest_priority_adherence": "Interest Priority",
    "summary_quality": "Summary Quality",
    "source_diversity": "Source Diversity",
    "signal_to_noise": "Signal-to-Noise",
    "theme_and_editorial_voice": "Theme & Voice",
    "content_freshness": "Freshness",
    "source_failure_recovery": "Failure Recovery",
    "novelty": "Novelty",
}

st.set_page_config(page_title="Daily Digest Evals", layout="wide")
st.title("📊 Daily Digest — Eval Dashboard")

@st.cache_data(ttl=60)
def load_scores() -> pd.DataFrame:
    df = pd.read_csv(SCORES_CSV)
    df["digest_date"] = pd.to_datetime(df["digest_date"])
    return df.sort_values("digest_date")

if not SCORES_CSV.exists():
    st.warning("No scores yet. Run `python -m evals.scoring_pipeline` first.")
    st.stop()

df = load_scores()

# --- KPIs ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Digests Evaluated", len(df))
c2.metric("Avg Overall Score", f"{df['overall_score'].mean():.2f} / 5")
c3.metric("Flagged (< 3.0)", int((df["overall_score"] < THRESHOLD).sum()))
c4.metric("Best Run", f"{df['overall_score'].max():.1f}")
c5.metric("Worst Run", f"{df['overall_score'].min():.1f}")

st.divider()

# --- Overall score over time ---
st.subheader("Overall Score Over Time")
fig = px.line(df, x="digest_date", y="overall_score", markers=True,
              labels={"overall_score": "Score", "digest_date": "Date"})
fig.add_hline(y=THRESHOLD, line_dash="dash", line_color="red",
              annotation_text="Threshold (3.0)")
fig.add_hline(y=df["overall_score"].mean(), line_dash="dot", line_color="grey",
              annotation_text=f"Mean ({df['overall_score'].mean():.1f})")
st.plotly_chart(fig, use_container_width=True)

# --- Dimension averages ---
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Average by Dimension")
    avgs = {label: df[f"{dim}_score"].mean() for dim, label in DIMENSIONS.items()}
    bar_colors = ["#ef4444" if v < THRESHOLD else "#22c55e" for v in avgs.values()]
    fig2 = go.Figure(go.Bar(
        x=list(avgs.values()), y=list(avgs.keys()),
        orientation="h", marker_color=bar_colors,
    ))
    fig2.update_layout(xaxis=dict(range=[0, 5]), height=350, margin=dict(l=0))
    st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.subheader("Score Distribution")
    fig3 = px.histogram(df, x="overall_score", nbins=10, range_x=[1, 5],
                        labels={"overall_score": "Overall Score", "count": "Digests"})
    st.plotly_chart(fig3, use_container_width=True)

# --- Dimension trends over time ---
st.subheader("Dimension Trends Over Time")
dim_cols = [f"{dim}_score" for dim in DIMENSIONS]
dim_rename = {f"{dim}_score": label for dim, label in DIMENSIONS.items()}
fig4 = px.line(df.rename(columns=dim_rename), x="digest_date",
               y=list(dim_rename.values()), markers=False)
st.plotly_chart(fig4, use_container_width=True)

# --- Flagged digests ---
st.subheader("⚠️ Flagged Digests (Overall < 3.0)")
flagged = df[df["overall_score"] < THRESHOLD].sort_values("overall_score")
if flagged.empty:
    st.success("No flagged digests.")
else:
    for _, row in flagged.iterrows():
        date_str = row["digest_date"].strftime("%Y-%m-%d")
        digest_path = DIGESTS_DIR / f"{date_str}_digest.html"
        with st.expander(f"{date_str} — Score: {row['overall_score']:.1f}"):
            st.markdown(f"**Top Issue:** {row['top_issue']}")
            st.markdown(f"**Top Strength:** {row['top_strength']}")
            st.markdown(f"**Summary:** {row['overall_summary']}")
            st.divider()
            for dim, label in DIMENSIONS.items():
                score = row[f"{dim}_score"]
                icon = "🔴" if score < 3 else "🟡" if score < 4 else "🟢"
                st.markdown(f"{icon} **{label}:** {score}/5 — _{row[f'{dim}_explanation']}_")
            if digest_path.exists():
                with open(digest_path) as f:
                    st.markdown("**Original digest:**")
                    st.components.v1.html(f.read(), height=600, scrolling=True)

# --- Browse all ---
st.subheader("All Evaluated Digests")
display_cols = (
    ["digest_date", "overall_score"]
    + [f"{d}_score" for d in DIMENSIONS]
    + ["top_issue", "sources_failed", "items_included"]
)
available = [c for c in display_cols if c in df.columns]
st.dataframe(df[available].sort_values("digest_date", ascending=False), use_container_width=True)
