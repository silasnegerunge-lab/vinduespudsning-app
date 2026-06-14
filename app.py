
import streamlit as st
import folium
from streamlit_folium import st_folium
from qrcode import QRCode
from io import BytesIO

st.set_page_config(page_title="Vinduespudsning Beregner", layout="centered")
st.title("🚗 Vinduespudsning Prisberegner")
st.write("Indtast en adresse for at få BBR-estimat og pris")

# Opret hukommelse i appen, hvis den ikke findes endnu
if "beregnet" not in st.session_state:
    st.session_state.beregnet = False
    st.session_state.bbr = None
    st.session_state.pris_ude = 0
    st.session_state.pris_begge = 0

adresse = st.text_input("Adresse", placeholder="f.eks. Rosenvej 12, 2800 Lyngby")

if st.button("🔍 Beregn pris", type="primary"):
    if adresse:
        with st.spinner("Henter data og beregner..."):
            st.session_state.bbr = {
                "adresse": adresse,
                "bygningsareal": 138,
                "etager": 2,
                "bygningstype": "Parcelhus",
                "antal_vinduer_est": 26
            }
            
            pris_pr_rude_ude = 28
            pris_pr_rude_begge = 58
            etage_tillaeg = 35
            
            antal = st.session_state.bbr["antal_vinduer_est"]
            etager = st.session_state.bbr["etager"]
            
            st.session_state.pris_ude = antal * pris_pr_rude_ude + (etager - 1) * etage_tillaeg
            st.session_state.pris_begge = antal * pris_pr_rude_begge + (etager - 1) * etage_tillaeg * 1.8
            st.session_state.beregnet = True
    else:
        st.error("Indtast venligst en adresse")

# Hvis der er beregnet noget, så bliv ved med at vise det på skærmen!
if st.session_state.beregnet:
    st.success("✅ Beregning færdig!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Udvendig pudsning", f"{st.session_state.pris_ude:,} kr")
    with col2:
        st.metric("Ude + Indvendig", f"{int(st.session_state.pris_begge):,} kr")
    
    st.subheader("BBR-oplysninger")
    st.json(st.session_state.bbr)
    
    m = folium.Map(location=[55.67, 12.57], zoom_start=15)
    folium.Marker([55.67, 12.57], popup=st.session_state.bbr["adresse"]).add_to(m)
    st_folium(m, width=700, height=300, key="kort_visning")
    
    st.subheader("📱 QR-kode til bilen")
    qr_data = f"Vinduespudsning tilbud\nAdresse: {st.session_state.bbr['adresse']}\nEst. pris ude: {st.session_state.pris_ude} kr"
    
    qr = QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Scan for tilbud")
    
    st.download_button(
        label=⬇️ Download QR-kode",
        data=buf.getvalue(),
        file_name="qr_kode.png",
        mime="image/png",
        key="qr_download"
    )
