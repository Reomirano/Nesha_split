import streamlit as st
import qrcode
from io import BytesIO
import re

# --- FUNKCIJE ---
def ocisti_racun(racun):
    samo_cifre = re.sub(r'\D', '', racun)
    return samo_cifre.zfill(18)

# --- KONFIGURACIJA ---
st.set_page_config(page_title="Podela troškova", layout="wide")

# KLJUČ ZA RESET
if "reset_kljuc" not in st.session_state:
    st.session_state.reset_kljuc = 0

# --- SIDEBAR: PODEŠAVANJA ---
# MALI DISKRETNI POTPIS (ITALLIC I SVEDEN)
st.sidebar.markdown("*<span style='font-size: 0.8rem; color: gray;'>powered by Reomirano</span>*", unsafe_allow_html=True)

st.sidebar.header("⚙️ Tvoja Podešavanja")
st.sidebar.info("Ovi podaci se koriste za generisanje QR koda kako bi novac bio uplaćen na ispravan račun.")

moje_ime = st.sidebar.text_input("Tvoje ime i prezime:", value="", key="user_name", placeholder="ime i prezime vlasnika računa")
moj_racun = st.sidebar.text_input("Tvoj Broj Računa:", value="", key="user_bank", placeholder="18-ocifreni broj tekućeg računa")

st.sidebar.divider()
st.sidebar.header("👥 Tvoje kolege")

if 'clanovi_univerzalni' not in st.session_state:
    st.session_state.clanovi_univerzalni = []

def dodaj_clana():
    ime = st.session_state.novo_ime_input.strip()
    if ime and ime not in st.session_state.clanovi_univerzalni:
        st.session_state.clanovi_univerzalni.append(ime)
    st.session_state.novo_ime_input = ""

st.sidebar.text_input("Dodaj člana:", key="novo_ime_input", on_change=dodaj_clana)

if st.sidebar.button("Obriši sve članove"):
    st.session_state.clanovi_univerzalni = []
    st.rerun()

sortirani_clanovi = sorted(st.session_state.clanovi_univerzalni)
for ime in sortirani_clanovi:
    col_p, col_b = st.sidebar.columns([4, 1])
    col_p.write(f"👤 {ime}")
    if col_b.button("✖", key=f"del_{ime}"):
        st.session_state.clanovi_univerzalni.remove(ime)
        st.rerun()

# --- GLAVNI PANEL ---
st.title("💰 Podela troškova")
st.caption(f"Novac se uplaćuje na ime: **{moje_ime}** | Račun: **{moj_racun}**")
st.divider()

sufiks = st.session_state.reset_kljuc
col_levo, col_desno = st.columns([1, 1])

with col_levo:
    st.subheader("📸 Račun")
    fajl = st.file_uploader("Otpremi sliku", type=['jpg', 'jpeg', 'png'], key=f"fajl_{sufiks}")
    if fajl:
        st.image(fajl, use_container_width=True)

with col_desno:
    if st.button("🔄 Novi unos", use_container_width=True, type="primary"):
        st.session_state.reset_kljuc += 1
        st.rerun()
    
    st.subheader("✍️ Podaci")
    col_iznos, col_dostava = st.columns(2)
    with col_iznos:
        iznos_racuna = st.number_input("Iznos sa računa (RSD):", min_value=0.0, step=10.0, value=None, placeholder="0.00", key=f"racun_{sufiks}")
    with col_dostava:
        dostava = st.number_input("Dostava (RSD):", min_value=0.0, step=10.0, value=None, placeholder="0.00", key=f"dostava_{sufiks}")

    v_racun = iznos_racuna if iznos_racuna is not None else 0.0
    v_dostava = dostava if dostava is not None else 0.0
    suma_ukupno = v_racun + v_dostava

    st.markdown(f"### Ukupno: {suma_ukupno:.2f} RSD")

    def promenuo_sve():
        check_kljuc = f"sve_{sufiks}"
        multi_kljuc = f"ucesnici_{sufiks}"
        if st.session_state[check_kljuc]:
            st.session_state[multi_kljuc] = sortirani_clanovi
        else:
            st.session_state[multi_kljuc] = []

    st.checkbox("Odaberi sve učesnike", key=f"sve_{sufiks}", on_change=promenuo_sve)
    
    odabrani = st.multiselect("Ko učestvuje:", options=sortirani_clanovi, key=f"ucesnici_{sufiks}")
    nacin = st.radio("Metoda:", ["Ravnopravno", "Ručni unos"], horizontal=True, key=f"nacin_{sufiks}")

    finalni_dugovi = {}
    if odabrani:
        if nacin == "Ravnopravno":
            po_osobi = suma_ukupno / len(odabrani) if len(odabrani) > 0 else 0
            st.info(f"Po osobi: **{po_osobi:.2f} RSD**")
            for o in odabrani:
                finalni_dugovi[o] = po_osobi
        else:
            for o in odabrani:
                finalni_dugovi[o] = st.number_input(
                    f"Iznos za člana {o}:", 
                    min_value=0.0, 
                    key=f"rucni_{o}_{sufiks}", 
                    value=None, 
                    placeholder="0.00"
                )

st.divider()

# --- QR SEKCIJA ---
if odabrani:
    if st.button("🔥 GENERIŠI QR KODOVE", use_container_width=True, type="primary"):
        if not moje_ime or not moj_racun:
            st.error("⚠️ Popunite svoje podatke u sidebar-u (levo)!")
        elif nacin == "Ručni unos" and any(v is None for v in finalni_dugovi.values()):
            st.error("⚠️ Niste uneli iznose za sve odabrane članove!")
        else:
            c_racun = ocisti_racun(moj_racun)
            qr_cols = st.columns(3) 
            for i, (ime, dug) in enumerate(finalni_dugovi.items()):
                if dug > 0:
                    iz_fmt = "{:.2f}".format(dug).replace('.', ',')
                    ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Rucak-{ime}"
                    qr_img = qrcode.make(ips_data)
                    buf = BytesIO()
                    qr_img.save(buf, format="PNG")
                    with qr_cols[i % 3]:
                        st.markdown(f"**{ime}**")
                        st.image(buf.getvalue(), width=160)
                        st.caption(f"{dug:.2f} RSD")
