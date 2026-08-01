"""Streamlit Web Application for FlashPDF Reader."""

from __future__ import annotations

import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import streamlit as st
from PIL import Image

# Ensure src/ is in Python path for Streamlit Cloud
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flashpdf.annotation_parser import (
    parse_answer_layers,
    parse_hide_actions,
    parse_speaker_annotations,
)
from flashpdf.asset_extractor import extract_embedded_assets
from flashpdf.pdf_renderer import PdfRenderer
from flashpdf.utils import default_cache_dir

st.set_page_config(
    page_title="FlashPDF Reader",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def qimage_to_pil(qimg) -> Image.Image:
    """Convert PySide6 QImage to PIL Image for Streamlit display."""
    qimg_rgb = qimg.convertToFormat(qimg.Format.Format_RGB888)
    width = qimg_rgb.width()
    height = qimg_rgb.height()
    ptr = qimg_rgb.bits()
    return Image.frombytes("RGB", (width, height), ptr.tobytes())


@st.cache_resource
def get_pdf_renderer() -> PdfRenderer:
    return PdfRenderer()


def load_pdf_data(pdf_path: Path):
    renderer = get_pdf_renderer()
    renderer.open(pdf_path)
    cache_dir = default_cache_dir(pdf_path)

    extracted_assets = extract_embedded_assets(pdf_path, cache_dir)
    assets = {asset.name: asset.path for asset in extracted_assets if asset.mime == "audio/mpeg"}

    speaker_annots = defaultdict(list)
    for annot in parse_speaker_annotations(pdf_path):
        speaker_annots[annot.page - 1].append(annot)

    answer_layers = defaultdict(list)
    for layer in parse_answer_layers(pdf_path):
        answer_layers[layer.page - 1].append(layer)

    hide_actions = defaultdict(list)
    for action in parse_hide_actions(pdf_path):
        hide_actions[action.page - 1].append(action)

    return renderer, assets, speaker_annots, answer_layers, hide_actions


def main() -> None:
    st.title("📖 FlashPDF Reader — Web Edition")
    st.caption("Interactive reader for Flash-embedded educational PDF textbooks")

    if "visible_answers" not in st.session_state:
        st.session_state.visible_answers = set()
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    # Sidebar: PDF Source Selection & Reader Settings
    st.sidebar.header("📁 Document & Settings")

    pdf_source = st.sidebar.radio(
        "PDF Source", ["Sample Textbooks", "Upload PDF"], index=0
    )

    pdf_path: Path | None = None

    if pdf_source == "Sample Textbooks":
        sample_files = sorted(Path(".").glob("*.pdf"))
        if sample_files:
            chosen_sample = st.sidebar.selectbox(
                "Select Textbook", [f.name for f in sample_files]
            )
            pdf_path = Path(chosen_sample)
        else:
            st.sidebar.info("No sample PDFs found in working directory.")
    else:
        uploaded = st.sidebar.file_uploader("Upload PDF File", type=["pdf"])
        if uploaded:
            temp_dir = Path(tempfile.gettempdir()) / "flashpdf_uploads"
            temp_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_dir / uploaded.name
            pdf_path.write_bytes(uploaded.getvalue())

    if not pdf_path or not pdf_path.exists():
        st.info("👈 Please select or upload a PDF textbook from the sidebar to begin reading.")
        return

    renderer, assets, speaker_annots, _answer_layers, hide_actions = load_pdf_data(pdf_path)
    total_pages = renderer.page_count

    if total_pages == 0:
        st.error("Could not load pages from PDF.")
        return

    st.sidebar.divider()
    st.sidebar.subheader("🎛 Controls & Display")

    # View Mode & Dark Mode
    view_mode = st.sidebar.radio("View Mode", ["Single Page", "Continuous Scroll"], index=0)
    dark_mode = st.sidebar.toggle("🌙 Smart Dark Mode", value=False)
    scale = st.sidebar.slider("Zoom Scale", min_value=0.5, max_value=2.5, value=1.25, step=0.25)

    # Page Navigation (Single Page Mode)
    if view_mode == "Single Page":
        st.session_state.current_page = st.sidebar.number_input(
            "Page Number",
            min_value=1,
            max_value=total_pages,
            value=min(st.session_state.current_page + 1, total_pages),
            step=1,
        ) - 1

    # Render Main View Layout
    col_main, col_interact = st.columns([3, 1.2])

    pages_to_render = range(total_pages) if view_mode == "Continuous Scroll" else [st.session_state.current_page]

    with col_main:
        for p_idx in pages_to_render:
            if view_mode == "Continuous Scroll":
                st.markdown(f"#### Page {p_idx + 1} of {total_pages}")

            qimg = renderer.render_page(
                p_idx,
                scale=scale,
                visible_answers=st.session_state.visible_answers,
                dark_mode=dark_mode,
            )
            pil_img = qimage_to_pil(qimg)
            st.image(pil_img, use_container_width=True)
            st.divider()

    with col_interact:
        curr = st.session_state.current_page
        st.subheader(f"⚡ Page {curr + 1} Interactivity")

        # 💡 Answer Layer Controls
        page_hides = hide_actions[curr]
        st.markdown("##### 💡 Answer Layers")
        if page_hides:
            for action in page_hides:
                target = action.target_field
                is_currently_visible = target in st.session_state.visible_answers

                label = f"❌ Hide '{target}'" if is_currently_visible else f"💡 Show '{target}'"
                if st.button(label, key=f"btn_{curr}_{target}_{action.hide}"):
                    if is_currently_visible:
                        st.session_state.visible_answers.discard(target)
                    else:
                        st.session_state.visible_answers.add(target)
                    st.rerun()
        else:
            st.caption("No hidden answer layers on this page.")

        st.divider()

        # 🔊 Speaker Audio Triggers
        st.markdown("##### 🔊 Audio Triggers")
        page_speakers = speaker_annots[curr]
        if page_speakers:
            for i, spk in enumerate(page_speakers, start=1):
                audio_file = assets.get(spk.audio)
                if audio_file and audio_file.exists():
                    label = f"Audio #{i} ({spk.audio})"
                    st.write(label)
                    st.audio(audio_file.read_bytes(), format="audio/mp3")
                else:
                    st.caption(f"Audio #{i}: {spk.audio} (asset missing)")
        else:
            st.caption("No audio triggers on this page.")

        st.divider()

        # 🎵 Audio Asset Inspector Expander
        with st.expander(f"🎵 All Extracted Audio ({len(assets)})"):
            for fname, fpath in assets.items():
                if fpath.exists():
                    st.write(f"**{fname}** ({fpath.stat().st_size // 1024} KB)")
                    st.audio(fpath.read_bytes(), format="audio/mp3")


if __name__ == "__main__":
    main()
