import streamlit as st
import folium
from streamlit_folium import st_folium
from qrcode import QRCode
from io import BytesIO
import requests
import urllib.parse

st.set_page_config(page_title="Vinduespudsning Beregner", layout="centered")
st.title("🚗 Vinduespudsning Prisberegner")
st.write("Indtast din adresse for at hente reelle BBR-data og beregne pris")

# Opret appens hukommelse, hvis den ikke findes
if "beregnet" not in st.session_state:
    st.session_state.beregnet = False
    st.session_state.bbr = None
    st.session_state.pris_ude = 0
    st.session_state.pris_begge = 0
    st.session_state.coords = [55.6760968, 12.5683371]

adresse = st.text_input("Adresse", placeholder="f.eks. Rosenvej 12, 2800 Lyngby")

if st.button("🔍 Beregn pris", type="primary"):
    if adresse:
        with st.spinner("Forbinder til BBR og henter live data..."):
            # 1. Slå adressen op hos DAWA med sikker URL-kodning
            sikker_adresse = urllib.parse.quote(adresse)
            url = f"https://dataforsyningen.dk{sikker_adresse}&per_side=1"
            
            try:
                response = requests.get(url).json()
                
                if response and isinstance(response, list) and len(response) > 0:
                    api_data = response[0]  # Tag fat i den første adresse i listen
                    adgangsadresse = api_data.get("adgangsadresse", {})
                    adgangsadresse_id = adgangsadresse.get("id")
                    
                    # DAWA returnerer [Længde, Bredde]. Folium og kort skal bruge [Bredde, Længde]
                    koordinater = adgangsadresse.get("adgangspunkt", {}).get("koordinater", [12.5683371, 55.6760968])
                    st.session_state.coords = [koordinater[1], koordinater[0]]
                    
                    # 2. Hent BBR-data via det rigtige bbrlight-endpoint hos Dataforsyningen
                    bbr_url = f"https://dataforsyningen.dk{adgangsadresse_id}"
                    bbr_response = requests.get(bbr_url).json()
                    
                    # Standardværdier hvis registeret fejler eller er tomt
                    areal = 135
                    etager = 1
                    bygningstype = "Parcelhus"
                    
                    if bbr_response and isinstance(bbr_response, list) and len(bbr_response) > 0:
                        bygning_data = bbr_response[0]
                        # Hent det bebyggede areal eller det samlede areal fra BBR
                        areal = bygning_data.get("bebyggetAreal", bygning_data.get("samletBygningsareal", 135))
                        etager = bygning_data.get("antalEtager", 1)
                        if not etager or etager < 1:
                            etager = 1
                    
                    # 3. Beregn estimeret antal vinduer (industristandard: 1 vindue pr. 6 kvm)
                    antal_vinduer = max(10, round(areal / 6))
                    
                    # Prisstruktur
                    pris_pr_rude_ude = 28
                    pris_pr_rude_begge = 58
                    etage_tillaeg = 35
                    
                    # Udregning baseret på BBR data
                    st.session_state.pris_ude = (antal_vinduer * pris_pr_rude_ude) + ((etager - 1) * etage_tillaeg)
                    st.session_state.pris_begge = (antal_vinduer * pris_pr_rude_begge) + ((etager - 1) * etage_tillaeg * 1.8)
                    
                    st.session_state.bbr = {
                        "adresse": api_data.get("adressebetegnelse", adresse),
                        "bygningsareal": areal,
                        "etager": etager,
                        "bygningstype": bygningstype,
                        "antal_vinduer_est": antal_vinduer
                    }
                    st.session_state.beregnet = True
                else:
                    st.error("Kunne ikke finde adressen. Tjek venligst stavningen.")
                    st.session_state.beregnet = False
            except Exception as e:
                st.error("Der opstod en fejl under synkronisering med BBR-registret.")
                st.session_state.beregnet = False
    else:
        st.error("Indtast venligst en adresse")

# Vis resultaterne permanent på skærmen efter beregning
if st.session_state.beregnet and st.session_state.bbr:
    st.success("✅ Officielle BBR-data indlæst!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Udvendig pudsning", f"{int(st.session_state.pris_ude):,} kr")
    with col2:
        st.metric("Ude + Indvendig", f"{int(st.session_state.pris_begge):,} kr")
        
    st.subheader("Officielle BBR-oplysninger")
    st.write(f"🏠 **Bygningsareal:** {st.session_state.bbr['bygningsareal']} m²")
    st.write(f"🏢 **Antal etager:** {st.session_state.bbr['etager']}")
    st.write(f"🧽 **Estimeret antal ruder ud fra m²:** {st.session_state.bbr['antal_vinduer_est']} stk.")
    st.write(f"📍 **Adresse:** {st.session_state.bbr['adresse']}")
    
    st.subheader("🗺️ Google Earth / Satellitvisning")
    # Integrerer Google Earth/Maps satellitvisning direkte i kortet
    m = folium.Map(location=st.session_state.coords, zoom_start=19, max_zoom=22)
    google_earth_tiles = "https://google.com{x}&y={y}&z={z}"
    folium.TileLayer(
        tiles=google_earth_tiles,
        attr="Google",
        name="Google Satellit",
        overlay=False,
        control=True
    ).add_to(m)
    folium.Marker(st.session_state.coords, popup=st.session_state.bbr["adresse"]).add_to(m)
    st_folium(m, width=700, height=350, key="google_earth_visning")
    
    st.subheader("📱 QR-kode til din bil (Linker til din forside)")
    hoved_hjemmeside = "https://streamlit.app"
    
    qr = QRCode(version=1, box_size=10, border=4)
    qr.add_data(hoved_hjemmeside)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Scan QR-koden for at gå til prisberegneren")
    
    st.download_button(
        label="⬇️ Download QR-kode",
        data=buf.getvalue(),
        file_name="vinduespudsning_hjemmeside_qr.png",
        mime="image/png",
        key="qr_download"
    )