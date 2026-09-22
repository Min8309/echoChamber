import networkx as nx
import plotly.graph_objects as go
import requests
import streamlit as st
import pandas as pd


API_BASE_URL = "http://127.0.0.1:8000"

st.divider()
st.subheader("실제 댓글 분석")

uploaded_file = st.file_uploader(
    "익명화한 네이버 댓글 CSV 업로드",
    type=["csv"],
    key="naver_comments_csv",
)

if uploaded_file is not None:
    try:
        comment_df = pd.read_csv(
            uploaded_file,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        )
    except Exception as error:
        st.error(f"CSV를 읽을 수 없습니다: {error}")
        st.stop()

    required_columns = {
        "message_id",
        "thread_id",
        "author_id",
        "text",
    }

    missing_columns = required_columns - set(comment_df.columns)

    if missing_columns:
        st.error(
            "필수 열이 없습니다: "
            + ", ".join(sorted(missing_columns))
        )
        st.stop()

    if comment_df.empty:
        st.error("CSV에 댓글이 없습니다.")
        st.stop()

    if len(comment_df) > 10:
        st.error(
            "첫 시험에서는 댓글을 10개 이하로 줄여 주세요."
        )
        st.stop()

    if comment_df["message_id"].duplicated().any():
        st.error("CSV 안에 중복된 message_id가 있습니다.")
        st.stop()

    for column in required_columns:
        if comment_df[column].str.strip().eq("").any():
            st.error(f"{column}에 빈 값이 있습니다.")
            st.stop()

    st.dataframe(
        comment_df,
        use_container_width=True,
    )

    if st.button(
        "댓글 저장",
        key="save_real_comments",
    ):
        payload = {"messages": []}

        for _, row in comment_df.iterrows():
            message = {
                "message_id": row["message_id"].strip(),
                "thread_id": row["thread_id"].strip(),
                "source_type": "naver_comment",
                "author_id": row["author_id"].strip(),
                "text": row["text"].strip(),
            }

            if "reply_to_id" in comment_df.columns:
                reply_to_id = row["reply_to_id"].strip()

                if reply_to_id:
                    message["reply_to_id"] = reply_to_id

            if "created_at" in comment_df.columns:
                created_at = row["created_at"].strip()

                if created_at:
                    message["created_at"] = created_at

            payload["messages"].append(message)

        try:
            response = requests.post(
                f"{API_BASE_URL}/ingest/messages",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

        except requests.RequestException as error:
            st.error(f"댓글 저장 실패: {error}")

        else:
            saved = response.json()
            st.success(
                f"새 댓글 {saved['saved_count']}개 저장, "
                f"중복 {saved['duplicate_count']}개 건너뜀"
            )

st.caption(
    "아래 버튼은 이번 CSV뿐 아니라 서버에 저장된 "
    "모든 댓글을 다시 분석합니다. API 비용이 발생할 수 있습니다."
)

if st.button(
    "저장된 댓글 분석",
    key="analyze_real_comments",
):
    try:
        stored_response = requests.get(
            f"{API_BASE_URL}/ingest/messages",
            timeout=30,
        )
        stored_response.raise_for_status()

        stored_messages = stored_response.json()

        if not stored_messages:
            st.warning("저장된 댓글이 없습니다.")

        elif len(stored_messages) > 10:
            st.error(
                f"현재 저장된 댓글이 {len(stored_messages)}개입니다. "
                "첫 시험은 10개 이하에서 진행해 주세요."
            )

        else:
            with st.spinner(
                f"댓글 {len(stored_messages)}개 분석 중..."
            ):
                analysis_response = requests.post(
                    f"{API_BASE_URL}/analysis/messages",
                    timeout=300,
                )
                analysis_response.raise_for_status()

            st.session_state["real_comment_analysis"] = (
                analysis_response.json()
            )

    except requests.RequestException as error:
        st.error(f"댓글 분석 실패: {error}")

result = st.session_state.get("real_comment_analysis")

if result:
    st.write(
        f"분석 성공: {result['success_count']}건 · "
        f"실패: {result['failed_count']}건 · "
        f"가십 분류: {result['gossip_count']}건"
    )

    result_df = pd.json_normalize(
        result["results"],
        sep="_",
    )

    st.dataframe(
        result_df,
        use_container_width=True,
    )

    st.download_button(
        label="분석 결과 CSV 다운로드",
        data=result_df.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="echochamber_comment_analysis.csv",
        mime="text/csv",
        key="download_comment_analysis",
    )

def run_simulation(
    topic: str,
    steps: int,
):
    response = requests.post(
        f"{API_BASE_URL}/simulation/run",
        json={
            "topic": topic,
            "steps": steps,
        },
        timeout=300,
    )

    response.raise_for_status()

    return response.json()

def run_autonomous_simulation(
    steps: int,
):
    response = requests.post(
        (
            f"{API_BASE_URL}"
            "/simulation/autonomous-run"
        ),
        json={
            "steps": steps,
        },
        timeout=600,
    )

    response.raise_for_status()

    return response.json()

def load_cascade_data(
    min_transmissions: int = 1,
):
    response = requests.get(
        f"{API_BASE_URL}/network/cascades",
        params={
            "min_transmissions": (
                min_transmissions
            ),
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()

def load_cascade_distortion(
    cascade_id: str,
):
    response = requests.get(
        (
            f"{API_BASE_URL}"
            f"/network/cascades/{cascade_id}"
            "/distortion"
        ),
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


st.set_page_config(
    page_title="EchoChamber",
    page_icon="🌐",
    layout="wide",
)

st.title("EchoChamber")
st.subheader("가십 역학 시뮬레이션 및 분석 플랫폼")
with st.sidebar:
    st.header("시뮬레이션 제어")

    simulation_topic = st.text_area(
        "대화 주제",
        value=(
            "Isabella가 파티 준비를 제대로 "
            "하지 못한다는 소문"
        ),
        height=100,
    )
    st.divider()

    st.subheader("AI 자율 시뮬레이션")

    st.caption(
        "에이전트가 기억과 목표를 바탕으로 "
        "대상과 대화 주제를 스스로 결정합니다."
    )

    autonomous_steps = st.number_input(
        "자율 실행 단계 수",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
        key="autonomous_steps",
    )

    autonomous_button = st.button(
        "AI 자율 시뮬레이션 실행",
        type="primary",
        use_container_width=True,
        key="autonomous_run_button",
    )

    if autonomous_button:
        try:
            with st.spinner(
                "에이전트가 계획을 세우고 "
                "대화하는 중입니다..."
            ):
                autonomous_result = (
                    run_autonomous_simulation(
                        steps=int(
                            autonomous_steps
                        )
                    )
                )

            st.session_state[
                "last_autonomous_result"
            ] = autonomous_result

            st.success(
                "AI 자율 시뮬레이션이 "
                "완료되었습니다."
            )

        except requests.HTTPError as error:
            error_message = str(error)

            if error.response is not None:
                try:
                    error_data = (
                        error.response.json()
                    )

                    error_message = (
                        error_data.get(
                            "detail",
                            error_message,
                        )
                    )

                except ValueError:
                    pass

            st.error(
                f"자율 실행 실패: "
                f"{error_message}"
            )

        except requests.RequestException as error:
            st.error(
                "FastAPI 서버 연결 실패: "
                f"{error}"
            )
    autonomous_result = st.session_state.get(
        "last_autonomous_result"
    )

    if autonomous_result is not None:
        st.markdown(
            "#### 최근 자율 실행 결과"
        )

        auto_col1, auto_col2 = st.columns(2)

        auto_col1.metric(
            "완료 단계",
            autonomous_result.get(
                "completed_steps",
                0,
            ),
        )

        auto_col2.metric(
            "가십 발생",
            autonomous_result.get(
                "gossip_count",
                0,
            ),
        )

        auto_col3, auto_col4 = st.columns(2)

        auto_col3.metric(
            "반추 발생",
            autonomous_result.get(
                "reflection_count",
                0,
            ),
        )

        auto_col4.metric(
            "실패 단계",
            autonomous_result.get(
                "failed_steps",
                0,
            ),
        )

        with st.expander(
            "자율 행동 기록 보기"
        ):
            for step_number, result in enumerate(
                autonomous_result.get(
                    "results",
                    [],
                ),
                start=1,
            ):
                speaker = result.get(
                    "selected_speaker",
                    {},
                )

                listener = result.get(
                    "selected_listener",
                    {},
                )

                planning = result.get(
                    "planning",
                    {},
                )

                plan = planning.get(
                    "plan",
                    {},
                )

                conversation = result.get(
                    "conversation",
                    {},
                )

                analysis = conversation.get(
                    "analysis",
                    {},
                )

                reflection = result.get(
                    "reflection",
                    {},
                )

                st.markdown(
                    f"**{step_number}단계 — "
                    f"{speaker.get('name', '?')} → "
                    f"{listener.get('name', '?')}**"
                )

                st.write(
                    f"계획 행동: "
                    f"{plan.get('action', '')}"
                )

                st.write(
                    f"계획 주제: "
                    f"{plan.get('topic', '')}"
                )

                st.write(
                    f"계획 이유: "
                    f"{plan.get('reason', '')}"
                )

                st.info(
                    conversation.get(
                        "utterance",
                        "",
                    )
                )

                st.write(
                    "가십 여부:",
                    analysis.get(
                        "is_gossip",
                        False,
                    ),
                )

                st.write(
                    "반추 발생:",
                    reflection.get(
                        "triggered",
                        False,
                    ),
                )

                st.divider()

    simulation_steps = st.number_input(
        "실행 단계 수",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
    )

    run_button = st.button(
        "시뮬레이션 실행",
        type="primary",
        use_container_width=True,
    )

    if run_button:
        if not simulation_topic.strip():
            st.warning(
                "대화 주제를 입력하세요."
            )

        else:
            try:
                with st.spinner(
                    f"{simulation_steps}단계 "
                    "시뮬레이션 실행 중..."
                ):
                    simulation_result = run_simulation(
                        topic=simulation_topic.strip(),
                        steps=int(simulation_steps),
                    )

                st.session_state[
                    "last_simulation_result"
                ] = simulation_result

                st.success(
                    "시뮬레이션이 완료되었습니다."
                )

            except requests.HTTPError as error:
                error_message = str(error)

                if error.response is not None:
                    try:
                        error_data = (
                            error.response.json()
                        )

                        error_message = error_data.get(
                            "detail",
                            error_message,
                        )

                    except ValueError:
                        pass

                st.error(
                    f"시뮬레이션 실패: "
                    f"{error_message}"
                )

            except requests.RequestException as error:
                st.error(
                    "FastAPI 서버에 연결할 수 "
                    f"없습니다: {error}"
                )

    if run_button:
        if not simulation_topic.strip():
            st.warning(
                "대화 주제를 입력하세요."
            )

        else:
            try:
                with st.spinner(
                    f"{simulation_steps}단계를 "
                    "연속 실행하고 있습니다..."
                ):
                    response = requests.post(
                        (
                            f"{API_BASE_URL}"
                            "/simulation/run"
                        ),
                        json={
                            "topic": simulation_topic,
                            "steps": simulation_steps,
                        },
                        timeout=600,
                    )

                    response.raise_for_status()

                    st.session_state[
                        "last_batch_simulation"
                    ] = response.json()

                st.success(
                    "연속 시뮬레이션이 완료됐습니다."
                )

            except requests.RequestException as error:
                st.error(
                    "연속 시뮬레이션 실행에 "
                    "실패했습니다."
                )
                st.exception(error)

    if "last_simulation" in st.session_state:
        latest = st.session_state[
            "last_simulation"
        ]

        speaker = latest[
            "selected_speaker"
        ]["name"]

        listener = latest[
            "selected_listener"
        ]["name"]

        conversation = latest["conversation"]
        analysis = conversation["analysis"]

        st.divider()
        st.subheader("최근 1단계 결과")

        st.write(
            f"**화자:** {speaker}"
        )
        st.write(
            f"**청자:** {listener}"
        )
        st.write(
            conversation["utterance"]
        )
        st.write(
            f"**가십 여부:** "
            f"{analysis['is_gossip']}"
        )
        st.write(
            f"**대상:** "
            f"{analysis.get('subject')}"
        )
        st.write(
            f"**평판 영향:** "
            f"{analysis['reputation_impact']:+.2f}"
        )

    if (
        "last_batch_simulation"
        in st.session_state
    ):
        batch = st.session_state[
            "last_batch_simulation"
        ]

        st.divider()
        st.subheader("최근 연속 실행 결과")

        summary_col1, summary_col2 = (
            st.columns(2)
        )

        summary_col1.metric(
            "완료 단계",
            batch["completed_steps"],
        )

        summary_col2.metric(
            "가십 발생",
            batch["gossip_count"],
        )

        with st.expander(
            "단계별 대화 보기",
            expanded=False,
        ):
            for item in batch["results"]:
                conversation = item[
                    "conversation"
                ]

                analysis = conversation[
                    "analysis"
                ]

                speaker = item[
                    "selected_speaker"
                ]["name"]

                listener = item[
                    "selected_listener"
                ]["name"]

                st.markdown(
                    f"### {item['step']}단계"
                )

                st.write(
                    f"**{speaker} → "
                    f"{listener}**"
                )

                st.write(
                    conversation["utterance"]
                )

                st.caption(
                    f"대상: "
                    f"{analysis.get('subject')} · "
                    f"감정: "
                    f"{analysis['sentiment']} · "
                    f"확실성: "
                    f"{analysis['certainty']} · "
                    f"평판 영향: "
                    f"{analysis['reputation_impact']:+.2f}"
                )

                st.divider()


def load_network_data():
    response = requests.get(
        f"{API_BASE_URL}/network",
        timeout=5,
    )
    response.raise_for_status()

    return response.json()
def run_simulation(
    topic: str,
    steps: int,
):
    response = requests.post(
        f"{API_BASE_URL}/simulation/run",
        json={
            "topic": topic,
            "steps": steps,
        },
        timeout=300,
    )

    response.raise_for_status()

    return response.json()


def load_gossip_events():
    response = requests.get(
        f"{API_BASE_URL}/conversations/gossip-events",
        timeout=5,
    )
    response.raise_for_status()

    return response.json()


def create_network_figure(network_data):

    graph = nx.DiGraph()

    nodes = network_data["nodes"]
    edges = network_data["edges"]

    for node in nodes:
        graph.add_node(
            node["id"],
            label=node["label"],
        )

    for edge in edges:
        graph.add_edge(
            edge["source"],
            edge["target"],
        )

    positions = nx.spring_layout(
        graph,
        seed=42,
        k=1.2,
    )

    normal_edge_x = []
    normal_edge_y = []

    gossip_edge_x = []
    gossip_edge_y = []

    for edge in edges:
        source = edge["source"]
        target = edge["target"]

        if (
            source not in positions
            or target not in positions
        ):
            continue

        source_x, source_y = positions[source]
        target_x, target_y = positions[target]

        if edge.get("is_gossip", False):
            gossip_edge_x.extend(
                [source_x, target_x, None]
            )
            gossip_edge_y.extend(
                [source_y, target_y, None]
            )

        else:
            normal_edge_x.extend(
                [source_x, target_x, None]
            )
            normal_edge_y.extend(
                [source_y, target_y, None]
            )

    normal_edge_trace = go.Scatter(
        x=normal_edge_x,
        y=normal_edge_y,
        mode="lines",
        name="일반 정보",
        line={
            "width": 2,
            "color": "#8B9DC3",
        },
        hoverinfo="none",
    )

    gossip_edge_trace = go.Scatter(
        x=gossip_edge_x,
        y=gossip_edge_y,
        mode="lines",
        name="가십 전달",
        line={
            "width": 4,
            "color": "#E45756",
        },
        hoverinfo="none",
    )

    node_x = []
    node_y = []
    node_text = []
    node_hover_text = []
    node_colors = []
    node_sizes = []

    for node in nodes:
        x, y = positions[node["id"]]

        reputation_score = node.get(
            "reputation_score",
            0.0,
        )

        sent_gossip_count = node.get(
            "sent_gossip_count",
            0,
        )

        received_gossip_count = node.get(
            "received_gossip_count",
            0,
        )

        mentioned_count = node.get(
            "mentioned_count",
            0,
        )

        total_gossip_activity = (
            sent_gossip_count
            + received_gossip_count
        )

        node_x.append(x)
        node_y.append(y)
        node_text.append(node["label"])
        node_colors.append(reputation_score)

        node_sizes.append(
            35 + total_gossip_activity * 8
        )

        node_hover_text.append(
            f"이름: {node['label']}<br>"
            f"직업: {node['occupation']}<br>"
            f"현재 위치: {node['location']}<br>"
            f"가십 성향: "
            f"{node['gossip_tendency']}<br>"
            f"가십 발신: "
            f"{sent_gossip_count}건<br>"
            f"가십 수신: "
            f"{received_gossip_count}건<br>"
            f"언급 횟수: "
            f"{mentioned_count}건<br>"
            f"평판 점수: "
            f"{reputation_score:+.2f}"
        )

    maximum_reputation = max(
        [
            abs(score)
            for score in node_colors
        ],
        default=1.0,
    )

    color_limit = max(
        1.0,
        maximum_reputation,
    )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="bottom center",
        hovertext=node_hover_text,
        hoverinfo="text",
        name="에이전트",
        marker={
            "size": node_sizes,
            "color": node_colors,
            "colorscale": "RdYlGn",
            "showscale": True,
            "cmin": -color_limit,
            "cmax": color_limit,
            "cmid": 0,
            "colorbar": {
                "title": "평판 점수",
            },
            "line": {
                "width": 2,
                "color": "#FFFFFF",
            },
        },
    )

    figure = go.Figure(
        data=[
            normal_edge_trace,
            gossip_edge_trace,
            node_trace,
        ]
    )

    figure.update_layout(
        title="소문 전파 및 평판 네트워크",
        showlegend=True,
        hovermode="closest",
        height=650,
        margin={
            "t": 60,
            "b": 20,
            "l": 20,
            "r": 20,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
    )

    return figure

def create_cascade_figure(
    cascade: dict,
):
    graph = nx.DiGraph()

    root_memory = cascade.get(
        "root_memory",
        {},
    )

    root_agent_id = root_memory.get(
        "agent_id"
    )

    root_agent_name = root_memory.get(
        "agent_name",
        "Unknown",
    )

    if root_agent_id:
        graph.add_node(
            root_agent_id,
            label=root_agent_name,
        )

    transmissions = cascade.get(
        "transmissions",
        [],
    )

    received_counts = {}

    for transmission in transmissions:
        source = transmission.get(
            "source",
            {},
        )

        target = transmission.get(
            "target",
            {},
        )

        source_id = source.get("agent_id")
        target_id = target.get("agent_id")

        if not source_id or not target_id:
            continue

        graph.add_node(
            source_id,
            label=source.get(
                "name",
                "Unknown",
            ),
        )

        graph.add_node(
            target_id,
            label=target.get(
                "name",
                "Unknown",
            ),
        )

        graph.add_edge(
            source_id,
            target_id,
            confidence=transmission.get(
                "confidence",
                0,
            ),
            depth=transmission.get(
                "depth",
                0,
            ),
            description=transmission.get(
                "description",
                "",
            ),
        )

        received_counts[target_id] = (
            received_counts.get(
                target_id,
                0,
            )
            + 1
        )

    figure = go.Figure()

    if not graph.nodes:
        figure.update_layout(
            title="표시할 전파 경로가 없습니다.",
            height=500,
        )

        return figure

    positions = nx.spring_layout(
        graph,
        seed=42,
        k=1.5,
    )

    # 전달선
    for source_id, target_id, edge_data in (
        graph.edges(data=True)
    ):
        source_x, source_y = positions[
            source_id
        ]

        target_x, target_y = positions[
            target_id
        ]

        confidence = edge_data.get(
            "confidence",
            0,
        )

        depth = edge_data.get(
            "depth",
            0,
        )

        figure.add_trace(
            go.Scatter(
                x=[
                    source_x,
                    target_x,
                ],
                y=[
                    source_y,
                    target_y,
                ],
                mode="lines",
                line={
                    "width": (
                        2
                        + confidence * 4
                    ),
                    "color": "#EF4444",
                },
                hovertext=(
                    f"전파 깊이: {depth}<br>"
                    f"신뢰도: {confidence}<br>"
                    f"{edge_data.get('description', '')}"
                ),
                hoverinfo="text",
                showlegend=False,
            )
        )

        # 방향 화살표
        figure.add_annotation(
            x=target_x,
            y=target_y,
            ax=source_x,
            ay=source_y,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.2,
            arrowwidth=1.5,
            arrowcolor="#EF4444",
            opacity=0.7,
        )

    node_x = []
    node_y = []
    node_names = []
    node_hover = []
    node_colors = []
    node_sizes = []

    for node_id, node_data in (
        graph.nodes(data=True)
    ):
        x, y = positions[node_id]

        node_name = node_data.get(
            "label",
            "Unknown",
        )

        received = received_counts.get(
            node_id,
            0,
        )

        node_x.append(x)
        node_y.append(y)
        node_names.append(node_name)

        node_hover.append(
            f"이름: {node_name}<br>"
            f"받은 횟수: {received}"
        )

        if node_id == root_agent_id:
            node_colors.append(
                "#7F1D1D"
            )
        else:
            node_colors.append(
                "#60A5FA"
            )

        node_sizes.append(
            35 + received * 8
        )

    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_names,
            textposition="bottom center",
            hovertext=node_hover,
            hoverinfo="text",
            marker={
                "size": node_sizes,
                "color": node_colors,
                "line": {
                    "width": 2,
                    "color": "#FFFFFF",
                },
            },
            showlegend=False,
        )
    )

    figure.update_layout(
        title="선택한 소문의 전파 경로",
        height=550,
        hovermode="closest",
        margin={
            "t": 60,
            "b": 20,
            "l": 20,
            "r": 20,
        },
        xaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
    )

    return figure
def create_distortion_figure(
    distortion_data: dict,
):
    steps = distortion_data.get(
        "steps",
        [],
    )

    figure = go.Figure()

    if not steps:
        figure.update_layout(
            title="왜곡 분석 데이터가 없습니다.",
            height=450,
        )

        return figure

    orders = [
        step["order"]
        for step in steps
    ]

    root_distortions = [
        step["distortion_from_root"]
        for step in steps
    ]

    parent_distortions = [
        step["distortion_from_parent"]
        for step in steps
    ]

    confidences = [
        step["confidence"]
        for step in steps
    ]

    figure.add_trace(
        go.Scatter(
            x=orders,
            y=root_distortions,
            mode="lines+markers",
            name="최초 기억 대비 왜곡도",
            line={
                "width": 3,
                "color": "#DC2626",
            },
            marker={
                "size": 8,
            },
            hovertemplate=(
                "%{x}번째 전달<br>"
                "원문 대비 왜곡도: "
                "%{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=orders,
            y=parent_distortions,
            mode="lines+markers",
            name="직전 기억 대비 왜곡도",
            line={
                "width": 2,
                "color": "#F59E0B",
                "dash": "dot",
            },
            marker={
                "size": 6,
            },
            hovertemplate=(
                "%{x}번째 전달<br>"
                "직전 기억 대비 왜곡도: "
                "%{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=orders,
            y=confidences,
            mode="lines+markers",
            name="정보 신뢰도",
            line={
                "width": 3,
                "color": "#2563EB",
            },
            marker={
                "size": 8,
            },
            hovertemplate=(
                "%{x}번째 전달<br>"
                "신뢰도: %{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title="전달 단계별 왜곡도와 신뢰도 변화",
        height=480,
        hovermode="x unified",
        margin={
            "t": 60,
            "b": 50,
            "l": 50,
            "r": 20,
        },
        xaxis={
            "title": "정보 전달 순서",
            "dtick": 1,
        },
        yaxis={
            "title": "점수",
            "range": [
                0,
                1.05,
            ],
            "tickformat": ".0%",
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
    )

    return figure

def create_sentiment_figure(gossip_events):
    sentiment_counts = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }

    for event in gossip_events:
        sentiment = event["analysis"]["sentiment"]

        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1

    labels = [
        "긍정",
        "중립",
        "부정",
    ]

    values = [
        sentiment_counts["positive"],
        sentiment_counts["neutral"],
        sentiment_counts["negative"],
    ]

    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker={
                    "colors": [
                        "#2E8B57",
                        "#A0A0A0",
                        "#DC143C",
                    ]
                },
            )
        ]
    )

    figure.update_layout(
        title="가십 감정 분포",
        height=400,
        margin={
            "t": 60,
            "b": 20,
            "l": 20,
            "r": 20,
        },
    )

    return figure


def create_certainty_figure(gossip_events):
    certainty_counts = {
        "confirmed": 0,
        "hearsay": 0,
        "speculation": 0,
    }

    for event in gossip_events:
        certainty = event["analysis"]["certainty"]

        if certainty in certainty_counts:
            certainty_counts[certainty] += 1

    figure = go.Figure(
        data=[
            go.Bar(
                x=[
                    "확인된 정보",
                    "전해 들은 정보",
                    "추측",
                ],
                y=[
                    certainty_counts["confirmed"],
                    certainty_counts["hearsay"],
                    certainty_counts["speculation"],
                ],
                marker={
                    "color": [
                        "#2E8B57",
                        "#F0A202",
                        "#D95D39",
                    ]
                },
            )
        ]
    )

    figure.update_layout(
        title="정보 확실성 분포",
        height=400,
        yaxis={
            "title": "건수",
            "rangemode": "tozero",
        },
        margin={
            "t": 60,
            "b": 20,
            "l": 40,
            "r": 20,
        },
    )

    return figure


def create_reputation_figure(gossip_events):
    reputation_scores = {}

    for event in gossip_events:
        analysis = event["analysis"]

        subject = (
            analysis.get("subject")
            or "대상 미상"
        )

        reputation_scores[subject] = (
            reputation_scores.get(subject, 0.0)
            + analysis["reputation_impact"]
        )

    subjects = list(reputation_scores.keys())
    scores = [
        reputation_scores[subject]
        for subject in subjects
    ]

    colors = []

    for score in scores:
        if score > 0:
            colors.append("#2E8B57")
        elif score < 0:
            colors.append("#DC143C")
        else:
            colors.append("#A0A0A0")

    figure = go.Figure(
        data=[
            go.Bar(
                x=subjects,
                y=scores,
                marker={
                    "color": colors,
                },
                text=[
                    f"{score:.2f}"
                    for score in scores
                ],
                textposition="auto",
            )
        ]
    )

    figure.update_layout(
        title="인물별 누적 평판 영향",
        height=400,
        yaxis={
            "title": "누적 평판 영향",
            "zeroline": True,
            "zerolinecolor": "#333333",
        },
        margin={
            "t": 60,
            "b": 30,
            "l": 50,
            "r": 20,
        },
    )

    return figure


def create_gossip_rows(
    gossip_events,
    agent_names,
):
    rows = []

    for event in reversed(gossip_events):
        analysis = event["analysis"]

        rows.append(
            {
                "생성 시각": event["created_at"],
                "화자": agent_names.get(
                    event["speaker_id"],
                    event["speaker_id"],
                ),
                "청자": agent_names.get(
                    event["listener_id"],
                    event["listener_id"],
                ),
                "대상": analysis.get("subject"),
                "주제": event["topic"],
                "발화": event["utterance"],
                "감정": analysis["sentiment"],
                "확실성": analysis["certainty"],
                "분석 신뢰도": analysis["confidence"],
                "평판 영향": analysis[
                    "reputation_impact"
                ],
            }
        )

    return rows


try:
    network_data = load_network_data()

except requests.RequestException as error:
    st.error(
        "FastAPI 서버에 연결할 수 없습니다. "
        "8000번 포트에서 서버가 실행 중인지 확인하세요."
    )

    st.code(
        "python -m uvicorn app.main:app --reload"
    )

    st.exception(error)
    st.stop()


try:
    gossip_events = load_gossip_events()

except requests.RequestException:
    gossip_events = []

    st.warning(
        "가십 이벤트 API를 불러오지 못했습니다. "
        "FastAPI 서버를 다시 확인하세요."
    )


# 네트워크 요약 지표
col1, col2, col3 = st.columns(3)

col1.metric(
    "전체 에이전트",
    network_data["node_count"],
)

col2.metric(
    "정보 전달 횟수",
    network_data["edge_count"],
)

average_confidence = 0.0

if network_data["edges"]:
    average_confidence = sum(
        edge["confidence"]
        for edge in network_data["edges"]
    ) / len(network_data["edges"])

col3.metric(
    "평균 정보 신뢰도",
    f"{average_confidence:.2f}",
)


# 네트워크 시각화
if not network_data["nodes"]:
    st.warning(
        "등록된 에이전트가 없습니다."
    )

else:
    figure = create_network_figure(
        network_data
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )
     


# AI 가십 분석 지표
st.divider()
st.subheader("AI 가십 분석")

gossip_count = len(gossip_events)

negative_count = sum(
    1
    for event in gossip_events
    if event["analysis"]["sentiment"] == "negative"
)

average_analysis_confidence = 0.0
average_reputation_impact = 0.0

if gossip_events:
    average_analysis_confidence = sum(
        event["analysis"]["confidence"]
        for event in gossip_events
    ) / gossip_count

    average_reputation_impact = sum(
        event["analysis"]["reputation_impact"]
        for event in gossip_events
    ) / gossip_count

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "저장된 가십",
    gossip_count,
)

metric2.metric(
    "부정적 가십",
    negative_count,
)

metric3.metric(
    "평균 분석 신뢰도",
    f"{average_analysis_confidence:.2f}",
)

metric4.metric(
    "평균 평판 영향",
    f"{average_reputation_impact:+.2f}",
)


if gossip_events:
    chart1, chart2 = st.columns(2)

    with chart1:
        st.plotly_chart(
            create_sentiment_figure(
                gossip_events
            ),
            use_container_width=True,
        )

    with chart2:
        st.plotly_chart(
            create_certainty_figure(
                gossip_events
            ),
            use_container_width=True,
        )

    st.plotly_chart(
        create_reputation_figure(
            gossip_events
        ),
        use_container_width=True,
    )

else:
    st.info(
        "아직 저장된 가십 이벤트가 없습니다."
    )


# 에이전트 및 전달 기록
st.divider()
st.subheader("에이전트 목록")

st.dataframe(
    
    network_data["nodes"],
    use_container_width=True,
)

st.subheader("정보 전달 기록")

if network_data["edges"]:
    st.dataframe(
        network_data["edges"],
        use_container_width=True,
    )

else:
    st.info(
        "아직 에이전트 사이의 정보 전달 기록이 없습니다."
    )


# 최근 가십 이벤트
st.subheader("최근 가십 이벤트")

agent_names = {
    node["id"]: node["label"]
    for node in network_data["nodes"]
}

gossip_rows = create_gossip_rows(
    gossip_events,
    agent_names,
)

if gossip_rows:
    st.dataframe(
        gossip_rows,
        use_container_width=True,
    )

else:
    st.info(
        "표시할 가십 이벤트가 없습니다."
    )

st.subheader("최근 시뮬레이션 결과")

last_result = st.session_state.get(
    "last_simulation_result"
)

if last_result is None:
    st.info(
        "아직 대시보드에서 실행한 "
        "시뮬레이션이 없습니다."
    )

else:
    result_col1, result_col2, result_col3 = (
        st.columns(3)
    )

    result_col1.metric(
        "요청 단계",
        last_result.get(
            "requested_steps",
            0,
        ),
    )

    result_col2.metric(
        "완료 단계",
        last_result.get(
            "completed_steps",
            0,
        ),
    )

    result_col3.metric(
        "가십 발생 수",
        last_result.get(
            "gossip_count",
            0,
        ),
    )

    result_rows = []

    for step_number, step_result in enumerate(
        last_result.get("results", []),
        start=1,
    ):
        conversation = step_result.get(
            "conversation",
            {},
        )

        analysis = conversation.get(
            "analysis",
            {},
        )

        reflection = step_result.get(
            "reflection",
            {},
        )

        speaker = step_result.get(
            "selected_speaker",
            {},
        )

        listener = step_result.get(
            "selected_listener",
            {},
        )

        result_rows.append(
            {
                "단계": step_number,
                "발화자": speaker.get(
                    "name",
                    "Unknown",
                ),
                "청자": listener.get(
                    "name",
                    "Unknown",
                ),
                "발화": conversation.get(
                    "utterance",
                    "",
                ),
                "가십": analysis.get(
                    "is_gossip",
                    False,
                ),
                "대상": analysis.get(
                    "subject",
                    "",
                ),
                "감정": analysis.get(
                    "sentiment",
                    "",
                ),
                "평판 영향": analysis.get(
                    "reputation_impact",
                    0,
                ),
                "반추 발생": reflection.get(
                    "triggered",
                    False,
                ),
            }
        )

    if result_rows:
        st.dataframe(
            result_rows,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        "전체 JSON 결과 확인"
    ):
        st.json(last_result)
        st.divider()
st.subheader("소문 전파 경로 분석")

try:
    cascade_data = load_cascade_data(
        min_transmissions=1
    )

except requests.RequestException as error:
    st.warning(
        "소문 전파 경로 데이터를 "
        "불러올 수 없습니다."
    )

    st.caption(str(error))

else:
    cascades = cascade_data.get(
        "cascades",
        [],
    )

    cascade_col1, cascade_col2 = (
        st.columns(2)
    )

    cascade_col1.metric(
        "추적된 소문",
        cascade_data.get(
            "cascade_count",
            0,
        ),
    )

    cascade_col2.metric(
        "전체 대화 기억",
        cascade_data.get(
            "dialogue_memory_count",
            0,
        ),
    )

    if not cascades:
        st.info(
            "추적할 수 있는 소문 전파 "
            "기록이 없습니다."
        )

    else:
        cascade_options = {}

        for index, cascade in enumerate(
            cascades,
            start=1,
        ):
            root_memory = cascade.get(
                "root_memory",
                {},
            )

            description = root_memory.get(
                "description",
                "내용 없음",
            )

            if len(description) > 50:
                description = (
                    description[:50]
                    + "..."
                )

            label = (
                f"{index}. {description} "
                f"({cascade.get('transmission_count', 0)}회)"
            )

            cascade_options[label] = (
                cascade
            )

        selected_label = st.selectbox(
            "분석할 소문 선택",
            options=list(
                cascade_options.keys()
            ),
        )

        selected_cascade = (
            cascade_options[
                selected_label
            ]
        )

        root_memory = (
            selected_cascade.get(
                "root_memory",
                {},
            )
        )

        st.markdown("#### 최초 기억")

        st.info(
            root_memory.get(
                "description",
                "",
            )
        )

        st.caption(
            f"최초 보유자: "
            f"{root_memory.get('agent_name', 'Unknown')} "
            f"| 기억 유형: "
            f"{root_memory.get('memory_type', '')}"
        )

        metric1, metric2, metric3, metric4 = (
            st.columns(4)
        )

        metric1.metric(
            "전달 횟수",
            selected_cascade.get(
                "transmission_count",
                0,
            ),
        )

        metric2.metric(
            "참여자 수",
            selected_cascade.get(
                "participant_count",
                0,
            ),
        )

        metric3.metric(
            "최대 전파 깊이",
            selected_cascade.get(
                "max_depth",
                0,
            ),
        )

        average_cascade_confidence = (
            selected_cascade.get(
            "average_confidence",
             0.0,
            )
        )

        metric4.metric(
            "평균 신뢰도",
            f"{average_cascade_confidence:.2f}",
       )

        cascade_figure = (
            create_cascade_figure(
                selected_cascade
            )
        )

        st.plotly_chart(
            cascade_figure,
            use_container_width=True,
        )
        st.markdown(
            "#### 소문 왜곡 및 신뢰도 분석"
        )

        try:
            distortion_data = (
                load_cascade_distortion(
                    selected_cascade[
                        "cascade_id"
                    ]
                )
            )

        except requests.RequestException as error:
            st.warning(
                "왜곡 분석 데이터를 "
                "불러올 수 없습니다."
            )

            st.caption(str(error))

        else:
            distortion_summary = (
                distortion_data.get(
                    "summary",
                    {},
                )
            )

            average_distortion = float(
                distortion_summary.get(
                    "average_distortion",
                    0.0,
                )
            )

            maximum_distortion = float(
                distortion_summary.get(
                    "maximum_distortion",
                    0.0,
                )
            )

            final_distortion = float(
                distortion_summary.get(
                    "final_distortion",
                    0.0,
                )
            )

            confidence_loss = float(
                distortion_summary.get(
                    "total_confidence_loss",
                    0.0,
                )
            )

            distortion_col1, distortion_col2 = (
                st.columns(2)
            )

            distortion_col3, distortion_col4 = (
                st.columns(2)
            )

            distortion_col1.metric(
                "평균 왜곡도",
                f"{average_distortion:.1%}",
            )

            distortion_col2.metric(
                "최대 왜곡도",
                f"{maximum_distortion:.1%}",
            )

            distortion_col3.metric(
                "최종 왜곡도",
                f"{final_distortion:.1%}",
            )

            distortion_col4.metric(
                "총 신뢰도 감소",
                f"{confidence_loss:.2f}",
            )

            distortion_figure = (
                create_distortion_figure(
                    distortion_data
                )
            )

            st.plotly_chart(
                distortion_figure,
                use_container_width=True,
            )

            st.markdown(
                "##### 단계별 왜곡 상세"
            )

            distortion_rows = []

            for step in distortion_data.get(
                "steps",
                [],
            ):
                source = step.get(
                    "source",
                    {},
                )

                target = step.get(
                    "target",
                    {},
                )

                distortion_rows.append(
                    {
                        "순서": step.get(
                            "order",
                            0,
                        ),
                        "깊이": step.get(
                            "depth",
                            0,
                        ),
                        "전달자": source.get(
                            "name",
                            "Unknown",
                        ),
                        "수신자": target.get(
                            "name",
                            "Unknown",
                        ),
                        "원문 유사도": (
                            step.get(
                                "similarity_from_root",
                                0,
                            )
                        ),
                        "원문 대비 왜곡도": (
                            step.get(
                                "distortion_from_root",
                                0,
                            )
                        ),
                        "직전 대비 왜곡도": (
                            step.get(
                                "distortion_from_parent",
                                0,
                            )
                        ),
                        "신뢰도": step.get(
                            "confidence",
                            0,
                        ),
                        "원문 대비 신뢰도 손실": (
                            step.get(
                                "confidence_loss_from_root",
                                0,
                            )
                        ),
                    }
                )

            st.dataframe(
                distortion_rows,
                use_container_width=True,
                hide_index=True,
            )

            most_distorted_order = (
                distortion_summary.get(
                    "most_distorted_order"
                )
            )

            if most_distorted_order is not None:
                st.warning(
                    f"가장 큰 왜곡은 "
                    f"{most_distorted_order}번째 "
                    "정보 전달에서 발생했습니다."
                )

        st.markdown("#### 전달 타임라인")

        timeline_rows = []

        for order, transmission in enumerate(
            selected_cascade.get(
                "transmissions",
                [],
            ),
            start=1,
        ):
            source = transmission.get(
                "source",
                {},
            )

            target = transmission.get(
                "target",
                {},
            )

            timeline_rows.append(
                {
                    "순서": order,
                    "깊이": transmission.get(
                        "depth",
                        0,
                    ),
                    "전달자": source.get(
                        "name",
                        "Unknown",
                    ),
                    "수신자": target.get(
                        "name",
                        "Unknown",
                    ),
                    "신뢰도": (
                        transmission.get(
                            "confidence",
                            0,
                        )
                    ),
                    "내용": (
                        transmission.get(
                            "description",
                            "",
                        )
                    ),
                    "시간": (
                        transmission.get(
                            "created_at",
                            "",
                        )
                    ),
                }
            )

        st.dataframe(
            timeline_rows,
            use_container_width=True,
            hide_index=True,
        )