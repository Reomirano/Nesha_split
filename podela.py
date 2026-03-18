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

# --- SIDEBAR: OSNOVNI PODACI ---
st.sidebar.markdown("*<span style='font-size: 0.8rem; color: gray;'>powered by Reomirano</span>*", unsafe_allow_html=True)
st.sidebar.header("⚙️ Tvoji podaci")
moje_ime = st.sidebar.text_input("Administrator (Ime i prezime):", value="", key="user_name", placeholder="Npr. Marko Marković")
moj_racun = st.sidebar.text_input("Broj tekućeg računa:", value="", key="user_bank", placeholder="170...")

# --- GLAVNI PANEL ---
st.title("💰 Podela troškova")
st.caption(f"Novac leže na: **{moje_ime if moje_ime else '...'}** | Račun: **{moj_racun if moj_racun else '...'}**")
st.divider()

sufiks = st.session_state.reset_kljuc
col_levo, col_desno = st.columns([1, 1.2])

with col_levo:
    st.subheader("📸 Račun")
    fajl = st.file_uploader("Otpremi sliku", type=['jpg', 'jpeg', 'png'], key=f"fajl_{sufiks}")
    if fajl:
        st.image(fajl, use_container_width=True)

with col_desno:
    if st.button("🔄 Novi unos / Reset", use_container_width=True):
        st.session_state.reset_kljuc += 1
        st.rerun()
    
    st.subheader("✍️ Unos iznosa")
    c1, c2 = st.columns(2)
    
    # FIX: Postavljamo value=0.0 da izbegnemo NoneType grešku
    iznos_racuna = c1.number_input("Iznos sa računa (RSD):", min_value=0.0, step=10.0, value=0.0, key=f"racun_{sufiks}")
    dostava = c2.number_input("Cena dostave (RSD):", min_value=0.0, step=10.0, value=0.0, key=f"dostava_{sufiks}")

    ukupno = iznos_racuna + dostava
    st.markdown(f"### Ukupno: {ukupno:.2f} RSD")
    st.divider()

    nacin = st.radio("Metoda podele:", ["Ravnopravno", "Ručni unos (po kolegama)"], horizontal=True, key=f"nacin_{sufiks}")

    finalni_dugovi = {}
    validna_podela = False

    # --- SCENARIO 1: RAVNOPRAVNO ---
    if nacin == "Ravnopravno":
        broj_ljudi = st.number_input("Ukupan broj osoba (uključujući i tebe):", min_value=1, value=2, step=1)
        if broj_ljudi > 1:
            po_osobi = ukupno / broj_ljudi
            st.info(f"Svako treba da ti uplati po: **{po_osobi:.2f} RSD**")
            finalni_dugovi["Zajednički kod"] = po_osobi
            validna_podela = True
        else:
            st.warning("Broj osoba mora biti veći od 1.")

    # --- SCENARIO 2: RUČNI UNOS ---
    else:
        st.write("---")
        # UPRAVLJANJE KOLEGAMA DIREKTNO OVDE
        if 'clanovi_univerzalni' not in st.session_state:
            st.session_state.clanovi_univerzalni = []

        def dodaj_clana_u_hodu():
            ime = st.session_state.novo_ime_temp.strip()
            if ime and ime not in st.session_state.clanovi_univerzalni:
                st.session_state.clanovi_univerzalni.append(ime)
            st.session_state.novo_ime_temp = ""

        st.text_input("Dodaj kolegu na listu:", key="novo_ime_temp", on_change=dodaj_clana_u_hodu, placeholder="Upiši ime i pritisni Enter")
        
        if st.session_state.clanovi_univerzalni:
            odabrani = st.multiselect("Ko učestvuje u ovom računu:", options=sorted(st.session_state.clanovi_univerzalni), key=f"ucesnici_{sufiks}")
            
            if odabrani:
                trenutna_suma = 0.0
                for o in odabrani:
                    dug = st.number_input(f"Iznos za člana {o}:", min_value=0.0, step=10.0, value=0.0, key=f"rucni_{o}_{sufiks}")
                    finalni_dugovi[o] = dug
                    trenutna_suma += dug
                
                ostatak = ukupno - trenutna_suma
                if ostatak > 0.01:
                    st.warning(f"Preostalo: **{ostatak:.2f} RSD**")
                elif ostatak < -0.01:
                    st.error(f"Prešišali ste račun za: **{abs(ostatak):.2f} RSD**")
                else:
                    st.success("Sve se uklapa! Možeš generisati kodove.")
                    validna_podela = True
            
            if st.button("Obriši listu svih kolega", type="secondary"):
                st.session_state.clanovi_univerzalni = []
                st.rerun()

# --- QR SEKCIJA ---
st.divider()
if validna_podela and ukupno > 0:
    if st.button("🔥 GENERIŠI QR KODOVE", use_container_width=True, type="primary"):
        if not moje_ime or not moj_racun:
            st.error("⚠️ Popuni svoje podatke (gore levo) pre generisanja!")
        else:
            c_racun = ocisti_racun(moj_racun)
            
            if nacin == "Ravnopravno":
                dug = finalni_dugovi["Zajednički kod"]
                iz_fmt = "{:.2f}".format(dug).replace('.', ',')
                ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Podela racuna"
                qr_img = qrcode.make(ips_data)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                
                _, col_qr, _ = st.columns([1, 1, 1])
                with col_qr:
                    st.image(buf.getvalue(), caption=f"Iznos po osobi: {dug:.2f} RSD", use_container_width=True)
            else:
                qr_cols = st.columns(5)
                for i, (ime, dug) in enumerate(finalni_dugovi.items()):
                    if dug > 0:
                        iz_fmt = "{:.2f}".format(dug).replace('.', ',')
                        ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Rucak-{ime}"
                        qr_img = qrcode.make(ips_data)
                        buf = BytesIO()
                        qr_img.save(buf, format="PNG")
                        with qr_cols[i % 5]:
                            st.markdown(f"**{ime}**")
                            st.image(buf.getvalue(), width=130)
                            st.caption(f"{dug:.2f} RSD")

st.caption("<br><br>*Aplikacija služi samo za lakše generisanje IPS koda. Proverite podatke pre potvrde uplate.*", unsafe_allow_html=True)
