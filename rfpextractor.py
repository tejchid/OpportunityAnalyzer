import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import PyPDF2
import docx
import io
from urllib.parse import urljoin, urlparse
import time
import json
from typing import Dict, List, Tuple, Optional
import logging
import plotly.express as px  # Added for visualizations

# Page setup
st.set_page_config(page_title="Industry NAV Opportunities Analyzer", layout="wide")

# Clean CSS
st.markdown("""
<style>
.stApp {
    background-color: #f8f9fa;
}
.stSidebar {
    background-color: #ffffff;
    border-right: 1px solid #e9ecef;
}
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.pulsing-success {
    animation: pulse 1.5s ease-in-out infinite alternate;
    background: linear-gradient(90deg, #28a745, #20c997);
    color: white;
    padding: 12px;
    border-radius: 8px;
    text-align: center;
    font-weight: 600;
    margin: 1rem 0;
}
@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    100% { transform: scale(1.02); opacity: 0.9; }
}
.stDataFrame {
    border: 1px solid #e9ecef;
    border-radius: 8px;
    overflow: hidden;
}
h1, h2, h3 {
    color: #212529;
    font-weight: 600;
}
.stMetric {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.score-breakdown {
    background: #f8f9fa;
    padding: 8px;
    border-radius: 4px;
    font-size: 0.9em;
    margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sidebar filters
st.sidebar.header("Filters")
locations = st.sidebar.multiselect(
    "Target Locations",
    ['california', 'sunnyvale', 'claremont', 'texas', 'florida', 'new york', 'illinois'],
    default=['california', 'sunnyvale', 'claremont']
)
show_expired = st.sidebar.checkbox("Show Expired", value=False)
search_documents = st.sidebar.checkbox("Search Inside Documents", value=True, help="Downloads and searches PDF/Word documents for keywords (slower but more thorough)")

# Ruckus dog image in sidebar (use a placeholder URL if local file is missing)
try:
    st.sidebar.image("https://via.placeholder.com/250x200.png?text=Ruckus+Dog", width=250)
except:
    st.sidebar.write("🐕 Ruckus Dog")

# Header
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🎯 Industry NAV Opportunities Analyzer")
with col2:
    st.write("")  # Empty space since dog is now in sidebar

# Keywords for networking with weights
networking_keywords = {
    'high_priority': ['ruckus', 'commscope', 'wifi 6', 'wifi 6e', 'wifi 7', 'enterprise wireless', 'wireless infrastructure'],
    'medium_priority': ['wifi', 'wi-fi', 'wireless', 'wlan', 'access point', 'mesh network', 'wireless controller'],
    'low_priority': ['network', 'networking', 'ethernet', 'switch', 'router', 'iot', 'infrastructure', 'cybersecurity']
}

# Bad keywords for walk-through filter
bad_keywords = {
    'disqualifiers': [
        'medical equipment', 'hospital', 'healthcare', 'patient care', 'medical device',
        'pharmaceutical', 'drug', 'medicine', 'clinic', 'surgery', 'dental',
        'construction', 'building', 'concrete', 'plumbing', 'electrical wiring', 'hvac',
        'food service', 'catering', 'restaurant', 'kitchen equipment', 'cafeteria',
        'landscaping', 'gardening', 'lawn care', 'tree removal', 'grounds maintenance',
        'janitorial', 'cleaning supplies', 'custodial', 'sanitation', 'waste management',
        'vehicle', 'automotive', 'fleet management', 'truck', 'car', 'transportation',
        'fuel', 'gasoline', 'diesel', 'oil change', 'maintenance garage'
    ],
    'penalty': [
        'legacy system', 'mainframe', 'cobol', 'obsolete', 'end of life',
        'budget cut', 'cost reduction', 'cheapest', 'lowest bid only',
        'non-technical', 'manual process', 'paper based', 'offline only',
        'proprietary only', 'single vendor', 'no alternatives',
        'temporary', 'short term', 'pilot only', 'proof of concept'
    ]
}

# Context window size for walk-through analysis
CONTEXT_WINDOW_SIZE = 50

# Agent classes (unchanged from original)
class RFPDataFetcher:
    @staticmethod
    def fetch_rfp_data(api_url: str = None, timeout: int = 15) -> Dict:
        try:
            if not api_url:
                api_url = "https://www.governmentnavigator.com/api/bidfeed?email=marcelo.molinari@commscope.com&token=22c7f7254d4202af5c73bd9108c527ed"
            response = requests.get(api_url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            bids = data.get('bids', data) if isinstance(data, dict) else data
            return {
                'success': True,
                'data': bids,
                'error': None,
                'count': len(bids) if isinstance(bids, list) else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching RFP data: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': str(e),
                'count': 0,
                'timestamp': datetime.now().isoformat()
            }

class DocumentProcessor:
    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
            return text.lower().strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return ""

    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        try:
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + " "
            return text.lower().strip()
        except Exception as e:
            logger.error(f"DOCX extraction error: {str(e)}")
            return ""

    @staticmethod
    def download_and_extract_document_text(url: str, timeout: int = 15) -> Dict:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
            text = ""
            if 'pdf' in content_type:
                text = DocumentProcessor.extract_text_from_pdf(response.content)
            elif 'word' in content_type or 'document' in content_type:
                text = DocumentProcessor.extract_text_from_docx(response.content)
            else:
                try:
                    text = response.text.lower().strip()
                except:
                    text = ""
            return {
                'success': True,
                'text': text,
                'error': None,
                'content_type': content_type,
                'url': url,
                'text_length': len(text)
            }
        except Exception as e:
            logger.error(f"Document download error for {url}: {str(e)}")
            return {
                'success': False,
                'text': "",
                'error': str(e),
                'content_type': None,
                'url': url,
                'text_length': 0
            }

class KeywordAnalyzer:
    @staticmethod
    def walk_through_bad_keyword_filter(text: str) -> Dict:
        if not text:
            return {
                'disqualified': False,
                'penalty_score': 0,
                'bad_keywords_found': [],
                'context_analysis': []
            }
        text_lower = text.lower()
        words = text_lower.split()
        disqualifiers_found = []
        for bad_keyword in bad_keywords['disqualifiers']:
            if bad_keyword in text_lower:
                disqualifiers_found.append(bad_keyword)
        if disqualifiers_found:
            return {
                'disqualified': True,
                'penalty_score': 0,
                'bad_keywords_found': disqualifiers_found,
                'context_analysis': [],
                'reason': 'Contains disqualifying keywords'
            }
        penalty_keywords_found = []
        context_analysis = []
        total_penalty = 0
        for penalty_keyword in bad_keywords['penalty']:
            if penalty_keyword in text_lower:
                penalty_keywords_found.append(penalty_keyword)
                keyword_positions = []
                start = 0
                while True:
                    pos = text_lower.find(penalty_keyword, start)
                    if pos == -1:
                        break
                    keyword_positions.append(pos)
                    start = pos + 1
                for pos in keyword_positions:
                    words_before_pos = text_lower[:pos].count(' ')
                    start_word = max(0, words_before_pos - CONTEXT_WINDOW_SIZE)
                    end_word = min(len(words), words_before_pos + CONTEXT_WINDOW_SIZE)
                    context = ' '.join(words[start_word:end_word])
                    has_good_context = any(
                        good_kw in context
                        for category in networking_keywords.values()
                        for good_kw in category
                    )
                    context_analysis.append({
                        'penalty_keyword': penalty_keyword,
                        'context': context[:200] + '...' if len(context) > 200 else context,
                        'has_good_networking_context': has_good_context,
                        'penalty_applied': not has_good_context
                    })
                    if not has_good_context:
                        total_penalty += 50
        return {
            'disqualified': False,
            'penalty_score': total_penalty,
            'bad_keywords_found': penalty_keywords_found,
            'context_analysis': context_analysis
        }

    @staticmethod
    def analyze_text_for_keywords(text: str, keywords_dict: Dict[str, List[str]], apply_walk_through: bool = True) -> Dict:
        if not text:
            return {
                'total_score': 0,
                'matched_keywords': [],
                'score_breakdown': {},
                'text_analyzed': False,
                'walk_through_result': None
            }
        result = {
            'text_analyzed': True,
            'walk_through_result': None
        }
        if apply_walk_through:
            walk_through_result = KeywordAnalyzer.walk_through_bad_keyword_filter(text)
            result['walk_through_result'] = walk_through_result
            if walk_through_result['disqualified']:
                return {
                    **result,
                    'total_score': -1000,
                    'matched_keywords': [],
                    'score_breakdown': {'disqualified': True},
                    'disqualified': True,
                    'disqualification_reason': walk_through_result.get('reason', 'Contains bad keywords')
                }
        text_lower = text.lower()
        matched_keywords = []
        score_breakdown = {}
        total_score = 0
        high_matches = [kw for kw in keywords_dict['high_priority'] if kw in text_lower]
        if high_matches:
            score_breakdown['high_priority'] = len(high_matches) * 30
            total_score += score_breakdown['high_priority']
            matched_keywords.extend(high_matches)
        medium_matches = [kw for kw in keywords_dict['medium_priority'] if kw in text_lower]
        if medium_matches:
            score_breakdown['medium_priority'] = len(medium_matches) * 20
            total_score += score_breakdown['medium_priority']
            matched_keywords.extend(medium_matches)
        low_matches = [kw for kw in keywords_dict['low_priority'] if kw in text_lower]
        if low_matches:
            score_breakdown['low_priority'] = len(low_matches) * 10
            total_score += score_breakdown['low_priority']
            matched_keywords.extend(low_matches)
        penalty_score = 0
        if apply_walk_through and result['walk_through_result']:
            penalty_score = result['walk_through_result']['penalty_score']
            total_score -= penalty_score
            score_breakdown['penalty'] = -penalty_score
        return {
            **result,
            'total_score': max(0, total_score),
            'matched_keywords': list(set(matched_keywords)),
            'score_breakdown': score_breakdown,
            'keyword_counts': {
                'high_priority': len(high_matches),
                'medium_priority': len(medium_matches),
                'low_priority': len(low_matches)
            },
            'disqualified': False
        }

class RFPScorer:
    @staticmethod
    def calculate_comprehensive_score(rfp_data: Dict, document_analysis: Dict = None) -> Dict:
        score_components = {}
        total_score = 0
        try:
            due_date = pd.to_datetime(rfp_data.get('due_date'))
            days_until_due = (due_date - datetime.now()).days
            if days_until_due <= 7:
                urgency_score = 40
            elif days_until_due <= 14:
                urgency_score = 30
            elif days_until_due <= 30:
                urgency_score = 20
            elif days_until_due <= 60:
                urgency_score = 10
            else:
                urgency_score = 0
            score_components['urgency'] = urgency_score
            total_score += urgency_score
        except:
            score_components['urgency'] = 0
        jurisdiction = str(rfp_data.get('jurisdiction_title', '')).lower()
        location_score = 20 if any(loc.lower() in jurisdiction for loc in locations) else 0
        score_components['location'] = location_score
        total_score += location_score
        status = str(rfp_data.get('opportunity_status', '')).lower()
        status_score = 10 if status in ['open', 'active'] else 0  # More flexible status check
        score_components['status'] = status_score
        total_score += status_score
        if document_analysis and document_analysis.get('text_analyzed'):
            keyword_score = document_analysis['total_score']
            score_components['keywords'] = keyword_score
            score_components['keyword_breakdown'] = document_analysis['score_breakdown']
            total_score += keyword_score
        else:
            score_components['keywords'] = 0
            score_components['keyword_breakdown'] = {}
        title_desc_text = ' '.join([
            str(rfp_data.get('title', '')).lower(),
            str(rfp_data.get('description', '')).lower(),
            str(rfp_data.get('short_description', '')).lower()
        ])
        title_analysis = KeywordAnalyzer.analyze_text_for_keywords(title_desc_text, networking_keywords)
        title_score = min(title_analysis['total_score'], 30)
        score_components['title_description'] = title_score
        total_score += title_score
        if total_score >= 100:
            priority_level = 'Critical'
        elif total_score >= 70:
            priority_level = 'High'
        elif total_score >= 40:
            priority_level = 'Medium'
        else:
            priority_level = 'Low'
        return {
            'total_score': total_score,
            'priority_level': priority_level,
            'score_components': score_components,
            'max_possible_score': 200,
            'score_percentage': round((total_score / 200) * 100, 1)
        }

class RFPAnalyzer:
    @staticmethod
    def analyze_single_rfp(rfp_data: Dict, search_docs: bool = True) -> Dict:
        analysis_result = {
            'rfp_id': rfp_data.get('id', 'unknown'),
            'title': rfp_data.get('title', ''),
            'analysis_timestamp': datetime.now().isoformat(),
            'document_analysis': None,
            'scoring': None,
            'errors': [],
            'processing_time_saved': False
        }
        title_desc_text = ' '.join([
            str(rfp_data.get('title', '')).lower(),
            str(rfp_data.get('description', '')).lower(),
            str(rfp_data.get('short_description', '')).lower()
        ])
        quick_walk_through = KeywordAnalyzer.walk_through_bad_keyword_filter(title_desc_text)
        if quick_walk_through['disqualified']:
            analysis_result['processing_time_saved'] = True
            analysis_result['early_disqualification'] = True
            analysis_result['disqualification_reason'] = quick_walk_through.get('reason', 'Bad keywords in title/description')
            document_analysis = KeywordAnalyzer.analyze_text_for_keywords(title_desc_text, networking_keywords)
            document_analysis['early_disqualified'] = True
            analysis_result['document_analysis'] = document_analysis
            scoring = RFPScorer.calculate_comprehensive_score(rfp_data, document_analysis)
            scoring['disqualified'] = True
            analysis_result['scoring'] = scoring
            return analysis_result
        document_analysis = None
        if search_docs:
            doc_urls = []
            for field in ['document_url', 'attachment_url', 'file_url', 'documents']:
                if field in rfp_data and pd.notna(rfp_data[field]):
                    if isinstance(rfp_data[field], str) and rfp_data[field].startswith('http'):
                        doc_urls.append(rfp_data[field])
                    elif isinstance(rfp_data[field], list):
                        doc_urls.extend([url for url in rfp_data[field] if isinstance(url, str) and url.startswith('http')])
            if not doc_urls:
                analysis_result['errors'].append("No valid document URLs found")
            combined_text = ""
            document_results = []
            for url in doc_urls[:3]:
                doc_result = DocumentProcessor.download_and_extract_document_text(url)
                document_results.append(doc_result)
                if doc_result['success']:
                    combined_text += doc_result['text'] + " "
                else:
                    analysis_result['errors'].append(f"Document processing failed: {doc_result['error']}")
                time.sleep(1)  # Increased delay to respect server
            full_text = title_desc_text + " " + combined_text
            document_analysis = KeywordAnalyzer.analyze_text_for_keywords(full_text, networking_keywords, apply_walk_through=True)
            document_analysis['document_urls'] = doc_urls
            document_analysis['document_results'] = document_results
            document_analysis['full_text_length'] = len(full_text)
            if document_analysis.get('disqualified'):
                analysis_result['processing_time_saved'] = False
                analysis_result['document_disqualification'] = True
            analysis_result['document_analysis'] = document_analysis
        else:
            document_analysis = KeywordAnalyzer.analyze_text_for_keywords(title_desc_text, networking_keywords, apply_walk_through=True)
            analysis_result['document_analysis'] = document_analysis
        scoring = RFPScorer.calculate_comprehensive_score(rfp_data, document_analysis)
        if document_analysis and document_analysis.get('disqualified'):
            scoring['disqualified'] = True
            scoring['total_score'] = 0
            scoring['priority_level'] = 'Disqualified'
        analysis_result['scoring'] = scoring
        return analysis_result

def main():
    # Check if data is available
    try:
        with st.spinner("Fetching RFP data..."):
            data_result = RFPDataFetcher.fetch_rfp_data()
        if not data_result['success'] or not data_result['data']:
            st.error(f"Failed to fetch data: {data_result.get('error', 'No data returned')}")
            return
        df = pd.DataFrame(data_result['data'])
        if df.empty:
            st.warning("No RFP data available to analyze.")
            return
        st.success(f"Successfully loaded {len(df)} RFPs")
        st.write('Initial DataFrame loaded:', df)  # Debug output
    except Exception as e:
        st.error(f"Critical error: {str(e)}")
        return
    # Process data
    with st.spinner("Analyzing RFPs and processing documents..." if search_documents else "Analyzing RFPs..."):
        analysis_results = []
        progress_bar = st.progress(0)
        if search_documents:
            st.info("🔍 Performing deep document analysis... This may take several minutes.")
        for idx, (_, row) in enumerate(df.iterrows()):
            try:
                analysis = RFPAnalyzer.analyze_single_rfp(row.to_dict(), search_documents)
                analysis_results.append(analysis)
                progress_bar.progress((idx + 1) / len(df))
            except Exception as e:
                st.warning(f"Error analyzing RFP {row.get('id', 'unknown')}: {str(e)}")
                continue
        time_saved_count = 0
        disqualified_count = 0
        for idx, analysis in enumerate(analysis_results):
            if idx < len(df):
                scoring = analysis.get('scoring', {})
                df.loc[idx, 'Total_Score'] = scoring.get('total_score', 0)
                df.loc[idx, 'Priority_Level'] = scoring.get('priority_level', 'Low')
                df.loc[idx, 'Score_Percentage'] = scoring.get('score_percentage', 0)
                df.loc[idx, 'Keyword_Score'] = scoring.get('score_components', {}).get('keywords', 0)
                df.loc[idx, 'Urgency_Score'] = scoring.get('score_components', {}).get('urgency', 0)
                df.loc[idx, 'Time_Saved'] = analysis.get('processing_time_saved', False)
                df.loc[idx, 'Disqualified'] = scoring.get('disqualified', False)
                if analysis.get('processing_time_saved'):
                    time_saved_count += 1
                if scoring.get('disqualified'):
                    disqualified_count += 1
                doc_analysis = analysis.get('document_analysis', {})
                df.loc[idx, 'Keywords_Found'] = ', '.join(doc_analysis.get('matched_keywords', []))
                walk_through = doc_analysis.get('walk_through_result', {})
                if walk_through:
                    bad_keywords = walk_through.get('bad_keywords_found', [])
                    df.loc[idx, 'Bad_Keywords_Found'] = ', '.join(bad_keywords) if bad_keywords else ''
        if time_saved_count > 0:
            st.success(f"⚡ Walk-through filter saved time on {time_saved_count} RFPs by early disqualification!")
        if disqualified_count > 0:
            st.warning(f"🚫 {disqualified_count} RFPs disqualified due to bad keywords")
    # Notify user when deep document analysis is complete
    if search_documents:
        st.success("✅ Deep document analysis completed!")
    # Apply filters
    filtered_df = df.copy()
    if not show_expired:
        filtered_df = filtered_df[filtered_df['opportunity_status'].str.lower().isin(['open', 'active'])]
    if locations:
        filtered_df = filtered_df[filtered_df['jurisdiction_title'].str.lower().apply(lambda x: any(loc.lower() in str(x) for loc in locations))]
    qualified_df = filtered_df[~filtered_df['Disqualified'].fillna(False)]
    disqualified_df = filtered_df[filtered_df['Disqualified'].fillna(False)]
    # Key metrics
    st.subheader("📈 Advanced Scoring Metrics with Walk-Through Filtering")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total RFPs", len(filtered_df))
    col2.metric("Qualified", len(qualified_df))
    col3.metric("Disqualified", len(disqualified_df))
    # Ensure 'Total_Score' column exists and fill missing values before sorting
    if 'Total_Score' not in qualified_df.columns:
        qualified_df['Total_Score'] = 0
    qualified_df['Total_Score'] = qualified_df['Total_Score'].fillna(0)
    # Ensure 'Priority_Level' column exists and fill missing values before using query
    if 'Priority_Level' not in qualified_df.columns:
        qualified_df['Priority_Level'] = 'Low'
    qualified_df['Priority_Level'] = qualified_df['Priority_Level'].fillna('Low')
    critical_high = len(qualified_df.query("`Priority_Level` in ['Critical', 'High']"))
    col4.metric("Critical/High Priority", critical_high)
    avg_score = qualified_df['Total_Score'].mean() if not qualified_df.empty else 0
    col5.metric("Average Score", f"{avg_score:.1f}")
    col6.metric("Time Saved", f"{time_saved_count} RFPs")
    # Display columns
    display_cols = ['id', 'title', 'type', 'due_date', 'opportunity_status', 'jurisdiction_title']
    display_cols = [c for c in display_cols if c in df.columns]
    score_cols = ['Total_Score', 'Priority_Level', 'Score_Percentage', 'Keywords_Found']
    walk_through_cols = ['Bad_Keywords_Found', 'Time_Saved']
    # Critical Priority section
    st.subheader("🚨 Critical Priority Opportunities")
    critical = qualified_df[qualified_df['Priority_Level'] == 'Critical']
    if not critical.empty:
        st.error(f"🔥 URGENT: {len(critical)} critical opportunities require immediate attention!")
        st.dataframe(critical[display_cols + score_cols], use_container_width=True)
        with st.expander("Critical Items Detailed Analysis"):
            for idx, row in critical.iterrows():
                st.write(f"**{row.get('title', 'Unnamed')}** (Score: {row.get('Total_Score', 0)})")
                if row.get('Keywords_Found'):
                    st.write(f"Keywords: {row['Keywords_Found']}")
    else:
        st.info("No critical priority opportunities found.")
    # High Priority section
    st.subheader("⚡ High Priority Opportunities")
    high_priority = qualified_df[qualified_df['Priority_Level'] == 'High']
    if not high_priority.empty:
        st.warning(f"Found {len(high_priority)} high priority opportunities!")
        st.dataframe(high_priority[display_cols + score_cols], use_container_width=True)
    else:
        st.info("No high priority opportunities found.")
    # Medium Priority section
    st.subheader("📋 Medium Priority Opportunities")
    medium_priority = qualified_df[qualified_df['Priority_Level'] == 'Medium']
    if not medium_priority.empty:
        st.success(f"Found {len(medium_priority)} medium priority opportunities")
        st.dataframe(medium_priority[display_cols + score_cols], use_container_width=True)
    else:
        st.info("No medium priority opportunities found.")
    # Disqualified RFPs section
    if not disqualified_df.empty:
        with st.expander(f"🚫 Disqualified RFPs ({len(disqualified_df)}) - Walk-Through Filter Results"):
            st.warning("These RFPs were disqualified due to bad keywords:")
            st.dataframe(disqualified_df[display_cols + score_cols + walk_through_cols], use_container_width=True)
    # All Qualified RFPs
    with st.expander("📋 All Qualified RFPs with Scores"):
        # Only display columns that exist in qualified_df
        all_display_cols = display_cols + score_cols + ['Keyword_Score', 'Urgency_Score']
        existing_display_cols = [col for col in all_display_cols if col in qualified_df.columns]
        st.dataframe(qualified_df[existing_display_cols], use_container_width=True)
    # Export
    st.subheader("📥 Export Enhanced Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="Download All (CSV)",
            data=filtered_df.to_csv(index=False),
            file_name=f"rfp_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
    with col2:
        high_value = qualified_df[qualified_df['Priority_Level'].isin(['Critical', 'High'])]
        if not high_value.empty:
            st.download_button(
                label="Download High Value (CSV)",
                data=high_value.to_csv(index=False),
                file_name=f"high_value_rfps_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )
    with col3:
        analysis_json = json.dumps(analysis_results, indent=2, default=str)
        st.download_button(
            label="Download Detailed Analysis (JSON)",
            data=analysis_json,
            file_name=f"detailed_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        )
    # Debug outputs
    st.write('Filtered DataFrame after initial filters:', filtered_df)
    st.write('Qualified DataFrame after disqualification filter:', qualified_df)
    st.write('Disqualified DataFrame:', disqualified_df)

if __name__ == "__main__":
    main()
