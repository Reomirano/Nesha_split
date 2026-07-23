import streamlit as st
import qrcode
from io import BytesIO
import re
import cv2
import numpy as np

# --- FUNKCIJE ---
def ocisti_racun(racun):
    samo_cifre = re.sub(r'\D', '', racun)
    if 5 < len(samo_cifre) < 18:
        kod_banke = samo_cifre[:3]          
        kontrolni_broj = samo_cifre[-2:]     
        partija_racuna = samo_cifre[3:-2]    
        partija_sa_nulama = partija_racuna.zfill(13)
        return f"{kod_banke}{partija_sa_nulama}{kontrolni_broj}"
    return samo_cifre.zfill(18)

def formatiraj_za_prikaz(racun_18_cifara):
    if len(racun_18_cifara) == 18:
        return f"{racun_18_cifara[:3]}-{racun_18_cifara[3:-2]}-{racun_18_cifara[-2:]}"
    return racun_18_cifara

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
moj_racun = st.sidebar.text_input("Broj računa administratora:", value="", key="user_bank", placeholder="Broj tekućeg računa")

# --- GLAVNI PANEL ---
st.title("💰 Podela troškova")

with st.expander("📖 Kako ovo radi?"):
    st.write("""
    1. **Unesi svoj račun:** U levom meniju unesi svoje ime i broj računa.
    2. **Unesi iznose:** Upiši vrednost sa računa i cenu dostave (ili otpremi sliku da očita QR kod).
    3. **Odaberi metodu:** Ravnopravno ili ručni unos.
    4. **Skeniranje:** Generiši IPS QR kodove za uplatu.
    """)

c_racun = ocisti_racun(moj_racun) if moj_racun else ""
prikaz_racuna = formatiraj_za_prikaz(c_racun) if c_racun else "Nije unet"

st.markdown(f"""
    <p style="font-size: 1.5rem; font-weight: 500; margin-top: 15px; margin-bottom: 0;">
        🏦 Ime primaoca: <b>{moje_ime if moje_ime else '...'}</b> | Račun primaoca: <b>{prikaz_racuna}</b>
    </p>
""", unsafe_allow_html=True)

st.divider()

sufiks = st.session_state.reset_kljuc
col_levo, col_desno = st.columns([1, 1])

