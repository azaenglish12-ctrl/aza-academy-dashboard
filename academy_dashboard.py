import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json

# ========================
# 페이지 설정
# ========================
st.set_page_config(
    page_title="AZA 학원 통합 대시보드",
    page_icon="📚",
    layout="wide"
)

# ========================
# Google Sheets 연결 (보안)
# ========================
@st.cache_resource
def get_google_client():
    """Google Sheets 인증 (Secrets 또는 credentials.json)"""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 방법 1: Streamlit Secrets 사용 (배포용)
        try:
            credentials_dict = dict(st.secrets["gcp_service_account"])
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=scopes
            )
            st.sidebar.success("✅ Streamlit Secrets 인증")
            return gspread.authorize(credentials)
        except:
            pass
        
        # 방법 2: credentials.json 파일 사용 (로컬 테스트용)
        import os
        if os.path.exists('credentials.json'):
            credentials = Credentials.from_service_account_file(
                'credentials.json',
                scopes=scopes
            )
            st.sidebar.success("✅ credentials.json 인증")
            return gspread.authorize(credentials)
        
        # 둘 다 없으면 오류
        st.error("❌ 인증 정보를 찾을 수 없습니다!")
        st.info("""
        **로컬 테스트:** credentials.json 파일을 이 폴더에 복사하세요.
        
        **배포:** Streamlit Cloud에서 Secrets 설정이 필요합니다.
        """)
        return None
        
    except Exception as e:
        st.error(f"Google Sheets 연결 실패: {str(e)}")
        return None

@st.cache_data(ttl=600)  # 10분마다 갱신
def load_sheet_data(_client, sheet_id):
    """Google Sheets에서 4개 탭 데이터 로드"""
    try:
        spreadsheet = _client.open_by_key(sheet_id)
        
        # 4개 탭 로드
        학생명단 = pd.DataFrame(spreadsheet.worksheet("학생명단").get_all_records())
        반정보 = pd.DataFrame(spreadsheet.worksheet("반정보").get_all_records())
        그룹진도표 = pd.DataFrame(spreadsheet.worksheet("그룹진도표").get_all_records())
        개별진도표 = pd.DataFrame(spreadsheet.worksheet("개별진도표").get_all_records())
        
        return 학생명단, 반정보, 그룹진도표, 개별진도표
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return None, None, None, None

# ========================
# 시간표 템플릿
# ========================
월금_시간표 = {
    "3:30-4:20": {
        "대강의실(원장)": {"반": "초등", "내용": "문법/듣기 수업"},
        "유리방(예은T)": {"반": "-", "내용": ""},
        "나무방(채민T)": {"반": "-", "내용": ""},
        "모고방(관리T)": {"반": "-", "내용": ""}
    },
    "4:30-5:20": {
        "대강의실(원장)": {"반": "-", "내용": ""},
        "유리방(예은T)": {"반": "-", "내용": ""},
        "나무방(채민T)": {"반": "초등", "내용": "리딩시험 10분\n문법시험"},
        "모고방(관리T)": {"반": "-", "내용": ""}
    },
    "5:30-5:50": {
        "대강의실(원장)": {"반": "중등, 수능", "내용": "어휘뜻 개별시험\n어휘문맥 개별시험"},
        "유리방(예은T)": {"반": "", "내용": ""},
        "나무방(채민T)": {"반": "초등", "내용": "독해/문법 오답"},
        "모고방(관리T)": {"반": "", "내용": ""}
    },
    "5:55-6:45": {
        "대강의실(원장)": {"반": "중등", "내용": "문법 수업"},
        "유리방(예은T)": {"반": "수능", "내용": "6:10 모고어휘\n6:20 문법시험"},
        "나무방(채민T)": {"반": "초등", "내용": "독해/문법 오답\n재시험\n마무리되면 6:30 하원"},
        "모고방(관리T)": {"반": "내신", "내용": "있으면 진행"}
    },
    "6:50-7:40": {
        "대강의실(원장)": {"반": "내신", "내용": "있으면 진행"},
        "유리방(예은T)": {"반": "수능", "내용": "모의고사 문제풀이"},
        "나무방(채민T)": {"반": "중등", "내용": "7:00 리딩시험"},
        "모고방(관리T)": {"반": "정시", "내용": "한줄해석"}
    },
    "7:45-8:35": {
        "대강의실(원장)": {"반": "수능", "내용": "문법 수업"},
        "유리방(예은T)": {"반": "내신", "내용": "있으면 진행"},
        "나무방(채민T)": {"반": "중등", "내용": "오답\n과제"},
        "모고방(관리T)": {"반": "정시", "내용": "한줄해석"}
    },
    "8:40-9:30": {
        "대강의실(원장)": {"반": "정시", "내용": "독해 수업"},
        "유리방(예은T)": {"반": "내신", "내용": "있으면 진행"},
        "나무방(채민T)": {"반": "중등", "내용": "문법시험"},
        "모고방(관리T)": {"반": "수능", "내용": "문법/독해 오답\n재시험"}
    }
}

