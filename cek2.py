import streamlit as st
import pandas as pd
import re
from openai import OpenAI

# DeepSeek client
client = OpenAI(api_key=st.secrets["API_KEY"], base_url="https://api.deepseek.com")

@st.cache_data
def load_kamus():
    df = pd.read_excel('data_kamus_full_14-5-25.xlsx')
    df['LEMA'] = df['LEMA'].astype(str).str.lower()
    df['SUBLEMA'] = df['SUBLEMA'].astype(str).str.lower()
    df['SINONIM'] = df['SINONIM'].astype(str).str.lower()
    df['(HALUS/LOMA/KASAR)'] = df['(HALUS/LOMA/KASAR)'].astype(str).str.upper()

    return df

kamus_df = load_kamus()

# Kumpulan kata HALUS
halus_kata = set()
df_halus = kamus_df[kamus_df['(HALUS/LOMA/KASAR)'] == 'HALUS']
for col in ['LEMA', 'SUBLEMA']:
    split_col = df_halus[col].dropna().str.split(',')
    for row in split_col:
        halus_kata.update([k.strip() for k in row])

st.title("🟡 Deteksi & Konversi Kata HALUS ke LOMA")

user_input = st.text_area("Masukkan kalimat dalam Bahasa Sunda...", height=200)

if st.button("🔍 Deteksi & Konversi"):
    if user_input.strip():

        detected_halus = set()

        def highlight_and_detect(text):
            paragraphs = text.split('\n')
            highlighted_paragraphs = []

            for para in paragraphs:
                def replacer(match):
                    word = match.group(0)
                    core = re.sub(r"^[\"'.,!?;:()]*|[\"'.,!?;:()]*$", "", word).lower()
                    if core in halus_kata:
                        detected_halus.add(core)
                        return f"<span style='background-color: yellow'>{word}</span>"
                    else:
                        return word

                highlighted = re.sub(r"\b[\w\'\-]+[.,!?\"']*", replacer, para)
                highlighted_paragraphs.append(highlighted)

            return "<br>".join(highlighted_paragraphs)

        hasil_output = highlight_and_detect(user_input)

        st.markdown(f"<p style='font-size: 18px; line-height: 1.8'><strong>Highlight Output:</strong><br>{hasil_output}</p>", unsafe_allow_html=True)

        # 🔄 Transformasi HALUS ke LOMA
        def cari_loma_dari_sinonim(kata):
            sinonim_rows = kamus_df[kamus_df['SINONIM'].str.contains(rf'\b{kata}\b', na=False)]
            for _, row in sinonim_rows.iterrows():
                for kolom in ['LEMA', 'SUBLEMA']:
                    kandidat = row[kolom]
                    if pd.notna(kandidat):
                        for kata_kandidat in kandidat.split(','):
                            kata_kandidat = kata_kandidat.strip()
                            row_match = kamus_df[(kamus_df['LEMA'].str.contains(rf'\b{kata_kandidat}\b', na=False)) |
                                                 (kamus_df['SUBLEMA'].str.contains(rf'\b{kata_kandidat}\b', na=False))]
                            for _, row2 in row_match.iterrows():
                                if row2['(HALUS/LOMA/KASAR)'] == 'LOMA':
                                    return kata_kandidat
            return None

        def ubah_ke_loma_ai(kata):
            prompt = f"Ubah kata Sunda HALUS berikut menjadi versi LOMA (kasual): '{kata}'"
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for Sundanese language."},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )
            return response.choices[0].message.content.strip()

        st.markdown("### 🔄 Konversi Kata HALUS ke LOMA:")
        for kata in sorted(detected_halus):
            kata_loma = cari_loma_dari_sinonim(kata)
            if kata_loma:
                st.markdown(f"- **{kata}** → {kata_loma} (dari SINONIM → LOMA)")
            else:
                kata_ai = ubah_ke_loma_ai(kata)
                st.markdown(f"- **{kata}** → {kata_ai} (dibantu AI)")
                # 🔚 Membuat versi akhir teks: HALUS → LOMA (final cleaned version)
        final_output = user_input

        for kata in detected_halus:
            kata_loma = cari_loma_dari_sinonim(kata)
            if not kata_loma:
                kata_loma = ubah_ke_loma_ai(kata)

            # Ganti semua bentuk kata HALUS ke LOMA (menghormati tanda baca)
            final_output = re.sub(rf"\b{kata}\b", kata_loma, final_output, flags=re.IGNORECASE)

        st.markdown("---")
        st.markdown("### ✅ Teks Akhir (Sudah dalam bentuk LOMA):")
        st.markdown(f"<p style='font-size: 18px; line-height: 1.8'>{final_output}</p>", unsafe_allow_html=True)
    else:
        st.warning("Mohon masukkan kalimat terlebih dahulu.")
