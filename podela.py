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
st.sidebar.markdown("*<span style='font-size: 0.8rem; color: gray;'>powered by Reomirano</span>*", unsafe_allow_html=True)
st.sidebar.header("⚙️ Podešavanja administratora")

moje_ime = st.sidebar.text_input("Ime i prezime primaoca:", value="", key="user_name")
moj_racun = st.sidebar.text_input("Broj računa (18 cifara):", value="", key="user_bank")

st.sidebar.divider()
st.sidebar.header("👥 Baza kolega")

if 'clanovi_univerzalni' not in st.session_state:
    st.session_state.clanovi_univerzalni = []

def dodaj_clana():
    ime = st.session_state.novo_ime_input.strip()
    if ime and ime not in st.session_state.clanovi_univerzalni:
        st.session_state.clanovi_univerzalni.append(ime)
    st.session_state.novo_ime_input = ""

st.sidebar.text_input("Dodaj kolegu u bazu:", key="novo_ime_input", on_change=dodaj_clana)

if st.sidebar.button("Obriši celu bazu"):
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
st.caption(f"Primalac: **{moje_ime if moje_ime else '---'}** | Račun: **{moj_racun if moj_racun else '---'}**")
st.divider()

sufiks = st.session_state.reset_kljuc
col_levo, col_desno = st.columns([1, 1.2])

with col_levo:
    st.subheader("📸 Slika računa")
    fajl = st.file_uploader("Otpremi račun", type=['jpg', 'jpeg', 'png'], key=f"fajl_{sufiks}")
    if fajl:
        st.image(fajl, use_container_width=True)

with col_desno:
    if st.button("🔄 Očisti sve unose", use_container_width=True):
        st.session_state.reset_kljuc += 1
        st.rerun()
    
    st.subheader("✍️ Finansije")
    c1, c2 = st.columns(2)
    iznos_racuna = c1.number_input("Iznos (RSD):", min_value=0.0, step=50.0, value=0.0, key=f"racun_{sufiks}")
    dostava = c2.number_input("Dostava (RSD):", min_value=0.0, step=10.0, value=0.0, key=f"dostava_{sufiks}")

    ukupno = iznos_racuna + dostava
    st.markdown(f"### Ukupno za naplatu: {ukupno:.2f} RSD")
    st.divider()

    nacin = st.radio("Kako delimo?", ["Ravnopravno (Svi isto)", "Ručni unos (Svako svoje)"], horizontal=True, key=f"nacin_{sufiks}")

    finalni_dugovi = {}
    validna_podela = False

    if nacin == "Ravnopravno (Svi isto)":
        broj_ljudi = st.number_input("Na koliko osoba delimo? (uključujući i tebe)", min_value=1, value=2, step=1)
        po_osobi = ukupno / broj_ljudi if broj_ljudi > 0 else 0
        st.info(f"Svaka osoba (osim tebe) treba da uplati: **{po_osobi:.2f} RSD**")
        
        # Generišemo jedan virtuelni unos za "Zajednički QR"
        if po_osobi > 0:
            finalni_dugovi["Zajednički kod"] = po_osobi
            validna_podela = True

    else:
        odabrani = st.multiselect("Ko učestvuje u ovom računu:", options=sortirani_clanovi, key=f"ucesnici_{sufiks}")
        if odabrani:
            st.write("Unesi iznose za kolege:")
            trenutna_suma = 0.0
            for o in odabrani:
                dug = st.number_input(f"Iznos za {o}:", min_value=0.0, step=10.0, value=0.0, key=f"rucni_{o}_{sufiks}")
                finalni_dugovi[o] = dug
                trenutna_suma += dug
            
            ostatak = ukupno - trenutna_suma
            
            if ostatak > 0.01:
                st.warning(f"⚠️ Preostalo za raspodelu: **{ostatak:.2f} RSD**")
            elif ostatak < -0.01:
                st.error(f"❌ Prebacili ste iznos za: **{abs(ostatak):.2f} RSD**")
            else:
                st.success("✅ Račun je tačno raspodeljen!")
                validna_podela = True

# --- QR SEKCIJA ---
st.divider()
if validna_podela:
    if st.button("🔥 GENERIŠI QR KODOVE", use_container_width=True, type="primary"):
        if not moje_ime or not moj_racun:
            st.error("⚠️ Unesi svoje podatke u sidebar-u (levo) pre generisanja!")
        else:
            c_racun = ocisti_racun(moj_racun)
            
            if nacin == "Ravnopravno (Svi isto)":
                # Prikazujemo jedan veliki centralni QR kod
                dug = finalni_dugovi["Zajednički kod"]
                iz_fmt = "{:.2f}".format(dug).replace('.', ',')
                ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Podela racuna"
                qr_img = qrcode.make(ips_data)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                
                col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
                with col_c2:
                    st.image(buf.getvalue(), caption=f"Iznos: {dug:.2f} RSD", use_container_width=True)
            else:
                # Prikazujemo male kodove u kolonama
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
                            st.image(buf.getvalue(), width=140)
                            st.caption(f"{dug:.2f} RSD")

st.caption("<br><br>Ovaj alat generiše kodove za mBanking (NBS IPS). Proverite podatke pre uplate.", unsafe_allow_html=True)
