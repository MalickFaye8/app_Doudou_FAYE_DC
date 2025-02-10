import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import date
import io

import plotly.express as px
import plotly.graph_objects as go


# Configuration de la page
st.set_page_config(page_title="Real Estate Scraper & Dashboard", page_icon="🏠", layout="wide")





# Titre de l'application
st.title("🏠 Real Estate Data Scraper & Dashboard")
st.markdown("""
    Cette application permet de scraper, nettoyer et visualiser des données immobilières.
    Utilisez les options ci-dessous pour explorer les fonctionnalités.
""")

# Sidebar pour les options
st.sidebar.title("Options")
option = st.sidebar.radio("Choisir une action :", ["Scraper des données", "Télécharger des données", "Dashboard", "Évaluer l'application"])

st.write(f"Option sélectionnée : {option}")  # Pour vérifier si l'option change

# Fonction pour scraper les données
def scrape_data(urls, categories, num_pages):
    data = []
    for url, category in zip(urls, categories):
        for page_num in range(1, num_pages + 1):
            page_url = f"{url}?page={page_num}" if page_num > 1 else url
            try:
                response = requests.get(page_url, verify=False)
                #soup = BeautifulSoup(response.text, "lxml")
                soup = BeautifulSoup(response.text, "html.parser")
                listings = soup.find_all("div", class_="listings-cards__list-item")

                for listing in listings:
                    details = listing.find("div", class_="listing-card__header__title")
                    details = details.text.strip() if details else "Non disponible"

                    nb_chambres = listing.find('span', class_='listing-card__header__tags__item--no-of-bedrooms')
                    nb_chambres = nb_chambres.text.strip() if nb_chambres else "Non disponible"

                    superficie = listing.find('span', class_='listing-card__header__tags__item--square-metres')
                    superficie = superficie.text.strip() if superficie else "Non disponible"

                    adresse = listing.find("div", class_="listing-card__header__location")
                    adresse = adresse.text.strip() if adresse else "Non disponible"

                    prix = listing.find("span", class_="listing-card__price__value")
                    prix = prix.text.strip() if prix else "Non disponible"

                    image = listing.find('img', class_='listing-card__image__resource')
                    image_lien = image['src'] if image else "Non disponible"

                    date_effet = listing.find("div", class_="listing-card__date-line")
                    date_effet = date_effet.text.strip() if date_effet else "Non disponible"

                    row = {
                        "Catégorie": category,
                        "Détails": details,
                        "Nombre de chambres": nb_chambres,
                        "Superficie": superficie,
                        "Adresse": adresse,
                        "Prix": prix,
                        "Image": image_lien,
                        "Date d'effet": date_effet,
                        "Date d'extraction": date.today().strftime("%Y-%m-%d")
                    }
                    data.append(row)
            except Exception as e:
                st.error(f"Erreur lors du scraping de {url} page {page_num} : {e}")

    df = pd.DataFrame(data)

    # Vérifier que les colonnes existent avant d'appliquer le nettoyage
    colonnes_a_nettoyer = ["Détails", "Nombre de chambres", "Superficie", "Adresse", "Prix", "Date d'effet"]
    for col in colonnes_a_nettoyer:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: re.sub(r'[^a-zA-Z0-9\s]', '', x) if isinstance(x, str) else x)

    return df

def nettoyer_donnees(df):
    df_cleaned = df.copy()
    for var in ['detail', 'nombre_chambre', 'superficie', 'adresse',
       'prix']:
        df_cleaned[var] = df_cleaned[var].apply(supprimer_caracteres_speciaux)

    df_cleaned['Montant-Prix'] = df_cleaned['prix'].apply(extraire_montant)
    # Remplacer les caractères indésirables dans 'Montant-Prix'
    df_cleaned['Montant-Prix'] = df_cleaned['Montant-Prix'].str.replace('\u202f', '').str.replace(' ', '')
    # Convertir 'Montant-Prix' en float, en remplaçant les valeurs invalides par 0
    df_cleaned['Montant-Prix'] = pd.to_numeric(df_cleaned['Montant-Prix'], errors='coerce').fillna(0)

    df_cleaned['Devise-Prix'] = df_cleaned['prix'].apply(extraire_devise)
    df_cleaned['type_Propriete'] = df_cleaned['web-scraper-start-url'].apply(type_propriete)
    df_cleaned['Categorie_Propriete'] = df_cleaned['detail'].apply(categoriser_propriete)


    # Extraire de la surface sans l'unité
    df_cleaned['superficie'] = df_cleaned['superficie'].apply(extraire_montant)

    columns_to_keep = [
        'nombre_salle_bain','detail', 'nombre_chambre', 'superficie',
        'adresse', 'image_lien-src','type_Propriete', 'Categorie_Propriete',
        'Montant-Prix', 'Devise-Prix'
    ]
    df_cleaned = df_cleaned[columns_to_keep]
    return df_cleaned

