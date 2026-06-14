import streamlit as st
import folium
from streamlit_folium import st_folium
from qrcode import QRCode
from io import BytesIO
import requests
import urllib.parse

st.set_page_config(page_title="Vinduespudsning Beregner", layout="centered")
st.title("🚗 Vinduespudsning Prisberegner")
st.write("Indtast din adresse for at få prisestimat og satellitvisning")

if "beregnet" not in st.session_state:
    st.session_state.beregnet = False
    st.session_state.bbr = None
    st.session_state.pris_ude = 0
    st.session_state.pris_begge = 0
    st.session_state.coords = [55.6760968, 12.5683371]

adresse = st.text_input("Adresse", placeholder="f.eks. Rosenvej 12, 2800 Lyngby")

if st.button("🔍 Beregn pris", type="primary"):
    if adresse:
        with st.spinner("Slår adresse op..."):
            sikker_adresse = urllib.parse.quote(adresse)
            url = f"https://dataforsyningen.dk/rest/adresser?q={sikker_adresse}&per_side=1"
            
            try:
                response = requests.get(url).json()
                
                if response and isinstance(response, list) and len(response) > 0:
                    api_data = response[0]
                    adgangsadresse = api_data.get("adgangsadresse", {})
                    koordinater = adgangsadresse.get("adgangspunkt", {}).get("koordinater", [12.5683371, 55.6760968])
                    
                    # HER ER DEN RIGTIGE RETTELSE: Vi henter tallene via rå indeks [0] og [1] direkte fra listen
                    lng = float(koordinater[0])
                    lat = float(koordinater[1])
                    st.session_state.coords = [lat, lng]
                    
                    byg_type = "Erhverv / Lejlighed" if "st" in adresse.lower() or "th" in adresse.lower() else "Parcelhus"
                    etager = 1 if "st" in adresse.lower() else 2
                    antal_vinduer = 12 if etager == 1 else 24
                    
                    pris_pr_rude_ude = 28
                    pris_pr_rude_begge = 58
                    etage_tillaeg = 35
                    
                    st.session_state.pris_ude = (antal_vinduer * pris_pr_rude_ude) + ((etager - 1) * etage_tillaeg)
                    st.session_state.pris_begge = (antal_vinduer * pris_pr_rude_begge) + ((etager - 1) * etage_tillaeg * 1.8)
                    
                    st.session_state.bbr = {
                        "adresse": api_data.get("adressebetegnelse", adresse),
                        "etager": etager,
                        "bygningstype": byg_type,
                        "antal_vinduer_est": antal_vinduer
                    }
                    st.session_state.beregnet = True
                else:
                    st.error("Kunne ikke finde adressen.")
                    st.session_state.beregnet = False
            except Exception as e:
                st.error("Der opstod en fejl under indlæsning af adressedata.")
                st.session_state.beregnet = False
    else:
        st.error("Indtast venligst en adresse")

if st.session_state.beregnet and st.session_state.bbr:
    st.success("✅ Prisberegning fuldført!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Udvendig pudsning", f"{int(st.session_state.pris_ude):,} kr")
    with col2:
        st.metric("Ude + Indvendig", f"{int(st.session_state.pris_begge):,} kr")
        
    st.subheader("Estimeret datagrundlag")
    st.write(f"🏢 **Antal etager:** {st.session_state.bbr['etager']}")
    st.write(f"🧽 **Anslået antal ruder:** {st.session_state.bbr['antal_vinduer_est']} stk.")
    st.write(f"📍 **Adresse:** {st.session_state.bbr['adresse']}")
    
    st.subheader("🗺️ Google Earth / Satellitvisning")
    m = folium.Map(location=st.session_state.coords, zoom_start=19, max_zoom=22)
    google_earth_tiles = "https://mt.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
    folium.TileLayer(
        tiles=google_earth_tiles,
        attr="Google",
        name="Google Satellit",
        overlay=False,
        control=True
    ).add_to(m)
    folium.Marker(st.session_state.coords, popup=st.session_state.bbr["adresse"]).add_to(m)
    st_folium(m, width=700, height=350, key="google_earth_visning")
    
    st.subheader("📱 QR-kode til din bil")
    hoved_hjemmeside = "https://streamlit.app"
    qr.add_data(hoved_hjemmeside)
    
    qr = QRCode(version=1, box_size=10, border=4)
    qr.add_data(hoved_hjemmeside)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
   buf = BytesIO()
   img.save(buf, format="PNG")
   buf.seek(0)  # ← Add this
   st.image(buf.getvalue(), ...)
    
    st.download_button(
        label="⬇️ Download QR-kode",
        data=buf.getvalue(),
        file_name="vinduespudsning_hjemmeside_qr.png",
        mime="image/png",
        key="qr_download"
    )