import streamlit as st
import requests

API = "http://localhost:5002"

st.set_page_config(page_title="FilmApp", layout="wide")
st.title("FilmApp - prohlížení filmů")

# fetch options
opts = requests.get(f"{API}/options").json()

years = opts.get("years") or []
ratings = opts.get("ratings") or [i/2 for i in range(0,21)]

col1, col2, col3 = st.columns([2,1,1])
with col1:
    q = st.text_input("Hledat titul nebo popis")
with col2:
    year = st.selectbox("Rok", options=[""] + years)
with col3:
    min_rating = st.selectbox("Min. hodnocení", options=[0] + ratings)

sort = st.selectbox("Seřadit podle", ["rating desc", "rating asc", "year desc", "year asc", "title asc", "title desc"]) 

if st.button("Hledat"):
    if q:
        resp = requests.get(f"{API}/search?q={q}")
    else:
        order = "asc" if "asc" in sort else "desc"
        sort_by = sort.split()[0]
        resp = requests.get(f"{API}/films?sort={sort_by}&order={order}&min_rating={min_rating}" + (f"&year={year}" if year else ""))
    if resp.status_code == 200:
        films = resp.json()
        for f in films:
            st.write(f"### {f.get('title')} ({f.get('year')}) - {f.get('rating')}")
            st.write(f.get('description'))
            st.image(f.get('poster_url') or '')
    else:
        st.error("Chyba při načítání")

if st.button("Náhodný film"):
    resp = requests.get(f"{API}/films/random?min_rating={min_rating}" + (f"&year={year}" if year else ""))
    if resp.status_code == 200:
        f = resp.json()
        st.write(f"# {f.get('title')} ({f.get('year')}) - {f.get('rating')}")
        st.write(f.get('description'))
        st.image(f.get('poster_url') or '')
    else:
        st.warning("Nebyly nalezeny žádné filmy s vybranými parametry")
