import streamlit as st
import qrcode
from io import BytesIO
import re

# --- FUNKCIJE ---
def ocisti_racun(racun):
    samo_cifre = re.sub(r'\D', '', racun)
    return samo_cifre.zfill(18)

# --- KONFIGURACIJA ---
st.set_page_config(page_title="Nesha_split ®", layout="wide")

# Dodajemo samo tvoj (R) diskretno u ugao, bez kvarenja boja
st.markdown("""
    <style>
    .reomirano-znak {
        position: fixed;
        top: 10px;
        right: 80px;
        font-size: 1.5rem;
        color: rgba(0,0,0,0.2);
        font-weight: bold;
        border: 1px solid rgba(0,0,0,0.1);
        border-radius: 50%;
        width: 35px;
        height: 35px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    </style>
    <div class="reomirano-znak">R</div>
    """, unsafe_allow_html=True)

# KLJUČ ZA RESET
if "reset_kljuc" not in st.session_state:
    st.session_state.reset_kljuc = 0

# --- SIDEBAR: PODEŠAVANJA ---
st.sidebar.header("⚙️ Podešavanja")
moje_ime = st.sidebar.text_input("Tvoje ime:", value="", key="user_name")
moj_racun = st.sidebar.text_input("Tvoj račun:", value="", key="user_bank")

st.sidebar.divider()
st.sidebar.header("👥 Ekipa")

if 'clanovi_univerzalni' not in st.session_state:
    st.session_state.clanovi_univerzalni = []

def dodaj_clana():
    ime = st.session_state.novo_ime_input.strip()
    if ime and ime not in st.session_state.clanovi_univerzalni:
        st.session_state.clanovi_univerzalni.append(ime)
    st.session_state.novo_ime_input = ""

st.sidebar.text_input("Dodaj člana:", key="novo_ime_input", on_change=dodaj_clana)

sortirani_clanovi = sorted(st.session_state.clanovi_univerzalni)
for ime in sortirani_clanovi:
    col_p, col_b = st.sidebar.columns([4, 1])
    col_p.write(f"👤 {ime}")
    if col_b.button("✖", key=f"del_{ime}"):
        st.session_state.clanovi_univerzalni.remove(ime)
        st.rerun()

# --- GLAVNI PANEL ---
st.title("💰 Nesha_split System ®")
st.write(f"Novac ide na: **{moje_ime}** | Račun: **{moj_racun}**")
st.divider()

sufiks = st.session_state.reset_kljuc
col_levo, col_desno = st.columns([1, 1])

with col_levo:
    st.subheader("📸 Račun")
    fajl = st.file_uploader("Otpremi sliku", type=['jpg', 'jpeg', 'png'], key=f"fajl_{sufiks}")
    if fajl:
        st.image(fajl, use_container_width=True)

with col_desno:
    if st.button("🔄 Novi unos (Reset)", use_container_width=True):
        st.session_state.reset_kljuc += 1
        st.rerun()
    
    st.subheader("✍️ Podaci")
    c1, c2 = st.columns(2)
    iznos_racuna = c1.number_input("Iznos (RSD):", min_value=0.0, step=10.0, value=None, key=f"r_{sufiks}")
    dostava = c2.number_input("Dostava (RSD):", min_value=0.0, step=10.0, value=None, key=f"d_{sufiks}")

    suma_ukupno = (iznos_racuna or 0) + (dostava or 0)
    st.markdown(f"### Ukupno za deljenje: {suma_ukupno:.2f} RSD")

    st.checkbox("Odaberi sve", key=f"sve_{sufiks}", on_change=lambda: st.session_state.update({f"ucesnici_{sufiks}": sortirani_clanovi if st.session_state[f"sve_{sufiks}"] else []}))
    odabrani = st.multiselect("Ko učestvuje:", options=sortirani_clanovi, key=f"ucesnici_{sufiks}")
    nacin = st.radio("Metoda:", ["Ravnopravno", "Ručni unos"], horizontal=True, key=f"nacin_{sufiks}")

    finalni_dugovi = {}
    if odabrani:
        if nacin == "Ravnopravno":
            po_osobi = suma_ukupno / len(odabrani)
            st.success(f"Svako plaća po: {po_osobi:.2f} RSD")
            for o in odabrani: finalni_dugovi[o] = po_osobi
        else:
            for o in odabrani:
                finalni_dugovi[o] = st.number_input(f"Iznos za {o}:", min_value=0.0, key=f"ruc_{o}_{sufiks}")

st.divider()

if odabrani and st.button("🔥 GENERIŠI QR KODOVE", use_container_width=True, type="primary"):
    if not moje_ime or not moj_racun:
        st.error("⚠️ Unesi svoje ime i račun u sidebar levo!")
    else:
        c_racun = ocisti_racun(moj_racun)
        qr_cols = st.columns(3)
        for i, (ime, dug) in enumerate(finalni_dugovi.items()):
            if dug and dug > 0:
                iz_fmt = "{:.2f}".format(dug).replace('.', ',')
                ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Rucak-{ime}"
                qr_img = qrcode.make(ips_data)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                with qr_cols[i % 3]:
                    st.write(f"**{ime}**")
                    st.image(buf.getvalue(), width=150)
                    st.write(f"{dug:.2f} RSD")
