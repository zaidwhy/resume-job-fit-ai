"""Job Application Tracker - save, track, and export your analyses."""

import streamlit as st

from secrets_bridge import load_secrets_into_env

load_secrets_into_env(("GEMINI_API_KEY", "GOOGLE_API_KEY"))

from db import (
    STATUSES,
    delete_application,
    export_csv,
    get_all_applications,
    get_score_history,
    get_stats,
    update_notes,
    update_status,
)
from ui_colors import score_color

st.set_page_config(page_title="Job Tracker - Resume Job-Fit AI", page_icon="📋", layout="wide")

st.title("📋 Job Application Tracker")
st.caption("Every analysis you save lands here. Track status, take notes, export to CSV.")

# --- Summary stats -----------------------------------------------------------

stats = get_stats()

if stats["total"] == 0:
    st.info(
        "No applications saved yet. Go to the main page, run an analysis, "
        "and click **Save to tracker**."
    )
else:
    col_total, col_avg, col_applied, col_interview, col_offer = st.columns(5)
    col_total.metric("Total saved", stats["total"])
    col_avg.metric("Avg fit score", f"{stats['avg_score']}/100")
    col_applied.metric("Applied", stats["by_status"].get("Applied", 0))
    col_interview.metric("Interviewing", stats["by_status"].get("Interviewing", 0))
    col_offer.metric("Offers", stats["by_status"].get("Offer", 0))

    # Score trend chart - shown when 3+ entries exist
    history = get_score_history()
    if len(history) >= 3:
        import altair as alt
        import pandas as pd

        df = pd.DataFrame(history)
        df["saved_on"] = pd.to_datetime(df["saved_on"])
        chart = (
            alt.Chart(df)
            .mark_line(point=True, color="#4f46e5")
            .encode(
                x=alt.X("saved_on:T", title="Date", axis=alt.Axis(format="%b %d")),
                y=alt.Y("score:Q", scale=alt.Scale(domain=[0, 100]), title="Fit Score"),
                tooltip=[
                    alt.Tooltip("saved_on:T", title="Date", format="%b %d, %Y"),
                    alt.Tooltip("score:Q", title="Score"),
                    alt.Tooltip("job_title:N", title="Role"),
                ],
            )
            .properties(height=180, title="Fit Score Trend")
        )
        st.altair_chart(chart, use_container_width=True)
    elif stats["total"] > 0:
        st.caption(f"Save {3 - stats['total']} more application{'s' if 3 - stats['total'] != 1 else ''} to see your score trend chart.")

    # --- Analytics expander --------------------------------------------------
    all_apps = get_all_applications()

    with st.expander("📊 Analytics", expanded=False):
        import altair as alt
        import pandas as pd

        left_chart, right_chart = st.columns(2)

        with left_chart:
            pipeline_df = pd.DataFrame([
                {"Status": s, "Count": stats["by_status"].get(s, 0)}
                for s in STATUSES
            ])
            pipeline_chart = (
                alt.Chart(pipeline_df)
                .mark_bar()
                .encode(
                    x=alt.X("Count:Q", title="Applications"),
                    y=alt.Y("Status:N", sort=STATUSES, title=None),
                    color=alt.condition(
                        alt.datum.Count > 0,
                        alt.value("#4f46e5"),
                        alt.value("#e5e7eb"),
                    ),
                    tooltip=["Status:N", "Count:Q"],
                )
                .properties(height=170, title="Application Pipeline")
            )
            st.altair_chart(pipeline_chart, use_container_width=True)

        with right_chart:
            score_df = pd.DataFrame({"Score": [a["score"] for a in all_apps]})
            hist_chart = (
                alt.Chart(score_df)
                .mark_bar(color="#4f46e5", opacity=0.75)
                .encode(
                    x=alt.X("Score:Q", bin=alt.Bin(step=10), title="Fit Score"),
                    y=alt.Y("count():Q", title="Count"),
                    tooltip=[
                        alt.Tooltip("Score:Q", bin=True, title="Score range"),
                        alt.Tooltip("count():Q", title="Applications"),
                    ],
                )
                .properties(height=170, title="Score Distribution")
            )
            st.altair_chart(hist_chart, use_container_width=True)

        applied_pool = sum(
            stats["by_status"].get(s, 0) for s in ["Applied", "Interviewing", "Offer", "Rejected"]
        )
        offers = stats["by_status"].get("Offer", 0)
        if applied_pool > 0 and offers > 0:
            rate = round(offers / applied_pool * 100)
            st.metric("Offer rate", f"{rate}%", help="Offers ÷ all progressed applications")

    st.divider()

    # --- Filter bar ----------------------------------------------------------
    filter_col, sort_col, _ = st.columns([2, 2, 4])
    with filter_col:
        status_filter = st.selectbox(
            "Filter by status", ["All"] + STATUSES, index=0
        )
    with sort_col:
        sort_by = st.selectbox("Sort by", ["Newest first", "Score (high→low)", "Score (low→high)"])

    apps = list(all_apps)  # reuse already-fetched data

    # Apply filter
    if status_filter != "All":
        apps = [a for a in apps if a["status"] == status_filter]

    # Apply sort
    if sort_by == "Score (high→low)":
        apps.sort(key=lambda a: a["score"], reverse=True)
    elif sort_by == "Score (low→high)":
        apps.sort(key=lambda a: a["score"])

    if not apps:
        st.info(f"No applications with status '{status_filter}'.")
    else:
        st.markdown(f"**{len(apps)} application{'s' if len(apps) != 1 else ''}**")

        for app in apps:
            score = app["score"]
            color = score_color(score)

            with st.container(border=True):
                head, score_col = st.columns([6, 1])
                with head:
                    st.markdown(f"### {app['job_title']}")
                    company_str = f" · {app['company']}" if app["company"] else ""
                    st.caption(f"Saved {app['saved_on']}{company_str}")
                with score_col:
                    st.markdown(
                        f"<div style='text-align:center;padding-top:0.3rem;'>"
                        f"<span style='font-size:2rem;font-weight:800;color:{color};'>{score}</span>"
                        f"<span style='font-size:0.85rem;color:#888;'>/100</span></div>",
                        unsafe_allow_html=True,
                    )

                ctrl_col, note_col, del_col = st.columns([2, 5, 1])

                with ctrl_col:
                    new_status = st.selectbox(
                        "Status",
                        STATUSES,
                        index=STATUSES.index(app["status"]),
                        key=f"status_{app['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != app["status"]:
                        update_status(app["id"], new_status)
                        st.rerun()

                with note_col:
                    new_notes = st.text_input(
                        "Notes",
                        value=app["notes"],
                        placeholder="Add notes (recruiter name, next steps…)",
                        key=f"notes_{app['id']}",
                        label_visibility="collapsed",
                    )
                    if new_notes != app["notes"]:
                        update_notes(app["id"], new_notes)
                        st.rerun()

                with del_col:
                    if st.button("🗑️", key=f"del_{app['id']}", help="Delete this entry"):
                        delete_application(app["id"])
                        st.rerun()

    # --- Export --------------------------------------------------------------
    st.divider()
    st.download_button(
        label="Export all as CSV",
        data=export_csv(),
        file_name="job_applications.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Built in public by Zaid Ali Syed "
    "· [Live demo](https://resume-job-fit-ai.streamlit.app) "
    "· [GitHub](https://github.com/syzayd/resume-job-fit-ai)"
)
