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

if "reset_kljuc" not in st.session_state:
    st.session_state.reset_kljuc = 0
if 'clanovi_univerzalni' not in st.session_state:
    st.session_state.clanovi_univerzalni = []

# --- SIDEBAR: PODACI ---
st.sidebar.markdown("*<span style='font-size: 0.8rem; color: gray;'>powered by Reomirano</span>*", unsafe_allow_html=True)
st.sidebar.header("⚙️ Tvoja podešavanja")
moje_ime = st.sidebar.text_input("Administrator:", value="", key="user_name", placeholder="Ime i prezime vlasnika računa")
moj_racun = st.sidebar.text_input("Broj računa administratora:", value="", key="user_bank", placeholder="18-ocifreni broj tekućeg računa")

# --- GLAVNI PANEL ---
st.title("💰 Podela troškova")

with st.expander("📖 Kako ovo radi?"):
    st.write("""
    1. **Unesi svoj račun:** U levom meniju unesi svoje ime i broj računa.
    2. **Unesi iznose:** Upiši vrednost sa računa i cenu dostave.
    3. **Odaberi metodu:**
        * **Ravnopravno:** Unesi broj ljudi i dobijaš univerzalni QR kod.
        * **Ručni unos:** Dodaš imena kolega i uneseš pojedinačnu vrednost.
    4. **Skeniranje:** Kolege otvore mBanking, izaberu 'IPS' i očitaju kod sa ekrana.
    """)

st.caption(f"Novac leže na: **{moje_ime}** | Račun: **{moj_racun}**")
st.divider()

sufiks = st.session_state.reset_kljuc
col_levo, col_desno = st.columns([1, 1])

with col_levo:
    st.subheader("📸 Račun")
    fajl = st.file_uploader("Otpremi dokument", type=['jpg', 'jpeg', 'png'], key=f"fajl_{sufiks}")
    if fajl:
        st.image(fajl, use_container_width=True)

with col_desno:
    if st.button("🔄 Novi unos / Reset", use_container_width=True, type="primary"):
        st.session_state.reset_kljuc += 1
        st.session_state.clanovi_univerzalni = []
        if f"ucesnici_{sufiks}" in st.session_state:
            del st.session_state[f"ucesnici_{sufiks}"]
        st.rerun()
    
    st.subheader("✍️ Podaci")
    c1, c2 = st.columns(2)
    iznos_racuna = c1.number_input("Iznos sa računa (RSD):", min_value=0.0, step=10.0, value=None, placeholder="0.00", key=f"racun_{sufiks}")
    dostava = c2.number_input("Dostava (RSD):", min_value=0.0, step=10.0, value=None, placeholder="0.00", key=f"dostava_{sufiks}")

    v_racun = iznos_racuna if iznos_racuna is not None else 0.0
    v_dostava = dostava if dostava is not None else 0.0
    suma_ukupno = v_racun + v_dostava

    st.markdown(f"### Ukupno: {suma_ukupno:.2f} RSD")
    st.divider()

    nacin = st.radio("Metoda podele:", ["Ravnopravno", "Ručni unos"], horizontal=True, key=f"nacin_{sufiks}")

    finalni_dugovi = {}
    validna_podela = False

    if nacin == "Ravnopravno":
        broj_ljudi = st.number_input("Ukupan broj osoba (i ti):", min_value=1, value=2, step=1, key=f"br_ljudi_{sufiks}")
        if broj_ljudi > 1:
            po_osobi = suma_ukupno / broj_ljudi
            st.info(f"Po osobi: **{po_osobi:.2f} RSD**")
            finalni_dugovi["Zajednički"] = po_osobi
            validna_podela = True

    else:
        def dodaj_direktno():
            ime = st.session_state.novo_ime_input.strip()
            if ime:
                if ime not in st.session_state.clanovi_univerzalni:
                    st.session_state.clanovi_univerzalni.append(ime)
                kljuc_multi = f"ucesnici_{sufiks}"
                trenutno_selektovani = list(st.session_state.get(kljuc_multi, []))
                if ime not in trenutno_selektovani:
                    trenutno_selektovani.append(ime)
                    st.session_state[kljuc_multi] = trenutno_selektovani
            st.session_state.novo_ime_input = ""

        st.text_input("Dodaj kolegu na listu (Enter dodaje i bira):", key="novo_ime_input", on_change=dodaj_direktno)
        
        sortirani = sorted(st.session_state.clanovi_univerzalni)
        
        if sortirani:
            odabrani = st.multiselect("Ko učestvuje:", options=sortirani, key=f"ucesnici_{sufiks}")
            
            if odabrani:
                # PRORAČUN FIKSNOG UČEŠĆA U DOSTAVI
                br_ucesnika = len(odabrani)
                fiksna_dostava = v_dostava / br_ucesnika
                st.write(f"Učešće u dostavi: **{fiksna_dostava:.2f} RSD**")
                
                trenutna_suma = 0.0
                for o in odabrani:
                    dug = st.number_input(f"Iznos za {o}:", min_value=0.0, step=10.0, value=None, placeholder="0.00", key=f"rucni_{o}_{sufiks}")
                    v_dug = dug if dug is not None else 0.0
                    finalni_dugovi[o] = v_dug
                    trenutna_suma += v_dug
                
                ostatak = suma_ukupno - trenutna_suma
                if abs(ostatak) < 0.01:
                    validna_podela = True
                elif ostatak > 0:
                    st.warning(f"Preostalo: **{ostatak:.2f} RSD**")
                else:
                    st.error(f"Višak: **{abs(ostatak):.2f} RSD**")
            
            if st.button("Obriši celu listu"):
                st.session_state.clanovi_univerzalni = []
                if f"ucesnici_{sufiks}" in st.session_state:
                    st.session_state[f"ucesnici_{sufiks}"] = []
                st.rerun()

# --- QR SEKCIJA ---
st.divider()
if validna_podela and suma_ukupno > 0:
    if st.button("🔥 GENERIŠI QR KODOVE", use_container_width=True, type="primary"):
        if not moje_ime or not moj_racun:
            st.error("⚠️ Popuni podatke u sidebar-u!")
        else:
            c_racun = ocisti_racun(moj_racun)
            if nacin == "Ravnopravno":
                iz_fmt = "{:.2f}".format(finalni_dugovi["Zajednički"]).replace('.', ',')
                ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Podela racuna"
                qr_img = qrcode.make(ips_data)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                _, col_qr, _ = st.columns([1, 1, 1])
                with col_qr:
                    st.image(buf.getvalue(), caption=f"Iznos: {finalni_dugovi['Zajednički']:.2f} RSD", use_container_width=True)
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

st.caption("<br><br>*Aplikacija za NBS IPS plaćanja.*", unsafe_allow_html=True)
