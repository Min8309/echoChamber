import csv
import io
import json
from datetime import datetime, timezone

import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8008"


st.set_page_config(
    page_title="EchoChamber 실험 데이터",
    page_icon="📊",
    layout="wide",
)

st.title("EchoChamber 실험 데이터")
st.caption(
    "에이전트, 정보 전달, 가십 이벤트와 "
    "소문 전파 경로 데이터를 내려받습니다."
)


def load_api_data(
    endpoint: str,
):
    response = requests.get(
        f"{API_BASE_URL}{endpoint}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def flatten_record(
    record: dict,
    prefix: str = "",
) -> dict:
    flattened = {}

    for key, value in record.items():
        flattened_key = (
            f"{prefix}_{key}"
            if prefix
            else key
        )

        if isinstance(value, dict):
            flattened.update(
                flatten_record(
                    value,
                    flattened_key,
                )
            )

        elif isinstance(value, list):
            flattened[flattened_key] = (
                json.dumps(
                    value,
                    ensure_ascii=False,
                )
            )

        else:
            flattened[flattened_key] = value

    return flattened


def create_csv_data(
    rows: list[dict],
) -> bytes:
    if not rows:
        return (
            "데이터가 없습니다.\n"
        ).encode("utf-8-sig")

    flattened_rows = [
        flatten_record(row)
        for row in rows
    ]

    fieldnames = sorted(
        {
            key
            for row in flattened_rows
            for key in row.keys()
        }
    )

    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(flattened_rows)

    return output.getvalue().encode(
        "utf-8-sig"
    )


refresh_button = st.button(
    "최신 데이터 불러오기",
    type="primary",
)

if (
    refresh_button
    or "export_data" not in st.session_state
):
    try:
        with st.spinner(
            "실험 데이터를 불러오는 중입니다..."
        ):
            network_data = load_api_data(
                "/network"
            )

            gossip_events = load_api_data(
                "/conversations/gossip-events"
            )

            cascade_data = load_api_data(
                "/network/cascades"
            )

        st.session_state["export_data"] = {
            "network": network_data,
            "gossip_events": gossip_events,
            "cascades": cascade_data,
        }

        st.success(
            "최신 데이터를 불러왔습니다."
        )

    except requests.RequestException as error:
        st.error(
            "FastAPI 서버에서 데이터를 "
            "불러올 수 없습니다."
        )

        st.exception(error)


export_data = st.session_state.get(
    "export_data"
)

if export_data is not None:
    network_data = export_data.get(
        "network",
        {},
    )

    gossip_events = export_data.get(
        "gossip_events",
        [],
    )

    cascade_data = export_data.get(
        "cascades",
        {},
    )

    agents = network_data.get(
        "nodes",
        [],
    )

    transmissions = network_data.get(
        "edges",
        [],
    )

    cascades = cascade_data.get(
        "cascades",
        [],
    )

    metric1, metric2, metric3, metric4 = (
        st.columns(4)
    )

    metric1.metric(
        "에이전트",
        len(agents),
    )

    metric2.metric(
        "정보 전달",
        len(transmissions),
    )

    metric3.metric(
        "가십 이벤트",
        len(gossip_events),
    )

    metric4.metric(
        "소문 전파 경로",
        len(cascades),
    )

    exported_at = datetime.now(
        timezone.utc
    ).isoformat()

    filename_timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_data = {
        "project": "EchoChamber",
        "exported_at": exported_at,
        "summary": {
            "agent_count": len(agents),
            "transmission_count": len(
                transmissions
            ),
            "gossip_event_count": len(
                gossip_events
            ),
            "cascade_count": len(cascades),
        },
        "agents": agents,
        "transmissions": transmissions,
        "gossip_events": gossip_events,
        "cascade_analysis": cascade_data,
    }

    report_json = json.dumps(
        report_data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    st.divider()
    st.subheader("데이터 내려받기")

    download_col1, download_col2 = (
        st.columns(2)
    )

    download_col3, download_col4 = (
        st.columns(2)
    )

    with download_col1:
        st.download_button(
            label="에이전트 CSV 다운로드",
            data=create_csv_data(
                agents
            ),
            file_name=(
                "echochamber_agents_"
                f"{filename_timestamp}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    with download_col2:
        st.download_button(
            label="정보 전달 CSV 다운로드",
            data=create_csv_data(
                transmissions
            ),
            file_name=(
                "echochamber_transmissions_"
                f"{filename_timestamp}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    with download_col3:
        st.download_button(
            label="가십 분석 CSV 다운로드",
            data=create_csv_data(
                gossip_events
            ),
            file_name=(
                "echochamber_gossip_"
                f"{filename_timestamp}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    with download_col4:
        st.download_button(
            label="전체 실험 JSON 다운로드",
            data=report_json,
            file_name=(
                "echochamber_report_"
                f"{filename_timestamp}.json"
            ),
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    st.subheader("데이터 미리보기")

    preview_tab1, preview_tab2, preview_tab3 = (
        st.tabs(
            [
                "에이전트",
                "정보 전달",
                "가십 이벤트",
            ]
        )
    )

    with preview_tab1:
        if agents:
            st.dataframe(
                agents,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "에이전트 데이터가 없습니다."
            )

    with preview_tab2:
        if transmissions:
            st.dataframe(
                transmissions,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "정보 전달 데이터가 없습니다."
            )

    with preview_tab3:
        if gossip_events:
            st.dataframe(
                [
                    flatten_record(event)
                    for event in gossip_events
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "가십 이벤트가 없습니다."
            )

    with st.expander(
        "전체 JSON 미리보기"
    ):
        st.json(report_data)