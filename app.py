import streamlit as st
import folium
from streamlit_folium import st_folium
from qrcode import QRCode
from io import BytesIO
import requests
import urllib.parse

st.set_page_config(page_title="Vinduespudsning Beregner", layout="centered")
st.title("🚗 Vinduespudsning Prisberegner")
st.write("Indtast din adresse for at få pris og kortvisning")

# Opret hukommelse i appen, hvis den ikke findes endnu
if "beregnet" not in st.session_state:
    st.session_state.beregnet = False
    st.session_state.bbr = None
    st.session_state.pris_ude = 0
    st.session_state.pris_begge = 0
    st.session_state.coords = [55.6760968, 12.5683371] # Standard København

adresse = st.text_input("Adresse", placeholder="f.eks. Rosenvej 12, 2800 Lyngby")

if st.button("🔍 Beregn pris", type="primary"):
    if adresse:
        with st.spinner("Henter live data og beregner..."):
            # 1. Slå adressen op hos DAWA med sikker URL-kodning
            sikker_adresse = urllib.parse.quote(adresse)
            url = f"https://dataforsyningen.dk{sikker_adresse}&per_side=1"
            
            try:
                response = requests.get(url).json()
                
                # SIKRING: Tjek at DAWA faktisk fandt og returnerede en liste med adresser
                if response and isinstance(response, list) and len(response) > 0:
                    api_data = response[0]  # Tag fat i den første og mest præcise adresse på listen
                    adgangsadresse = api_data.get("adgangsadresse", {})
                    koordinater = adgangsadresse.get("adgangspunkt", {}).get("koordinater", [12.5683371, 55.6760968])
                    
                    # DAWA sender [længdegrad, breddegrad]. Folium kræver [breddegrad, længdegrad] -> Vend dem om!
                    st.session_state.coords = [koordinater[1], koordinater[0]]
                    
                    # 2. Opsæt data baseret på den officielle adressebetegnelse
                    st.session_state.bbr = {
                        "adresse": api_data.get("adressebetegnelse", adresse),
                        "bygningsareal": 142,
                        "etager": 1 if "st" in adresse.lower() else 2,
                        "bygningstype": "Parcelhus",
                        "antal_vinduer_est": 22
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
                    st.error("Kunne ikke finde adressen i systemet. Tjek venligst stavningen.")
                    st.session_state.beregnet = False
            except Exception as e:
                st.error("Der opstod en systemfejl ved indlæsning af adressedata.")
                st.session_state.beregnet = False
    else:
        st.error("Indtast venligst en adresse")

# Hvis der er beregnet noget, så vis resultatet permanent på skærmen
if st.session_state.beregnet and st.session_state.bbr:
    st.success("✅ Beregning færdig!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Udvendig pudsning", f"{st.session_state.pris_ude:,} kr")
    with col2:
        st.metric("Ude + Indvendig", f"{int(st.session_state.pris_begge):,} kr")
        
    st.subheader("Adresseoplysninger")
    st.write(f"**Fundet adresse:** {st.session_state.bbr['adresse']}")
    
    # Det levende kort centrerer nu automatisk på den rigtige adresse
    m = folium.Map(location=st.session_state.coords, zoom_start=17)
    folium.Marker(st.session_state.coords, popup=st.session_state.bbr["adresse"]).add_to(m)
    st_folium(m, width=700, height=300, key="kort_visning")
    
    st.subheader("📱 QR-kode til bilen")
    qr_data = "https://streamlit.app"
    
    qr = QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Scan for at besøge siden")
    
    st.download_button(
        label="⬇️ Download QR-kode",
        data=buf.getvalue(),
        file_name="qr_kode.png",
        mime="image/png",
        key="qr_download"
    )