화목_시간표 = {
    "3:30-4:20": {
        "대강의실(원장)": {"반": "초등", "내용": "문법/듣기 수업"},
        "유리방(민서T)": {"반": "-", "내용": ""},
        "나무방(승연T)": {"반": "-", "내용": ""},
        "모고방(관리T)": {"반": "-", "내용": ""}
    },
    "4:30-5:20": {
        "대강의실(원장)": {"반": "-", "내용": ""},
        "유리방(민서T)": {"반": "-", "내용": ""},
        "나무방(승연T)": {"반": "초등", "내용": "리딩시험 10분\n문법시험"},
        "모고방(관리T)": {"반": "-", "내용": ""}
    },
    "5:30-5:50": {
        "대강의실(원장)": {"반": "중등, 수능", "내용": "어휘뜻 개별시험\n어휘문맥 개별시험"},
        "유리방(민서T)": {"반": "", "내용": ""},
        "나무방(승연T)": {"반": "초등", "내용": "독해/문법 오답"},
        "모고방(관리T)": {"반": "", "내용": ""}
    },
    "5:55-6:45": {
        "대강의실(원장)": {"반": "중등", "내용": "문법 수업"},
        "유리방(민서T)": {"반": "수능", "내용": "6:10 모고(공통)어휘\n6:25 문법(이전범위개념)시험"},
        "나무방(승연T)": {"반": "초등", "내용": "독해/문법 오답\n재시험\n마무리되면 6:30 하원"},
        "모고방(관리T)": {"반": "내신", "내용": "있으면 진행"}
    },
    "6:50-7:40": {
        "대강의실(원장)": {"반": "내신", "내용": "있으면 진행"},
        "유리방(민서T)": {"반": "수능", "내용": "모의고사 문제풀이"},
        "나무방(승연T)": {"반": "중등", "내용": "7:00 리딩시험\n오답"},
        "모고방(관리T)": {"반": "", "내용": ""}
    },
    "7:45-8:35": {
        "대강의실(원장)": {"반": "수능", "내용": "문법 수업"},
        "유리방(민서T)": {"반": "내신", "내용": "있으면 진행"},
        "나무방(승연T)": {"반": "중등", "내용": "독해/문법 오답\n개별 과제 진행"},
        "모고방(관리T)": {"반": "", "내용": ""}
    },
    "8:40-9:30": {
        "대강의실(원장)": {"반": "수능", "내용": "독해 수업(모고)"},
        "유리방(민서T)": {"반": "내신", "내용": "있으면 진행"},
        "나무방(승연T)": {"반": "중등", "내용": "이전 개념 문법시험\n오답 진행"},
        "모고방(관리T)": {"반": "", "내용": ""}
    }
}