with col_levo:
    st.subheader("📸 Račun")
    fajl = st.file_uploader("Otpremi dokument", type=['jpg', 'jpeg', 'png'], key=f"fajl_{sufiks}")
    
    if fajl:
        st.image(fajl, use_container_width=True)
        
        file_bytes = np.asarray(bytearray(fajl.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        
        qr_detector = cv2.QRCodeDetector()
        data, points, _ = qr_detector.detectAndDecode(opencv_image)
        
        if data:
            st.success("✔ QR kod uspešno učitan sa računa!")
            st.session_state[f"qr_url_{sufiks}"] = data
            
            with st.expander("Detalji očitanog linka"):
                st.write(data)
        else:
            st.warning("⚠️ QR kod nije pronađen na slici. Pokušaj ponovo sa jasnijom fotografijom.")

with col_desno:
    if st.button("🔄 Novi unos", use_container_width=True, type="primary"):
        st.session_state.reset_kljuc += 1
        st.session_state.clanovi_univerzalni = []
        if f"ucesnici_{sufiks}" in st.session_state:
            del st.session_state[f"ucesnici_{sufiks}"]
        st.rerun()
    
    st.subheader("✍️ Podaci")
    c1, c2 = st.columns(2)
    iznos_racuna = c1.number_input("Iznos sa računa (RSD):", min_value=0.0, step=10.0, value=None, placeholder="0,00", key=f"racun_{sufiks}")
    dostava = c2.number_input("Dostava (RSD):", min_value=0.0, step=10.0, value=None, placeholder="0,00", key=f"dostava_{sufiks}")

    v_racun = iznos_racuna if iznos_racuna is not None else 0.0
    v_dostava = dostava if dostava is not None else 0.0
    suma_ukupno = v_racun + v_dostava

    st.markdown(f"### Ukupno: {f'{suma_ukupno:.2f}'.replace('.', ',')} RSD")
    st.divider()

    nacin = st.radio("Metoda podele:", ["Ravnopravno", "Ručni unos"], horizontal=True, key=f"nacin_{sufiks}")

    finalni_dugovi = {}
    validna_podela = False

    if nacin == "Ravnopravno":
        broj_ljudi = st.number_input("Ukupan broj osoba:", min_value=1, value=2, step=1, key=f"br_ljudi_{sufiks}")
        if broj_ljudi > 1:
            po_osobi = suma_ukupno / broj_ljudi
            st.info(f"Po osobi: **{f'{po_osobi:.2f}'.replace('.', ',')} RSD**")
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

        st.text_input("Dodaj učesnika na listu (potvrdi na Enter):", key="novo_ime_input", on_change=dodaj_direktno)
        
        sortirani = sorted(st.session_state.clanovi_univerzalni)
        
        if sortirani:
            odabrani = st.multiselect("Ko učestvuje:", options=sortirani, key=f"ucesnici_{sufiks}")
            
            if odabrani:
                br_ucesnika = len(odabrani)
                fiksna_dostava = v_dostava / br_ucesnika
                
                st.markdown(f"""
                    <div style="background-color: #f3e5f5; padding: 10px; border-radius: 5px; border-left: 5px solid #9c27b0; margin-bottom: 20px;">
                        <span style="color: #4a148c;">Učešće u dostavi: <b>{f'{fiksna_dostava:.2f}'.replace('.', ',')} RSD</b></span>
                    </div>
                """, unsafe_allow_html=True)
                
                trenutna_suma = 0.0
                for o in odabrani:
                    dug = st.number_input(f"Iznos za učesnika {o}:", min_value=0.0, step=10.0, value=None, placeholder="0,00", key=f"rucni_{o}_{sufiks}")
                    v_dug = dug if dug is not None else 0.0
                    finalni_dugovi[o] = v_dug
                    trenutna_suma += v_dug
                
                ostatak = suma_ukupno - trenutna_suma
                if abs(ostatak) < 0.01:
                    validna_podela = True
                elif ostatak > 0:
                    st.warning(f"Preostalo: **{f'{ostatak:.2f}'.replace('.', ',')} RSD**")
                else:
                    st.error(f"Višak: **{f'{abs(ostatak):.2f}'.replace('.', ',')} RSD**")
            
            def obrisi_listu_callback():
                st.session_state.clanovi_univerzalni = []
                kljuc_multi = f"ucesnici_{sufiks}"
                if kljuc_multi in st.session_state:
                    del st.session_state[kljuc_multi]

            st.button("Obriši celu listu", on_click=obrisi_listu_callback)

# --- QR SEKCIJA ---
st.divider()
if validna_podela and suma_ukupno > 0:
    if st.button("🔥 GENERIŠI QR KODOVE", use_container_width=True, type="primary"):
        if not moje_ime or not moj_racun:
            st.error("⚠️ Popuni podatke u sidebar-u!")
        else:
            if nacin == "Ravnopravno":
                iznos_zajednicki = finalni_dugovi["Zajednički"]
                iz_fmt = "{:.2f}".format(iznos_zajednicki).replace('.', ',')
                ips_data = f"K:PR|V:01|C:1|R:{c_racun}|N:{moje_ime}|I:RSD{iz_fmt}|SF:289|S:Podela racuna"
                qr_img = qrcode.make(ips_data)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                _, col_qr, _ = st.columns([1, 1, 1])
                with col_qr:
                    st.image(buf.getvalue(), caption=f"Iznos: {iz_fmt} RSD", use_container_width=True)
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
                            st.caption(f"{iz_fmt} RSD")

st.write("") 
st.divider() 
st.caption("**Napomena:** Aplikacija je namenjena isključivo za plaćanja u okviru **IPS sistema Narodne banke Srbije**. Pre potvrde plaćanja, obavezno **proverite ispravnost podataka**. Autor ne snosi odgovornost za pogrešne uplate.")
st.caption("**Disclaimer:** This app is designed solely for **Serbian IPS payments**. Please verify all details before confirming. The author is not responsible for any incorrect payments.")
