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
            url = f"https://api.dataforsyningen.dk/adresser?q={sikker_adresse}&per_side=1"
            
            try:
                response = requests.get(url).json()
                
                if response and isinstance(response, list) and len(response) > 0:
                    api_data = response[0]
                    adgangsadresse = api_data.get("adgangsadresse", {})
                    koordinater = adgangsadresse.get("adgangspunkt", {}).get("koordinater", [12.5683371, 55.6760968])
                    
                    lng = float(koordinater[0])
                    lat = float(koordinater[1])
                    st.session_state.coords = [lat, lng]
                    
                    # ✅ Hent BBR-data (ejendomsdata) fra API'et
                    bbr_id = api_data.get("id", None)
                    etager = 2  # Standard værdi hvis BBR ikke findes
                    byg_type = "Parcelhus"  # Standard værdi
                    
                    if bbr_id:
                        try:
                            # Hent BBR-data baseret på adresse-ID
                            bbr_url = f"https://api.dataforsyningen.dk/bbr-data/{bbr_id}"
                            bbr_response = requests.get(bbr_url).json()
                            
                            if bbr_response:
                                # Hent etageantal fra BBR
                                etager = bbr_response.get("etager", 2)
                                
                                # Hent bygningstype
                                bygn_type = bbr_response.get("bygningstype", 0)
                                if bygn_type in [110, 111, 112]:  # Enfamiliehus
                                    byg_type = "Parcelhus"
                                elif bygn_type in [120, 121]:  # Tofamiliehus
                                    byg_type = "Tofamiliehus"
                                else:
                                    byg_type = "Erhverv / Lejlighed"
                        except:
                            # Hvis BBR-opslag fejler, brug standard værdier
                            pass
                    
                    # Beregn antal vinduer baseret på etager
                    antal_vinduer = 12 if etager == 1 else (12 * etager)
                    
                    pris_pr_rude_ude = 28
                    pris_pr_rude_begge = 58
                    etage_tillaeg = 35
                    
                    pris_ude_temp = (antal_vinduer * pris_pr_rude_ude) + ((etager - 1) * etage_tillaeg)
                    pris_begge_temp = (antal_vinduer * pris_pr_rude_begge) + ((etager - 1) * etage_tillaeg * 1.8)
                    
                    # ✅ HALVER PRISERNE TO GANGE OG GØR DEM DEREFTER 25% HØJERE
                    st.session_state.pris_ude = ((pris_ude_temp / 2) / 2) * 1.25
                    st.session_state.pris_begge = ((pris_begge_temp / 2) / 2) * 1.25
                    
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
    hoved_hjemmeside = "https://vinduespudsning-app-elrcdizplonssjmnempviq.streamlit.app/"
    
    qr = QRCode(version=1, box_size=10, border=4)
    qr.add_data(hoved_hjemmeside)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    st.image(buf.getvalue(), caption="Scan QR-koden for at gå til prisberegneren")
    
    st.download_button(
        label="⬇️ Download QR-kode",
        data=buf.getvalue(),
        file_name="vinduespudsning_hjemmeside_qr.png",
        mime="image/png",
        key="qr_download"
    )