# ========================
# 진도 데이터 가져오기
# ========================
def get_class_progress(date_str, class_name, 그룹진도표, 반정보):
    """특정 날짜, 특정 반의 그룹 진도 가져오기 (진도 + 과제)"""
    try:
        # 날짜 형식 통일 (25-11-10 형식)
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%y-%m-%d")  # 25-11-10
        
        # 그룹진도표에서 해당 날짜 행 찾기 (다양한 형식 지원)
        date_row = None
        for idx, row in 그룹진도표.iterrows():
            date_col = str(row['날짜']).strip()
            # "25-11-10 월" 형식도 지원
            if formatted_date in date_col or date_col.startswith(formatted_date):
                date_row = 그룹진도표.iloc[[idx]]
                break
        
        if date_row is None or date_row.empty:
            return None
        
        # 반정보에서 해당 반의 컬럼명 찾기
        class_info = 반정보[반정보['반이름'] == class_name]
        if class_info.empty:
            return None
        
        result = {}
        
        # 진도-문법
        if '진도-문법' in class_info.columns:
            col_name = class_info['진도-문법'].iloc[0]
            if col_name and col_name in date_row.columns:
                val = date_row[col_name].iloc[0]
                if val and str(val).strip() and str(val) != 'nan':
                    result['문법'] = val
        
        # 과제-문법
        if '과제-문법' in class_info.columns:
            col_name = class_info['과제-문법'].iloc[0]
            if col_name and col_name in date_row.columns:
                val = date_row[col_name].iloc[0]
                if val and str(val).strip() and str(val) != 'nan':
                    result['문법과제'] = val
        
        # 진도-듣기
        if '진도-듣기' in class_info.columns:
            col_name = class_info['진도-듣기'].iloc[0]
            if col_name and col_name in date_row.columns:
                val = date_row[col_name].iloc[0]
                if val and str(val).strip() and str(val) != 'nan':
                    result['듣기'] = val
        
        # 진도-독해
        if '진도-독해' in class_info.columns:
            col_name = class_info['진도-독해'].iloc[0]
            if col_name and col_name in date_row.columns:
                val = date_row[col_name].iloc[0]
                if val and str(val).strip() and str(val) != 'nan':
                    result['독해'] = val
        
        # 과제-독해
        if '과제-독해' in class_info.columns:
            col_name = class_info['과제-독해'].iloc[0]
            if col_name and col_name in date_row.columns:
                val = date_row[col_name].iloc[0]
                if val and str(val).strip() and str(val) != 'nan':
                    result['독해과제'] = val
        
        return result if result else None
    except Exception as e:
        return None

