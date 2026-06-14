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
                response = requests.get(url, timeout=5).json()
                
                if response and isinstance(response, list) and len(response) > 0:
                    api_data = response[0]
                    adgangsadresse = api_data.get("adgangsadresse", {})
                    koordinater = adgangsadresse.get("adgangspunkt", {}).get("koordinater", [12.5683371, 55.6760968])
                    
                    lng = float(koordinater[0])
                    lat = float(koordinater[1])
                    st.session_state.coords = [lat, lng]
                    
                    # ✅ Hent BBR-data via husnummerkode (mere reliable)
                    husnummerkode = api_data.get("husnummerkode", None)
                    etager = 2  # Standard værdi hvis BBR ikke findes
                    byg_type = "Parcelhus"  # Standard værdi
                    antal_vinduer = 24
                    debug_info = []
                    
                    if husnummerkode:
                        try:
                            # Alternativ 1: Prøv at hente via husnummer
                            bbr_url = f"https://api.dataforsyningen.dk/bbr?husnummerkode={husnummerkode}"
                            bbr_response = requests.get(bbr_url, timeout=5).json()
                            debug_info.append(f"✅ BBR husnummer API svar: {len(bbr_response)} records")
                            
                            if bbr_response and len(bbr_response) > 0:
                                bbr_data = bbr_response[0]
                                
                                # Hent etageantal
                                if "etager" in bbr_data:
                                    etager = int(bbr_data.get("etager", 2))
                                    debug_info.append(f"✅ Etager fra BBR: {etager}")
                                
                                # Hent bygningstype
                                if "bbrkodenavn" in bbr_data:
                                    bbr_kode = bbr_data.get("bbrkodenavn", "").lower()
                                    if "enfamilie" in bbr_kode or "villa" in bbr_kode:
                                        byg_type = "Parcelhus"
                                    elif "tofamilie" in bbr_kode:
                                        byg_type = "Tofamiliehus"
                                    else:
                                        byg_type = "Erhverv / Lejlighed"
                                    debug_info.append(f"✅ Bygningstype: {byg_type}")
                        except Exception as e:
                            debug_info.append(f"⚠️ BBR husnummer fejl: {str(e)}")
                            
                            # Alternativ 2: Prøv vejkodenavn
                            try:
                                vejkode = adgangsadresse.get("vejkode", None)
                                husnr = api_data.get("husnr", None)
                                if vejkode and husnr:
                                    bbr_url2 = f"https://api.dataforsyningen.dk/bbr?vejkode={vejkode}&husnr={husnr}"
                                    bbr_response2 = requests.get(bbr_url2, timeout=5).json()
                                    debug_info.append(f"✅ BBR vejkode API svar: {len(bbr_response2)} records")
                                    
                                    if bbr_response2 and len(bbr_response2) > 0:
                                        bbr_data2 = bbr_response2[0]
                                        etager = int(bbr_data2.get("etager", 2))
                                        debug_info.append(f"✅ Etager fra BBR (vejkode): {etager}")
                            except Exception as e2:
                                debug_info.append(f"⚠️ BBR vejkode fejl: {str(e2)}")
                    
                    # Beregn antal vinduer baseret på etager
                    antal_vinduer = 12 if etager == 1 else (12 * etager)
                    debug_info.append(f"📊 Antal vinduer beregnet: {antal_vinduer} (baseret på {etager} etager)")
                    
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
                        "antal_vinduer_est": antal_vinduer,
                        "debug_info": debug_info
                    }
                    st.session_state.beregnet = True
                else:
                    st.error("Kunne ikke finde adressen.")
                    st.session_state.beregnet = False
            except requests.exceptions.Timeout:
                st.error("API opslag tog for lang tid - prøv igen")
                st.session_state.beregnet = False
            except Exception as e:
                st.error(f"Der opstod en fejl: {str(e)}")
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
    
    # ✅ DEBUG INFO
    with st.expander("🔧 Debug Information"):
        for info in st.session_state.bbr.get("debug_info", []):
            st.write(info)
    
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