def extraire_montant(valeur):
    if isinstance(valeur, (str, bytes)):
        match = re.search(r'([\d\s,]+(?:\.\d+)?)', valeur)
        if match:
            montant = match.group(1).replace(' ', '').replace(',', '.')
            return montant
        else:
            return None
    elif isinstance(valeur, (int, float)):
        return str(valeur)
    else:
        return None

def extraire_devise(valeur):
    if isinstance(valeur, (str, bytes)):
        match = re.search(r'([^\d\s,\.]+(?:\s+[^\d\s,\.]+)*)', valeur)
        if match:
            return match.group(1).strip()
    return None

def type_propriete(prop):
    prop_lower = prop.lower()
    if 'terrain' in prop_lower or 'terrains' in prop_lower:
        return 'terrains'
    elif 'appartement-meubles' in prop_lower or 'appartements-meubles' in prop_lower:
        return 'appartement-meublés'
    elif 'appartements-a-louer' in prop_lower or 'appartement-a-louer' in prop_lower:
        return 'appartement à louer'
    else:
        return 'autre'

def categoriser_propriete(prop):
    prop_lower = prop.lower()
    if 'terrain' in prop_lower or 'terrains' in prop_lower:
        return 'terrains'
    elif 'appartement' in prop_lower or 'appartements' in prop_lower:
        return 'appartement'
    elif 'chambre' in prop_lower:
        return 'chambre'
    elif 'villa' in prop_lower or 'villas' in prop_lower:
        return 'villa'
    elif 'studio' in prop_lower or 'studios' in prop_lower:
        return 'studio'
    elif 'maison' in prop_lower or 'maisons' in prop_lower:
        return 'maison'
    else:
        return 'autre'
    # Fonction pour supprimer les caractères spéciaux d'une chaîne
def supprimer_caracteres_speciaux(chaine):
    if isinstance(chaine, (str, bytes)):
        return re.sub(r'[^a-zA-Z0-9\s]', '', str(chaine))
    else:
        return chaine


# Interface Streamlit pour le scraping
if option == "Scraper des données":
    st.header("🔍 Scraper des données")
    st.markdown("""
        Scrapez des données immobilières à partir des liens prédéfinis ou personnalisés.
    """)
    
    # Liste des liens prédéfinis
    predefined_links = {
        "Appartements à louer": "https://www.expat-dakar.com/appartements-a-louer",
        "Appartements meublés": "https://www.expat-dakar.com/appartements-meubles",
        "Terrains à vendre": "https://www.expat-dakar.com/terrains-a-vendre"
    }
    
    # Nombre de liens à scraper
    num_links = st.number_input("Nombre de liens à scraper", min_value=1, max_value=3, value=1)
    
    # Sélection des liens et catégories
    urls, categories = [], []
    for i in range(num_links):
        col1, col2 = st.columns(2)
        with col1:
            selected_categ = st.selectbox(
                f"Sélectionnez une catégorie prédéfinie {i+1}",
                options=list(predefined_links.keys()),
                key=f"predefined_link_{i}"
            )
            url = predefined_links[selected_categ]
        with col2:
            Lien = st.text_input(f"Lien {i+1}", url)

        if url not in urls:
            urls.append(url)
            categories.append(selected_categ)
        else:
            st.warning(f"L'URL '{url}' a déjà été ajoutée. Veuillez en choisir une autre.")

    # Nombre de pages à scraper
    num_pages = st.number_input("Nombre de pages à scraper", min_value=1, max_value=100, value=10)
    
    # Bouton pour lancer le scraping
    if st.button("🚀 Lancer le scraping"):
        with st.spinner("Scraping en cours..."):
            df = scrape_data(urls, categories, num_pages)
            df['Montant-Prix'] = df['Prix'].apply(extraire_montant)
            df['Devise-Prix'] = df['Prix'].apply(extraire_devise)
            st.success("Scraping terminé !")
            st.write(df)
            
            # Télécharger les données au format CSV
            st.download_button(
                label="📥 Télécharger les données scrapées",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="donnees_scrapees.csv",
                mime="text/csv"
            )

# Télécharger des données
elif option == "Télécharger des données":
    st.header("📂 Télécharger des données scrapées")
    st.markdown("""
        Chargez un fichier Excel ou CSV pour visualiser et nettoyer les données.
    """)
    uploaded_file = st.file_uploader("Choisir un fichier (Excel ou CSV)", type=["xlsx", "csv"])
    if uploaded_file:
        # Vérifier si c'est un fichier Excel ou CSV
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        st.write("Données brutes :")
        st.dataframe(df)
        # Nettoyage des données
        df_cleaned = nettoyer_donnees(df)
        st.write("Données nettoyées :")
        st.dataframe(df_cleaned)
        st.session_state['df_cleaned'] = df_cleaned
        st.success("Les données nettoyées sont prêtes pour le Dashboard !")

