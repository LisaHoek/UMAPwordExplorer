import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="CSV Scatter Explorer", layout="wide")

st.title("CSV Scatter Explorer")
st.write("Upload a CSV file with columns: `text`, `x`, `y`, `freq`")

uploaded_file = st.file_uploader("Upload your CSV", type="csv")


def scale_sizes_dynamic(freq_series, min_size=4, max_size=30, freq_min=1, freq_max=None):
    """
    Scale frequencies logarithmically to marker sizes.
    Uses the maximum frequency from the data instead of a fixed max.
    """
    freq = pd.to_numeric(freq_series, errors="coerce").fillna(1)
    freq = freq.clip(lower=freq_min)

    if freq_max is None:
        freq_max = freq.max()

    freq_max = max(freq_max, freq_min)
    freq = freq.clip(upper=freq_max)

    log_freq = np.log1p(freq)
    log_min = np.log1p(freq_min)
    log_max = np.log1p(freq_max)

    if log_max == log_min:
        return pd.Series([min_size] * len(freq), index=freq.index)

    scaled = min_size + (log_freq - log_min) / (log_max - log_min) * (max_size - min_size)
    return scaled


if uploaded_file is not None:
    # Read CSV
    df = pd.read_csv(uploaded_file)

    # Check required columns
    required_cols = {"text", "x", "y", "freq"}
    missing = required_cols - set(df.columns)
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    # Clean data
    df = df.copy()
    df["text"] = df["text"].astype(str)
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["freq"] = pd.to_numeric(df["freq"], errors="coerce")
    df = df.dropna(subset=["x", "y", "freq"]).reset_index(drop=True)
    df["freq"] = df["freq"].clip(lower=1).astype(int)

    if df.empty:
        st.warning("No valid rows remain after cleaning x, y, and freq.")
        st.stop()

    # Determine max freq from data
    data_freq_max = int(df["freq"].max())

    # Sidebar settings
    st.sidebar.header("Settings")

    # User typed minimum freq filter
    min_freq_size = st.sidebar.number_input(
        "Minimum freq to show",
        min_value=1,
        max_value=data_freq_max,
        value=1,
        step=1
    )

    # Apply filter for plot
    df_plot = df[df["freq"] >= min_freq_size].copy().reset_index(drop=True)

    use_freq_size = st.sidebar.checkbox("Use frequency-based point size", value=False)

    if use_freq_size:
        min_marker_size = st.sidebar.slider("Minimum point size", 1, 15, 4)
        max_marker_size = st.sidebar.slider("Maximum point size", 5, 50, 20)
        df_plot["marker_size"] = scale_sizes_dynamic(
            df_plot["freq"],
            min_size=min_marker_size,
            max_size=max_marker_size,
            freq_min=1,
            freq_max=data_freq_max
        )
    else:
        fixed_marker_size = st.sidebar.slider("Point size", 1, 10, 4)
        df_plot["marker_size"] = fixed_marker_size

    marker_opacity = st.sidebar.slider("Opacity", 0.1, 1.0, 0.2)
    max_texts = st.sidebar.number_input("Maximum number of texts to display", 10, 10000, 500)

    st.sidebar.caption(f"Total rows: {len(df)}")
    st.sidebar.caption(f"Rows after freq filter: {len(df_plot)}")
    st.sidebar.caption(f"Max freq in data: {data_freq_max}")

    if df_plot.empty:
        st.warning("No points remain after applying the frequency filter.")
        st.stop()

    # Plot
    fig = go.Figure(
        go.Scattergl(
            x=df_plot["x"],
            y=df_plot["y"],
            mode="markers",
            text=df_plot["text"],
            customdata=np.stack([df_plot.index, df_plot["freq"]], axis=-1),
            marker=dict(
                size=df_plot["marker_size"],
                opacity=marker_opacity,
                color="#1f77b4",
                sizemode="diameter",
                line=dict(width=0)
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "x=%{x}<br>"
                "y=%{y}<br>"
                "freq=%{customdata[1]}<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=700,
        dragmode="lasso",
        uirevision="keep_zoom",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="x",
        yaxis_title="y",
    )

    left, right = st.columns([2, 1], gap="large")

    with left:
        st.subheader("Scatter Plot")
        event = st.plotly_chart(
            fig,
            use_container_width=True,
            key="scatter_plot",
            on_select="rerun",
            selection_mode=("box", "lasso"),
            config={
                "scrollZoom": True,
                "displaylogo": False
            }
        )

    # Read selected points
    selected_indices = []
    selected_df = pd.DataFrame()

    try:
        if event and event.selection and event.selection.point_indices:
            selected_indices = list(event.selection.point_indices)
    except Exception:
        try:
            selected_indices = list(event["selection"]["point_indices"])
        except Exception:
            selected_indices = []

    with right:
        st.subheader("Selection")

        if selected_indices:
            selected_df = df_plot.iloc[selected_indices]

            st.success(f"{len(selected_df)} point(s) selected")

            shown_df = selected_df.head(max_texts)

            st.text_area(
                "Selected text",
                value="\n\n".join(shown_df["text"].tolist()),
                height=500
            )

            with st.expander("Show selected rows"):
                st.dataframe(
                    selected_df[["text", "x", "y", "freq"]],
                    use_container_width=True
                )

            csv_selected = selected_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download selection as CSV",
                data=csv_selected,
                file_name="selection.csv",
                mime="text/csv"
            )
        else:
            st.info("Select points using lasso or box selection.")

    st.divider()
    st.subheader("Data Preview (selected)")
    if not selected_df.empty:
        st.dataframe(selected_df, use_container_width=True)
    else:
        st.info("No points selected.")

    st.subheader("Data Preview (plot)")
    st.dataframe(df_plot, use_container_width=True)

else:
    st.info("Please upload a CSV file first.")