# ========================
# 메인 UI
# ========================
def main():
    st.title("📚 AZA 학원 통합 대시보드")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # Sheets ID를 Secrets에서 불러오기 (없으면 입력 받기)
        default_sheet_id = ""
        if 'google_sheets_id' in st.secrets:
            default_sheet_id = st.secrets['google_sheets_id']
            st.success("✅ Sheets ID 자동 로드")
        
        sheet_id = st.text_input(
            "Google Sheets ID",
            value=default_sheet_id,
            help="스프레드시트 URL의 /d/ 다음 부분을 입력하세요",
            disabled=bool(default_sheet_id)  # Secrets에 있으면 수정 불가
        )
        st.session_state.sheet_id = sheet_id
        
        st.markdown("---")
        
        # 디버그 모드
        if 'debug_mode' not in st.session_state:
            st.session_state.debug_mode = False
        
        st.session_state.debug_mode = st.checkbox("🔍 디버그 모드", value=st.session_state.debug_mode)
        
        st.markdown("---")
        
        # 날짜 선택 위젯
        st.header("📅 날짜 선택")
        selected_date = st.date_input(
            "수업 날짜",
            value=datetime.now(),
            format="YYYY-MM-DD"
        )
        
        weekday = selected_date.weekday()  # 0=월, 1=화, ..., 6=일
        weekday_name = ['월', '화', '수', '목', '금', '토', '일'][weekday]
        
        st.info(f"선택: {selected_date.strftime('%Y-%m-%d')} ({weekday_name})")
        
        # 시간표 선택
        if weekday in [0, 4]:  # 월, 금
            시간표 = 월금_시간표
            st.success("✅ 월/금 시간표 적용")
        elif weekday in [1, 3]:  # 화, 목
            시간표 = 화목_시간표
            st.success("✅ 화/목 시간표 적용")
        else:
            st.warning("⚠️ 수업 없는 요일입니다")
            시간표 = None
    
    # 데이터 로드
    if not sheet_id:
        st.warning("⬅️ 왼쪽 사이드바에서 Google Sheets ID를 입력해주세요")
        st.info("""
        **Google Sheets ID 찾는 방법:**
        
        1. Google Sheets 열기
        2. 주소창의 URL 확인
        3. `/d/` 와 `/edit` 사이의 긴 문자열 복사
        
        예시: `https://docs.google.com/spreadsheets/d/[이부분복사]/edit`
        """)
        st.stop()
    
    client = get_google_client()
    if not client:
        st.stop()
    
    with st.spinner("📊 Google Sheets에서 데이터 로딩 중..."):
        학생명단, 반정보, 그룹진도표, 개별진도표 = load_sheet_data(client, sheet_id)
    
    if 그룹진도표 is None:
        st.error("❌ 데이터를 불러올 수 없습니다")
        st.warning("""
        **체크리스트:**
        1. Google Sheets ID가 올바른가요?
        2. Sheets가 서비스 계정과 공유되었나요?
        3. 시트 이름이 정확한가요? (학생명단, 반정보, 그룹진도표, 개별진도표)
        """)
        st.stop()
    
    # 데이터 로딩 성공 표시
    st.sidebar.success(f"✅ 데이터 로딩 완료")
    st.sidebar.info(f"""
    **로드된 데이터:**
    - 학생: {len(학생명단)}명
    - 반: {len(반정보)}개
    - 그룹진도: {len(그룹진도표)}일
    - 개별진도: {len(개별진도표)}건
    """)
    
    # 디버깅: 그룹진도표 날짜 확인
    with st.sidebar.expander("🔍 디버깅 정보"):
        st.write("**그룹진도표 날짜 목록 (최근 10개):**")
        if len(그룹진도표) > 0:
            dates = 그룹진도표['날짜'].head(10).tolist()
            for d in dates:
                st.write(f"- {d}")
        
        st.write("**반정보 목록:**")
        if len(반정보) > 0:
            classes = 반정보['반이름'].tolist()
            for c in classes:
                st.write(f"- {c}")
    
    # 시간표가 없는 경우
    if 시간표 is None:
        st.info("선택한 날짜는 수업이 없습니다")
        st.stop()
    
    # ========================
    # 시간표 뷰 (하나의 통합 표)
    # ========================
    st.header(f"🏫 {selected_date.strftime('%Y-%m-%d')} ({weekday_name}) 시간표")
    
    # 요일에 따라 선생님 이름 설정
    if weekday in [0, 4]:  # 월금
        room_keys = ["대강의실(원장)", "유리방(예은T)", "나무방(채민T)", "모고방(관리T)"]
        room_names = ["대강의실(원장)", "유리방(예은T)", "나무방(채민T)", "모고방(관리T)"]
    else:  # 화목
        room_keys = ["대강의실(원장)", "유리방(민서T)", "나무방(승연T)", "모고방(관리T)"]
        room_names = ["대강의실(원장)", "유리방(민서T)", "나무방(승연T)", "모고방(관리T)"]
    
    # HTML 생성 (리스트로 모아서 join)
    html_parts = []
    
    # CSS
    html_parts.append('''
    <style>
        .schedule-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .schedule-table th {
            background-color: #1f77b4;
            color: white;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #ddd;
        }
        .schedule-table td {
            padding: 10px;
            border: 1px solid #ddd;
            vertical-align: top;
            min-height: 60px;
        }
        .schedule-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .time-cell {
            background-color: #e8f4f8;
            font-weight: bold;
            text-align: center;
            white-space: nowrap;
            width: 10%;
        }
        .class-name {
            color: #1f77b4;
            font-weight: bold;
            font-size: 14px;
        }
        .activity {
            color: #666;
            font-size: 13px;
            margin: 4px 0;
            line-height: 1.4;
        }
        .progress {
            color: #2c5f2d;
            font-size: 12px;
            background-color: #f0f8f0;
            padding: 6px;
            margin-top: 6px;
            border-radius: 3px;
            border-left: 3px solid #4CAF50;
        }
        .empty-cell {
            text-align: center;
            color: #ccc;
            font-size: 16px;
        }
    </style>
    <table class="schedule-table">
        <thead>
            <tr>
                <th class="time-cell">시간</th>
    ''')
    
    # 헤더 추가
    for name in room_names:
        html_parts.append(f'<th>{name}</th>')
    
    html_parts.append('</tr></thead><tbody>')
    
    # 시간대별로 행 생성
    for time_slot, room_data in 시간표.items():
        html_parts.append(f'<tr><td class="time-cell">{time_slot}</td>')
        
        for room in room_keys:
            info = room_data[room]
            
            if info['반'] and info['반'] != "-":
                class_names = [c.strip() for c in info['반'].split(',')]
                
                cell_parts = []
                cell_parts.append(f'<div class="class-name">{info["반"]}</div>')
                
                activity_text = info['내용'].replace('\n', '<br>')
                cell_parts.append(f'<div class="activity">{activity_text}</div>')
                
                # 진도 정보
                activity_lower = info['내용'].lower()
                progress_items = []
                
                for class_name in class_names:
                    if class_name in ['초등', '중등', '수능', '정시']:
                        if weekday in [0, 4]:
                            full_class_name = f"{class_name}-월금"
                        else:
                            full_class_name = f"{class_name}-화목"
                    else:
                        full_class_name = class_name
                    
                    progress = get_class_progress(
                        selected_date.strftime("%Y-%m-%d"),
                        full_class_name,
                        그룹진도표,
                        반정보
                    )
                    
                    if progress:
                        # 시험, 오답, 재시험, 해석 → 진도 표시 안 함
                        if any(word in activity_lower for word in ['시험', '오답', '재시험', '해석']):
                            # 단, "과제"는 예외 (과제는 표시해야 함)
                            if '과제' not in activity_lower:
                                continue
                        
                        # 과제 활동
                        if '과제' in activity_lower:
                            if '문법' in activity_lower and '문법과제' in progress:
                                content = str(progress['문법과제'])
                                if len(content) > 40:
                                    content = content[:40] + "..."
                                progress_items.append(f"과제: {content}")
                            elif '독해' in activity_lower and '독해과제' in progress:
                                content = str(progress['독해과제'])
                                if len(content) > 40:
                                    content = content[:40] + "..."
                                progress_items.append(f"과제: {content}")
                            # 과제만 있고 과목 없으면 모든 과제 표시
                            elif not any(x in activity_lower for x in ['문법', '독해']):
                                if '문법과제' in progress:
                                    content = str(progress['문법과제'])
                                    if len(content) > 40:
                                        content = content[:40] + "..."
                                    progress_items.append(f"문법과제: {content}")
                                if '독해과제' in progress:
                                    content = str(progress['독해과제'])
                                    if len(content) > 40:
                                        content = content[:40] + "..."
                                    progress_items.append(f"독해과제: {content}")
                        
                        # 문법 수업
                        elif '문법' in activity_lower and '문법' in progress:
                            content = str(progress['문법'])
                            if len(content) > 40:
                                content = content[:40] + "..."
                            progress_items.append(f"문법: {content}")
                        
                        # 독해 수업 (모고 포함)
                        elif ('독해' in activity_lower or '모고' in activity_lower or '문제풀이' in activity_lower) and '독해' in progress:
                            content = str(progress['독해'])
                            if len(content) > 40:
                                content = content[:40] + "..."
                            progress_items.append(f"독해: {content}")
                        
                        # 듣기 수업
                        elif '듣기' in activity_lower and '듣기' in progress:
                            content = str(progress['듣기'])
                            if len(content) > 40:
                                content = content[:40] + "..."
                            progress_items.append(f"듣기: {content}")
                        
                        # "수업"만 있고 특정 과목이 없으면 → 모든 진도 표시
                        elif '수업' in activity_lower and not any(x in activity_lower for x in ['문법', '독해', '듣기', '과제']):
                            for subject, content in progress.items():
                                if content and str(content).strip() and str(content) != 'nan':
                                    content_str = str(content)
                                    if len(content_str) > 40:
                                        content_str = content_str[:40] + "..."
                                    progress_items.append(f"{subject}: {content_str}")
                
                if progress_items:
                    cell_parts.append('<div class="progress">')
                    for item in progress_items:
                        cell_parts.append(f'{item}<br>')
                    cell_parts.append('</div>')
                
                html_parts.append(f'<td>{"".join(cell_parts)}</td>')
            else:
                html_parts.append('<td class="empty-cell">-</td>')
        
        html_parts.append('</tr>')
    
    html_parts.append('</tbody></table>')
    
    # 한 번에 출력
    st.markdown(''.join(html_parts), unsafe_allow_html=True)
    
    # ========================
    # 반별 요약
    # ========================
    st.markdown("---")
    st.header("📊 반별 오늘 일정 요약")
    
    # 반 순서 정의 (초등 → 중등 → 수능 → 정시 → 내신)
    class_order = ['초등', '중등', '수능', '정시', '내신']
    
    # 모든 반 추출
    all_classes = set()
    for room_data in 시간표.values():
        for info in room_data.values():
            if info['반'] and info['반'] != "-":
                classes = [c.strip() for c in info['반'].split(',')]
                all_classes.update(classes)
    
    # 정렬된 순서로 반별 정리
    sorted_classes = []
    for base_class in class_order:
        # 월금/화목 구분
        if weekday in [0, 4]:
            full_name = f"{base_class}-월금"
        else:
            full_name = f"{base_class}-화목"
        
        # 해당 반이 존재하는 경우만 추가
        if base_class in all_classes:
            sorted_classes.append((base_class, full_name))
    
    # 반별로 표시
    for class_name, full_class_name in sorted_classes:
        with st.expander(f"📚 {full_class_name} 일정"):
            # 시간표에서 해당 반 스케줄 추출
            schedule = []
            for time_slot, room_data in 시간표.items():
                for room, info in room_data.items():
                    if info['반'] and class_name in info['반']:
                        # 활동 내용
                        activity = info['내용']
                        activity_lower = activity.lower()
                        
                        # 진도 정보 가져오기
                        progress = get_class_progress(
                            selected_date.strftime("%Y-%m-%d"),
                            full_class_name,
                            그룹진도표,
                            반정보
                        )
                        
                        # 진도를 활동 옆에 표시할지 결정
                        progress_text = ""
                        if progress:
                            # 시험/오답/재시험/해석은 진도 표시 안 함 (과제는 예외)
                            if not any(word in activity_lower for word in ['시험', '오답', '재시험', '해석']) or '과제' in activity_lower:
                                progress_parts = []
                                
                                # 과제 활동
                                if '과제' in activity_lower:
                                    if '문법' in activity_lower and '문법과제' in progress:
                                        progress_parts.append(f"📖과제: {progress['문법과제']}")
                                    elif '독해' in activity_lower and '독해과제' in progress:
                                        progress_parts.append(f"📖과제: {progress['독해과제']}")
                                    elif not any(x in activity_lower for x in ['문법', '독해']):
                                        if '문법과제' in progress:
                                            progress_parts.append(f"📖문법과제: {progress['문법과제']}")
                                        if '독해과제' in progress:
                                            progress_parts.append(f"📖독해과제: {progress['독해과제']}")
                                
                                # 문법 수업 → 문법 진도
                                elif '문법' in activity_lower and '문법' in progress:
                                    progress_parts.append(f"📖문법: {progress['문법']}")
                                
                                # 독해 수업 (모고 포함) → 독해 진도
                                elif ('독해' in activity_lower or '모고' in activity_lower or '문제풀이' in activity_lower) and '독해' in progress:
                                    progress_parts.append(f"📖독해: {progress['독해']}")
                                
                                # 듣기 수업 → 듣기 진도
                                elif '듣기' in activity_lower and '듣기' in progress:
                                    progress_parts.append(f"📖듣기: {progress['듣기']}")
                                
                                # "수업"만 있으면 모든 진도
                                elif '수업' in activity_lower and not any(x in activity_lower for x in ['문법', '독해', '듣기', '과제']):
                                    for subject, content in progress.items():
                                        if content and str(content).strip() and str(content) != 'nan':
                                            progress_parts.append(f"📖{subject}: {content}")
                                
                                # 진도가 있으면 괄호로 추가
                                if progress_parts:
                                    progress_text = f" ({', '.join(progress_parts)})"
                        
                        schedule.append(f"**{time_slot}** - {room}: {activity}{progress_text}")
            
            for item in schedule:
                st.write(item)

if __name__ == "__main__":
    main()