# Dashboard
elif option == "Dashboard":
    st.header("📊 Dashboard des données nettoyées")
    st.markdown("""
        Explorez les données nettoyées à travers des indicateurs clés et des visualisations interactives.
    """)
    #uploaded_file = st.file_uploader("Choisir un fichier Excel", type=["xlsx"])

    if 'df_cleaned' not in st.session_state:
        st.warning("Veuillez d'abord charger et nettoyer les données dans la section 'Télécharger des données'.")
    else:
        df_cleaned = st.session_state['df_cleaned']


    # Filtres interactifs
    st.subheader("🔧 Filtres")
    col1, col2, col3 = st.columns(3)
    with col1:
        type_propriete_filter = st.multiselect(
            "Filtrer par type de propriété",
            options=df_cleaned['type_Propriete'].unique(),
            default=df_cleaned['type_Propriete'].unique()
        )
    with col2:
        categorie_filter = st.multiselect(
            "Filtrer par catégorie",
            options=df_cleaned['Categorie_Propriete'].unique(),
            default=df_cleaned['Categorie_Propriete'].unique()
        )
    with col3:
        prix_range = st.slider(
            "Filtrer par prix",
            min_value=float(df_cleaned['Montant-Prix'].astype(float).min()),
            max_value=float(df_cleaned['Montant-Prix'].astype(float).max()),
            value=(float(df_cleaned['Montant-Prix'].astype(float).min()), float(df_cleaned['Montant-Prix'].astype(float).max()))
        )

    # Appliquer les filtres
    filtered_data = df_cleaned.copy()  # Commencez avec toutes les données
    # Filtre par type de propriété
    if type_propriete_filter:
        filtered_data = filtered_data[filtered_data['type_Propriete'].isin(type_propriete_filter)]
        
    # Filtre par catégorie
    if categorie_filter:
        filtered_data = filtered_data[filtered_data['Categorie_Propriete'].isin(categorie_filter)]
    # Filtre par plage de prix
    filtered_data = filtered_data[
        (filtered_data['Montant-Prix'].astype(float) >= prix_range[0]) &
        (filtered_data['Montant-Prix'].astype(float) <= prix_range[1])
    ]
    # Afficher les indicateurs clés (KPI) basés sur les données filtrées
    st.subheader("📈 Indicateurs clés")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nombre total de propriétés", filtered_data.shape[0])
    with col2:
        prix_moyen = filtered_data['Montant-Prix'].astype(float).mean()
        st.metric("Prix moyen", f"{prix_moyen:.2f} {filtered_data['Devise-Prix'].mode()[0]}")
    with col3:
        superficie_moyenne = filtered_data['superficie'].astype(float).mean()
        st.metric("Superficie moyenne", f"{superficie_moyenne:.2f} m²")
    # Afficher les données filtrées
    st.subheader("📋 Données filtrées")
    st.dataframe(filtered_data)
    # Graphiques
    st.subheader("📊 Visualisations")

    # Répartition par catégorie de propriété (camembert)
    st.write("Répartition par catégorie de propriété")
    fig1 = px.pie(filtered_data, names='Categorie_Propriete', title="Répartition par catégorie de propriété")
    st.plotly_chart(fig1, use_container_width=True)

    # Distribution des prix (histogramme)
    st.write("Distribution des prix")
    fig2 = px.histogram(filtered_data, x='Montant-Prix', nbins=20, title="Distribution des prix")
    st.plotly_chart(fig2, use_container_width=True)

    # Relation entre superficie et prix (nuage de points)
    st.write("Relation entre superficie et prix")
    fig3 = px.scatter(filtered_data, x='superficie', y='Montant-Prix', color='Categorie_Propriete', title="Superficie vs Prix")
    st.plotly_chart(fig3, use_container_width=True)

    # Carte géographique (si les données contiennent des informations géographiques)
    if 'adresse' in filtered_data.columns:
        st.write("Carte des propriétés")
        try:
            # Exemple simple de carte (nécessite des données géolocalisées)
            filtered_data['latitude'] = filtered_data['adresse'].apply(lambda x: 14.7167)  # Exemple de latitude
            filtered_data['longitude'] = filtered_data['adresse'].apply(lambda x: -17.4677)  # Exemple de longitude
            fig5 = px.scatter_mapbox(
                filtered_data,
                lat='latitude',
                lon='longitude',
                hover_name='detail',
                hover_data=['Montant-Prix', 'superficie'],
                color='Categorie_Propriete',
                zoom=10
            )
            fig5.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig5, use_container_width=True)
        except Exception as e:
            st.warning(f"Impossible d'afficher la carte : {e}")

# Évaluer l'application
elif option == "Évaluer l'application":
    st.header("⭐ Évaluer l'application")
    st.markdown("""
        Nous apprécions vos commentaires pour améliorer cette application.
    """)
    with st.form("evaluation_form"):
        nom = st.text_input("Nom")
        email = st.text_input("Email")
        note = st.slider("Note (1-10)", 1, 10)
        commentaire = st.text_area("Commentaire")
        if st.form_submit_button("Soumettre"):
            st.success("Merci pour votre évaluation !")
