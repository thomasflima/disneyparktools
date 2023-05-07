import datetime
import pandas as pd
import geopandas as gpd
import requests
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from streamlit_option_menu import option_menu
import streamlit as st
import matplotlib as plt
from PIL import Image, ImageDraw
import numpy as np
import folium
from branca.colormap import LinearColormap as lcmap
import googlemaps
import polyline
from datetime import datetime, timedelta
import json

st.set_config_file(path="config.toml")

@st.cache_data()
def load_data_wait_times():
    df_atracoes = pd.read_csv('data/atracoes_disney_att.csv')
    numbers = [5, 6, 7, 8]
    wait_time_parks_list = []
    for number in numbers:
        url = f"https://queue-times.com/fr/parks/{number}/queue_times.json"
        response = requests.get(url)
        if response.status_code == 200:
            wait_time_parks_json = response.json()
            for land in wait_time_parks_json['lands']:
                for ride in land['rides']:
                    wait_time_parks_list.append({
                        'name': ride['name'],
                        'is_open': ride['is_open'],
                        'wait_time': ride['wait_time'],
                        'last_updated': ride['last_updated']})
        else:
            print(f"A solicitação falhou com o código de erro {response.status_code}.")
    wait_time_parks_df = pd.DataFrame(wait_time_parks_list)
    merged_df = pd.merge(wait_time_parks_df, df_atracoes, left_on='name',
                         right_on='Ride Name')
    return merged_df

@st.cache_data()
def get_walt_disney_parks(url):
    """Obtém uma lista dos parques da Walt Disney Attractions a partir da API Queue Times"""
    response = requests.get(url)

    if response.status_code == 200:
        parks = response.json()
        walt_disney_parks = [park for park in parks if "Walt Disney Attractions" in park["name"]]
        return walt_disney_parks[0]["parks"]
    else:
        print(f"A solicitação falhou com o código de erro {response.status_code}.")
        return []

def filter_data(df_atracoes, parques):
    col1, col2, col3 = st.columns(3)
    with col1:
        nome_parque = st.selectbox("Choose a Park Name", parques)
    with col2:
        if nome_parque == "All":
            selected_land_name = "All"
            land_names = ["All"]
            st.selectbox("Choose a Land Name", land_names, key="land")
        else:
            land_names = df_atracoes[df_atracoes["Park Name"] == nome_parque]['Land'].unique().tolist()
            land_names.insert(0, 'All')
            selected_land_name = st.selectbox('Choose a Land Name:', land_names, key="land")
    if nome_parque == "All":
        df_filtrado = df_atracoes
    else:
        if selected_land_name == "All":
            df_filtrado = df_atracoes[df_atracoes["Park Name"] == nome_parque]
        else:
            df_filtrado = df_atracoes[
                (df_atracoes["Park Name"] == nome_parque) & (df_atracoes["Land"] == selected_land_name)]
    with col3:
        ride_names = df_filtrado["Ride Name"].unique().tolist()
        ride_names.insert(0, "All")
        selected_ride_name = st.selectbox("Choose an Attraction", ride_names)
        if selected_ride_name != "All":
            df_filtrado = df_filtrado[df_filtrado["Ride Name"] == selected_ride_name]
    return df_filtrado

def ler_arquivo_csv(nome_arquivo):
    df_atracoes = pd.read_csv(nome_arquivo)
    return df_atracoes

# define as camadas de mapa com folium.TileLayer()
fantasyland = folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/thomaslima22/clgmfw5un001301qn9d8v8ffd/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoidGhvbWFzbGltYTIyIiwiYSI6ImNrcmNhcWYzOTUxNXUybnJ1MTYyemk2NnMifQ.iNn2WyeT4PxcDcELUieNaQ',attr='Mapbox',name='Fantasyland',retain=True)

shadownland = folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/thomaslima22/clgmg8fop001601qth4lz7vr6/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoidGhvbWFzbGltYTIyIiwiYSI6ImNrcmNhcWYzOTUxNXUybnJ1MTYyemk2NnMifQ.iNn2WyeT4PxcDcELUieNaQ',attr='Mapbox',name='Shadownland',retain=True)

neverland = folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/thomaslima22/clgmger0y001i01ny8a4m58um/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoidGhvbWFzbGltYTIyIiwiYSI6ImNrcmNhcWYzOTUxNXUybnJ1MTYyemk2NnMifQ.iNn2WyeT4PxcDcELUieNaQ',attr='Mapbox',name='Neverland',retain=True)

real_world = folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/thomaslima22/clgmgfxgc001k01pe83qvau6x/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoidGhvbWFzbGltYTIyIiwiYSI6ImNrcmNhcWYzOTUxNXUybnJ1MTYyemk2NnMifQ.iNn2WyeT4PxcDcELUieNaQ',attr='Mapbox',name='Real World',retain=True)

monochrome =  folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/lbencz/clhcrd0sc00q601qpewwu47vt/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoibGJlbmN6IiwiYSI6ImNsZGVuZDJudzBhdDgzb3FiY3N6eDBhaXgifQ.78HzulaJ8rRPgX0bxND9zg',attr='Mapbox',name='Classic',retain=True)

supermario = folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/lbencz/clgdr3k4g00ph01mn1dwhd51m/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoibGJlbmN6IiwiYSI6ImNsZGVuZDJudzBhdDgzb3FiY3N6eDBhaXgifQ.78HzulaJ8rRPgX0bxND9zg', attr='Mapbox',name='Super Mario',retain=True)

totoro = folium.TileLayer(
    tiles='https://api.mapbox.com/styles/v1/lbencz/clgdvhyz900a601lcc2ojjfj8/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoibGJlbmN6IiwiYSI6ImNsZGVuZDJudzBhdDgzb3FiY3N6eDBhaXgifQ.78HzulaJ8rRPgX0bxND9zg', attr='Mapbox',name='Totoro',retain=True)



st.set_page_config(page_title="Disney's Parks Tools", page_icon="", layout="wide",initial_sidebar_state="expanded")
st.markdown('<link href="https://fonts.cdnfonts.com/css/walt-disney-script" rel="stylesheet">', unsafe_allow_html=True)
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Lato:wght@300&display=swap" rel="stylesheet">',unsafe_allow_html=True)

df_atracoes = ler_arquivo_csv('data/atracoes_disney.csv')
merged_df=load_data_wait_times()

def main():
    # Cria a seção do menu
    with st.sidebar:
        logo_image = "logo_app.png"
        st.sidebar.image(logo_image)
        # Adiciona o menu com as opções
        choice = option_menu(
            "Main Menu",
            ["Home", "Disney World Parks Map", "Real-Time Queue Status", "Magic Routes Calculator", "About Disney World Resorts", "Theme Parks World Map"],
            icons=["house", "map", "clock", "signpost", "book", "globe"],
            menu_icon="None",
            default_index=0,)
        st.markdown("<blockquote style='text-align: right; font-family: Walt Disney Script; font-size: 21px; margin-top: 0;'>If you can dream it, you can do it. - Walt Disney</blockquote>",
            unsafe_allow_html=True)
    if choice == 'Home':
        # Scroll to top of the page

        # Adicionar o mapa dentro de um collapse com o título "Look, it's a Disney map"
        with st.container():
            with st.expander("👀 Look, it's a 🏰 Disney 🗺️ map!"):
                # Defina a URL da solicitação
                url = "https://queue-times.com/pt-BR/parks.json"

                # Obter a lista de parques da Walt Disney Attractions
                parques = get_walt_disney_parks(url)
                latitude = float(parques[0]['latitude'])
                longitude = float(parques[0]['longitude'])
                mapa = folium.Map(location=[0, 0], zoom_start=2, tiles = monochrome)

                # Criar o cluster para os marcadores dos parques
                cluster = MarkerCluster(name='Parques')

                # Adicionar marcadores para cada parque ao cluster
                for parque in parques:
                    icon_dn = 'mickey.png'
                    icondisney = folium.features.CustomIcon(icon_dn, icon_size=(30, 40))
                    latitude = float(parque['latitude'])
                    longitude = float(parque['longitude'])
                    popup = folium.Popup(parque['name'], max_width=300)
                    folium.Marker(location=[latitude, longitude], popup=popup, icon=icondisney).add_to(cluster)


                # Adicionar o cluster ao mapa
                cluster.add_to(mapa)

                # Adicionar o controle de camadas ao mapa
                folium.LayerControl().add_to(mapa)

                # Exibir o mapa
                folium_static(mapa, width=850)


        tab1, tab2, tab3 = st.tabs(["Welcome to the Magic" ,"Behind the Scenes", "Meet the Dreammakers"])
        with tab1:

            st.write("## Welcome to Disney's Parks Tools!")
            st.write("If you love theme parks and Disney, you're in the right place!")
            st.write("Here, you'll have access to an amazing application developed with great care to provide you with the best experience at Disney theme parks.")
            st.write("Developed as a requirement for the Geospatial Applications Development course, the main objective of this project is to provide incredible interactive maps using Python libraries and APIs.")
            st.write("## Tools and Information")
            st.write("Here, you'll find a variety of tools and information about the main Disney parks. Want to know the wait time for each attraction? Or maybe calculate routes and time needed to get around the attractions? No problem, our platform has all of that! Additionally, you can also check an estimate of how many people are ahead of you in line.")
            st.write("## A Magical Experience")
            st.write("But that's just the beginning! To make your experience even more magical, we're providing various cartographic visualizations so you can see differences between them, as well as various base maps inspired by classic scenes from Disney movies. All of this to make your experience the best possible!")
            st.write("## Contribute to Our Project")
            st.write("The project is developed entirely nonprofit and purely for academic purposes. We're using data from the Queue Times API (available here https://queue-times.com/) , to which we give full credit for real-time data collection. If you find any bugs or have suggestions to improve the platform, please let us know by email at thomasfelipedelima@gmail.com. Your contribution is very important to us!")
            st.markdown("<center><img src='https://media.giphy.com/media/xdQ9tS2nEstKe7OcMX/giphy.gif' width='250px'></center>",
                unsafe_allow_html=True)
            st.markdown("""<div style='font-size: 16px; text-align: center;'><a href='https://giphy.com/' target='_blank' style="color: black; text-decoration:none;">Font: Giphy, 2023</a></div>""", unsafe_allow_html=True)


        with tab2:
            st.title("Behind the Scenes")
            st.write("""A collection of tools for spatial visualization of attractions in the theme parks of the Walt Disney World Resort complex. Explore this magical world of fun through interactive maps, wait time information, graphics, and much more.
              \nMade with love by Disney fans for Disney fans.""")
            st.subheader("Under Contruction")

        with tab3:
            st.title("Meet the Dreammakers")
            st.write("""🏰🎢🎠 We are a group of Disney fans who created this collection of tools for spatial visualization of attractions in the theme parks of the Walt Disney World complex. 🌟✨ We want to provide a magical experience for everyone who loves Disney.
            \n💻🐍 Our project was created with Streamlit, Python, and other technologies to bring information about interactive maps, wait times for queues, charts, and more. 📈🗺️ We hope you enjoy and explore this enchanted world with us. 🎉🎊.""")
            # Load image
            # Load image
            image = Image.open("lilian.png")

            # Resize image
            image = image.resize((200, 200))

            # Make image round
            mask = Image.new("L", (200, 200), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 200, 200), fill=255)
            image.putalpha(mask)
            # Display image and text side by side
            col_k1, col_k2 = st.columns([1, 3])
            with col_k1:
                st.image(image, use_column_width= 'auto',width=400)

            with col_k2:
                st.subheader("Hi I'am Lilian")
                st.write(
                "Hi there, my name is Lilian Bencz and I am 25 years old. Soon, I will be graduating in Cartographic and Land Surveying Engineering. I love challenges and I am not afraid to step out of my comfort zone to achieve my goals. I enjoy sunny days as they give me energy and inspiration to face the day with more enthusiasm. In my leisure time, I like to hang out with my friends. I am a huge fan of the Star Wars saga and my favorite childhood cartoon is Pokémon.")

                st.write(
                "My education in Cartographic and Land Surveying Engineering has given me skills in spatial analysis, geoprocessing, and data interpretation, which makes me a committed professional to provide accurate and efficient solutions.")

                st.write(
                "If you want to know more about me or connect with me professionally, please feel free to add me on LinkedIn (linkedin.com/in/lilianbencz) or contact me by email (lilianbencz@ufpr.br).")
                st.write("\n")
                st.write("\n")
                st.subheader("Hi I'am Thomas")

        # Load image
            image = Image.open("thomas.png")

        # Resize image
            image = image.resize((200, 200))

        # Make image round
            mask = Image.new("L", (200, 200), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 200, 200), fill=255)
            image.putalpha(mask)

        # Display image and text side by side
            col_k3, col_k4 = st.columns([1, 3])
            with col_k3:
                st.image(image, use_column_width= 'auto',width=400)

            with col_k4:
                st.write(
                "I am Thomas, and just like you, I believe in the magic of Disney. Since I was a child, I have been fascinated by the enchantment of Disney movies and the joy they bring into our lives. My favorite movie is undoubtedly 'Beauty and the Beast'! I know all the songs and every detail of this magical story that transports me to a world of dreams and imagination.")
                st.write(
                "I grew up watching the Disney Channel, and my passion for the characters and fantastic worlds only grew with time. And what about Disney World? That place is simply amazing! When I'm there, I feel like I'm part of a fairy tale, living magical and unforgettable moments.")
                st.write(
                "But a young man like me doesn't just live on magic. I graduated in Engineering from the Federal University of Paraná, and now I'm specializing in the area of emotional cartography and mapping of representations of the intangible world. This fascinating area allows me to explore maps in a whole new way, discovering how our emotions can be related and represented in a spatial way.")
                st.write(
                "In my free time, I am a small aspiring GIS developer, always looking for new tools and solutions to make the world a more amazing place. If you want to know more about my work, take a look at my GitHub (thomasfelipedelima) or contact me by email (thomasfelipedelima@gmail.com).")
                st.write(
                "I hope these tools are useful and can bring a little bit of the magic of the Disney world to you. Who knows, you might even embark on your own Disney developer adventure. Remember: magic is everywhere, you just have to believe!")

    elif choice == 'Disney World Parks Map':
        st.header("🗺️ Map of Attractions at Walt Disney World 🏰")
        st.write("Welcome to the magical world of Disney parks in Orlando! Here, the fun never ends, and now, with the Disney World Parks Map tool, your experience will be even more enchanting.")
        st.write("The Disney World Parks Map is an interactive map that allows you to filter the attractions of the four theme parks: Magic Kingdom, Epcot, Disney's Hollywood Studios, and Disney's Animal Kingdom. Imagine finding incredible attractions like Space Mountain, Splash Mountain, and Frozen Ever After with just a few clicks. You can even find your favorite restaurant or gift shop nearby.")
        st.write("This magical map is easy to use and different from traditional maps, as it combines cartographic visualization knowledge and the magic of Disney to provide a unique experience. Plus, it's completely free! You can change the background maps, inspired by your favorite magical lands. With it, you can get real-time information about attractions, wait times, approximate crowd levels, and much more. 🎢🎡🎠")
        st.write("The Disney World Parks Map tool is a simple and fun way to plan your day in the parks. Whether you're a first-time visitor or a veteran of Disney parks, the interactive map will help you make the most of your experience in Orlando. Let yourself be enchanted by Disney magic and have fun like never before! ✨🎉")
        m = folium.Map(location=[28.377625, -81.56505], zoom_start=13, tiles=real_world, )
        fantasyland.add_to(m)
        shadownland.add_to(m)
        neverland.add_to(m)
        parques = merged_df["Park Name"].unique().tolist()  # Obter lista única de parques e adicionar a opção "All"
        parques.insert(0, "All")
        df_filtrado = filter_data(merged_df, parques)

        # Criar GeoDataFrame com os pontos filtrados
        gdf_filtrado = gpd.GeoDataFrame(df_filtrado,
                                        geometry=gpd.points_from_xy(df_filtrado.Longitude, df_filtrado.Latitude))

        # Obter a extensão espacial da feição filtrada
        bounds = gdf_filtrado.bounds

        # Iterar sobre as linhas do DataFrame filtrado e adicionar marcadores ao mapa
        for index, row in df_filtrado.iterrows():
            if pd.isna(row["Latitude"]) or pd.isna(row["Longitude"]):
                continue  # Ignorar linhas com valores faltantes na latitude ou longitude

            # Dicionário de icones para cada parque
            icon_magic = 'magic.png'
            icon_animal = 'animal.png'
            icon_studio = 'studios.png'
            icon_epcot = 'epcot.png'

            magic = folium.features.CustomIcon(icon_magic, icon_size=(30, 40))
            animal = folium.features.CustomIcon(icon_animal, icon_size=(30, 40))
            studio = folium.features.CustomIcon(icon_studio, icon_size=(30, 40))
            epcot = folium.features.CustomIcon(icon_epcot, icon_size=(30, 40))

            icons = {"Disney Magic Kingdom": magic, "Epcot": epcot, "Disney Hollywood Studio": studio,
                     "Animal kingdom": animal}

            popup_text = f"<b>Ride:</b> {row['Ride Name']}<br><b>Park:</b> {row['Park Name']}<br><b>Land:</b> {row['Land']}"
            popup = folium.Popup(popup_text, max_width=500)
            icon = icons[row["Park Name"]]
            folium.Marker(location=[row["Latitude"], row["Longitude"]], popup=popup, icon=icon).add_to(m)

        # Definir zoom para a extensão espacial da feição filtrada
        m.fit_bounds([[bounds.miny.min(), bounds.minx.min()], [bounds.maxy.max(), bounds.maxx.max()]])

        # Exibir mapa
        folium.LayerControl(position='topleft').add_to(m)
        folium_static(m, width=915)

    elif choice == 'Real-Time Queue Status':
        st.title('⏰ Real-Time Queue Status ✨')
        st.write("With our 'Real-Time Queue Status' tool, you can experience a unique and enchanting experience. With just a few clicks, you can access an interactive map that allows you to filter the attractions of the four theme parks: Magic Kingdom 👸🏰, Epcot 🌎, Disney's Hollywood Studios 🎥, and Disney's Animal Kingdom 🦁, and check the average wait time for each attraction ⏰.")
        st.write("In addition, with our statistical chart of average time 📊, you can plan your visit in advance, knowing how long it may take at each attraction and optimize your fun time 🎉. And of course, this magical tool also includes a choropleth map that shows the approximate density of people per land 🗺️ and a chart 📈, helping you choose the least crowded areas and make the most of your experience.")
        st.write("We combined our knowledge of cartographic visualization with the magic of Disney to create a unique and free tool for all visitors to Disney parks. Enjoy the magic of Disney and have fun like never before with our 'Real-Time Queue Status' tool ✨.")
        tab1, tab2= st.tabs(["Real-Time Queue Status", "How many people are in this land?"])
        with tab1:
            legend_colors = {
                "red": "Wait time over 50 minutes",
                "yellow": "Wait time between 15-50 minutes",
                "green": "Wait time less than 15 minutes"}
            # Define a largura e altura do retângulo da legenda
            legend_width = "100%"
            legend_height = "50px"

            # Cria o texto da legenda formatado em markdown
            legend_text = f"<div style='background-color: #FFF; width: {legend_width}; height: {legend_height}; display: flex; justify-content: center; align-items: center; font-size: 16px; font-weight: bold;'>\
                                   <span style='background-color: #35B019; width: 20px; height: 20px; margin-right: 10px;'></span>{legend_colors['green']}\
                                   <span style='background-color: #F8C206; width: 20px; height: 20px; margin-right: 10px; margin-left: 20px;'></span>{legend_colors['yellow']}\
                                   <span style='background-color: #B12228; width: 20px; height: 20px; margin-right: 10px; margin-left: 20px;'></span>{legend_colors['red']}\
                               </div>"
            m = folium.Map(location=[28.377625, -81.56505], zoom_start=13, tiles=real_world, )
            fantasyland.add_to(m)
            shadownland.add_to(m)
            neverland.add_to(m)
            folium.LayerControl(position='topleft').add_to(m)  # Adicionar legenda
            parques2 = merged_df["Park Name"].unique().tolist()  # Obter lista única de parques e adicionar a opção "All"
            parques2.insert(0, "All")
            col1, col2, col3 = st.columns(3)
            with col1:
                nome_parque2 = st.selectbox("Choose a Park Name", parques2, index=0)
            with col2:
                if nome_parque2 == "All":  # Criar filtro de lista para o nome da land
                    selected_land_name = "All"
                    land_names = ["All"]
                    st.selectbox("Choose a Land Name", land_names, key="land")
                else:
                    land_names = merged_df[merged_df["Park Name"] == nome_parque2]['Land'].unique().tolist()
                    land_names.insert(0, 'All')
                    selected_land_name = st.selectbox('Choose a Land Name:', land_names, key="land")
            if nome_parque2 == "All":  # Filtrar DataFrame pelo nome do parque e nome da land selecionados
                df_filtrado = merged_df
            else:
                if selected_land_name == "All":
                    df_filtrado = merged_df[merged_df["Park Name"] == nome_parque2]
                else:
                    df_filtrado = merged_df[
                        (merged_df["Park Name"] == nome_parque2) & (merged_df["Land"] == selected_land_name)]
            with col3:
                ride_names = df_filtrado["Ride Name"].unique().tolist()
                ride_names.insert(0, "All")
                selected_ride_name = st.selectbox("Choose an Attraction", ride_names)
                if selected_ride_name != "All":
                    df_filtrado = df_filtrado[df_filtrado["Ride Name"] == selected_ride_name]

            use_slider = st.checkbox('Use Slider',
                                     value=False)  # Adiciona o slider apenas se o checkbox estiver selecionado
            st.markdown(legend_text, unsafe_allow_html=True)
            if use_slider:
                if selected_ride_name != "All":
                    df_filtrado = df_filtrado[df_filtrado["Ride Name"] == selected_ride_name]
                min_value = 0  # Define o intervalo de tempo do slider
                max_value = 100
                step = 15
                selected_interval = st.slider('Select an interval of 15 minutes:', min_value, max_value, (0, 100), step)
                start_time = selected_interval[0]  # Calcula o intervalo de tempo correspondente
                end_time = selected_interval[1]  # Filtra os dados de acordo com o intervalo de tempo selecionado
                df_filtrado = df_filtrado[(df_filtrado["wait_time"] >= start_time) & (df_filtrado["wait_time"] <= end_time)]
            else:
                st.markdown('<style>div.row-widget.stRadio > div{pointer-events:none;opacity:0.6;}</style>',
                            unsafe_allow_html=True)
                st.markdown('<style>div.row-widget.stCheckbox > div{opacity:0.6;}</style>', unsafe_allow_html=True)
            # Define as cores da legenda

            # Exibe a legenda abaixo do slider
            # Criar GeoDataFrame com os pontos filtrados
            gdf_filtrado = gpd.GeoDataFrame(df_filtrado,
                                            geometry=gpd.points_from_xy(df_filtrado.Longitude, df_filtrado.Latitude))

            # Obter a extensão espacial da feição filtrada
            bounds = gdf_filtrado.bounds
            for index, row in df_filtrado.iterrows():  # Iterar sobre as linhas do DataFrame e adicionar marcadores ao mapa
                if pd.isna(row["Latitude"]) or pd.isna(
                        row["Longitude"]):  # Ignorar linhas com valores faltantes na latitude ou longitude
                    continue
                icon_mnr = 'minnie_r.png'
                icon_mng = 'minnie_g.png'
                icon_mny = 'minnie_y.png'
                iconmnr = folium.features.CustomIcon(icon_mnr, icon_size=(30, 40))
                iconmng = folium.features.CustomIcon(icon_mng, icon_size=(30, 40))
                iconmny = folium.features.CustomIcon(icon_mny, icon_size=(30, 40))
                if row['wait_time'] > 50:  # Definir a cor do marcador com base no tempo de espera
                    icon = iconmnr
                elif row['wait_time'] > 15:
                    icon = iconmny
                else:
                    icon = iconmng
                popup_text = f"<b>Ride:</b> {row['Ride Name']}<br><b>Park:</b> {row['Park Name']}<br><b>Wait time:</b> {row['wait_time']} minutes"
                popup = folium.Popup(popup_text, max_width=500)

                # Criar pop-up com nome da ride, do parque e do tempo de espera

                folium.Marker(location=[row["Latitude"], row["Longitude"]], popup=popup,
                              tooltip=f"{row['Ride Name']} - {row['wait_time']} minutes ",
                              fill=True,
                              icon=icon,
                              overlay=True).add_to(m)


            m.fit_bounds([[bounds.miny.min(), bounds.minx.min()], [bounds.maxy.max(), bounds.maxx.max()]])
            # Criar um container e centralizar o elemento m dentro dele
            folium_static(m, width=915)
            df_mean = merged_df.groupby('Park Name')['wait_time'].mean().reset_index()
            # Define a cor para cada barra de acordo com o tempo médio de espera
            colors = []
            for time in df_mean['wait_time']:
                if time < 15:
                    colors.append('#35B019')
                elif time > 15 and time < 50:
                    colors.append('#F8C206')
                else:
                    colors.append('#B12228')

            # Plota um gráfico de barras horizontais com o tempo médio de espera por parque
            from matplotlib.backends.backend_agg import RendererAgg
            _lock = RendererAgg.lock

            st.subheader("Graph - Average Wait Time per Park 📈")
            st.write(" The 'Average Wait Time per Park' graph displays the average wait time for attractions in each Disney theme park, allowing visitors to choose rides with shorter wait times and optimize their fun time! ⏰🎉")

            with _lock:
                fig, ax = plt.pyplot.subplots(figsize=(15, 5))  # ajusta o tamanho da figura

                # adiciona estilo ao gráfico
                ax.barh(df_mean['Park Name'], df_mean['wait_time'], color=colors, edgecolor='black')
                ax.set_xlabel('Average Wait Time', fontsize=12)
                ax.set_ylabel('Park Name', fontsize=12)
                ax.spines['right'].set_visible(False)  # remove borda direita
                ax.spines['top'].set_visible(False)  # remove borda superior
                ax.tick_params(axis='both', labelsize=10)  # aumenta tamanho das fontes do eixo
                ax.grid(alpha=0.3, linestyle='--')  # adiciona linhas de grid com transparência
                ax.set_axisbelow(True)  # coloca o grid abaixo das barras
                canvas = plt.pyplot.get_current_fig_manager().canvas
                canvas.draw()
                image = np.frombuffer(canvas.tostring_rgb(), dtype='uint8')
                image = image.reshape(canvas.get_width_height()[::-1] + (3,))
                st.image(image)
        with tab2:
            st.write("Welcome to our Disney's choropleth map! 🎉 Here you can discover how many people are in each Land of our dreamland. 🏰🌈 With vibrant colors, we show the population density in each area, allowing you to plan your adventure and avoid the crowds. 🚶‍♂️🚶‍♀️ Join us on this magical journey and start exploring Disney World Resort today! ✨")
            # Load the data and calculate the density
            parques3 = merged_df["Park Name"].unique().tolist()  # Obter lista única de parques
            nome_parque3 = st.selectbox("Choose a Park Name", parques3, index=0, key="selectbox3")

            if nome_parque3 != "":
                bounds = merged_df[merged_df['Park Name'] == nome_parque3][['Latitude', 'Longitude']].agg(
                    [min, max]).values.tolist()

                densidade_df = merged_df[merged_df['Park Name'] == nome_parque3]
                densidade_df["densidade"] = densidade_df["capacidade"] / (densidade_df["wait_time"] / 60)
                densidade_df["densidade"] = densidade_df["densidade"].fillna(0)
                densidade_df["densidade"] = densidade_df["densidade"].replace([np.inf, -np.inf], 0)
                # Group by land and sum the density
                grouped_df = densidade_df.groupby('Land')['densidade'].sum().reset_index()
                # Load the GeoJSON file with the land polygons
                with open('data/lands.geojson') as f:
                    land = json.load(f)
                # Convert to a GeoDataFrame and merge with the grouped data
                geo_df = gpd.GeoDataFrame.from_features(land)
                merged_df_land = geo_df.merge(grouped_df, on='Land')
                # Convert to UTM projection
                utm = gpd.GeoDataFrame(merged_df_land, geometry='geometry', crs='EPSG:4326').to_crs('EPSG:32616')
                # Calculate the density per square meter
                utm['area'] = utm.geometry.area
                utm['density_per_m2'] = utm['densidade'] / utm['area']
                # Remove rows with NaN or infinite values
                utm.replace([np.inf, -np.inf], np.nan, inplace=True)
                utm.dropna(subset=['density_per_m2'], inplace=True)
                utm = utm.to_crs(epsg=4326)
                # Create the choropleth map with Jenks Natural Breaks classification
                # Define the bins for the choropleth map
                # Plot the choropleth map
                # Convert the GeoDataFrame to GeoJSON
                utm_json = utm.to_json()
                # Create a folium map centered on the first polygon
                m = folium.Map(location=[bounds[0][0], bounds[0][1]], zoom_start=14, tiles=real_world, )
                # Add a choropleth layer to the map
                folium.Choropleth(
                    geo_data=utm_json,
                    name='Density per m²',
                    data=utm,
                    columns=['Land', 'density_per_m2'],
                    key_on='feature.properties.Land',
                    fill_color='YlOrRd',
                    fill_opacity=0.7,
                    line_opacity=0.2,
                    legend_name='Density per m²',
                    highlight=True,).add_to(m)
                # Display the map
                folium_static(m, width=915)


    elif choice == 'Magic Routes Calculator':
        st.title("🗺️ Magic Routes Calculator ⏰")
        st.write("With the Magic Routes Calculator, you can choose your favorite park and discover the attractions you want to visit 🎢🎡🏰. The map shows the estimated time to travel the route of each attraction, along with the current wait time ⏰. But don't worry, we've also included extra time so you can take your photos with your favorite Disney characters! 📷👨‍👧‍👦💫 Use our map to plan your perfect day at the park and make the most of your Disney experience! 🎉🌟")
        parques = df_atracoes["Park Name"].unique().tolist()  # Obter lista única de parques
        col1, col2 = st.columns(2)
        with col1:
            nome_parque = st.selectbox("Choose a Park Name", parques)
        with col2:
            ride_names = merged_df[merged_df["Park Name"] == nome_parque]["Ride Name"].unique().tolist()
            selected_ride_names = st.multiselect("Choose the Attractions", sorted(ride_names))
            df_filtrado = merged_df[
                (merged_df["Park Name"] == nome_parque) & (merged_df["Ride Name"].isin(selected_ride_names))]
        if len(selected_ride_names) > 0:
            gdf_filtrado = gpd.GeoDataFrame(df_filtrado,geometry=gpd.points_from_xy(df_filtrado.Longitude, df_filtrado.Latitude))

        # Obter a extensão espacial da feição filtrada
            bounds = gdf_filtrado.bounds
            m = folium.Map(location=[28.377625, -81.56505], zoom_start=13, tiles=monochrome)

        # Iterar sobre as linhas do DataFrame filtrado e adicionar marcadores ao mapa
            for index, row in gdf_filtrado.iterrows():
                if pd.isna(row["Latitude"]) or pd.isna(row["Longitude"]):
                    continue  # Ignorar linhas com valores faltantes na latitude ou longitude
                icon_mk = 'mickey.png'
                iconmk = folium.features.CustomIcon(icon_mk, icon_size=(30, 40))
                popup_text = f"<b>Ride:</b> {row['Ride Name']}<br><b>Park:</b> {row['Park Name']}<br><b>Land:</b> {row['Land']}"  # Personalizar o popup
                popup = folium.Popup(popup_text, max_width=500)
                folium.Marker(location=[row["Latitude"], row["Longitude"]], popup=popup,
                              icon=iconmk).add_to(m)


        # Definir zoom para a extensão espacial da feição filtrada
        # Definir zoom para a extensão espacial da feição filtrada
            m.fit_bounds([[bounds.miny.min(), bounds.minx.min()], [bounds.maxy.max(), bounds.maxx.max()]])
        # Exibir mapa
            folium.LayerControl(position='topleft').add_to(m)
        # Substitua 'sua_chave_de_api' pela sua chave de API do Google Maps
            gmaps = googlemaps.Client(key='AIzaSyAWOd-oTM2yFXrlrvFDzru1hbFk2yeIXQE')
        # Coordenadas de origem e destino
            start = (df_filtrado.iloc[0].Latitude, df_filtrado.iloc[0].Longitude)
            end = (df_filtrado.iloc[-1].Latitude, df_filtrado.iloc[-1].Longitude)

        # Criar lista de coordenadas intermediárias
            waypoints = []
            for _, row in df_filtrado.iterrows():
                if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
                    waypoints.append((row['Latitude'], row['Longitude']))
        # Calcular rota
            now = datetime.now()
            directions_result = gmaps.directions(start, end, waypoints=waypoints, mode='walking', departure_time=now, optimize_waypoints=True)

        # Obter a polyline da rota
            route_polyline = directions_result[0]['overview_polyline']['points']
            route_coordinates = polyline.decode(route_polyline)


        # Criar linha de rota com coordenadas da rota

            route_line = folium.PolyLine(locations=route_coordinates, color='#FFC62E', weight=5)

        # Adicionar linha de rota ao mapa
            route_line.add_to(m)
            tempo_rota = directions_result[0]['legs'][0]['duration']['text']
            total_wait_time = df_filtrado["wait_time"].sum()
            tempo_rota = directions_result[0]['legs'][0]['duration']['text']
            tempo_total = str(timedelta(seconds=int(total_wait_time) + int(directions_result[0]['legs'][0]['duration']['value'])))
            st.write(f"🕒 <span style='font-size:24px;font-weight:bold;'>Total route time (including wait time): {total_wait_time + 15}</span>", unsafe_allow_html=True)
            folium_static(m, width=915)
            # Plota um gráfico de barras horizontais com o tempo médio de espera por parque
            from matplotlib.backends.backend_agg import RendererAgg
            _lock = RendererAgg.lock

            if not df_filtrado.empty:
                st.subheader("Graph - Average Wait Time per Ride 📈")
                st.markdown("The 'Average Wait Time per Ride' graph displays the average wait time for attractions in each Disney theme park, allowing visitors to choose rides with shorter wait times and optimize their fun time! ⏰🎉")
                with _lock:
                    colors = []
                    ride_names = [name[:20] + '...' if len(name) > 20 else name for name in
                                  df_filtrado['Ride Name'].tolist()]
                    for time in df_filtrado['wait_time']:
                        if time < 15:
                            colors.append('#35B019') #g
                        elif time > 15 and time < 50:
                            colors.append('#F8C206')
                        else:
                            colors.append('#B12228')
                    fig, ax = plt.pyplot.subplots(figsize=(15, 4))  # ajusta o tamanho da figura
                    ax.barh(y=ride_names, width=df_filtrado['wait_time'], color=colors, edgecolor='#12194A')
                    ax.set_xlabel('Average Wait Time', fontsize=10)
                    ax.spines['right'].set_visible(False)
                    ax.spines['top'].set_visible(False)
                    ax.tick_params(axis='both', labelsize=10)
                    ax.grid(alpha=0.3, linestyle='--')
                    ax.set_axisbelow(True)
                    for i, v in enumerate(df_filtrado['wait_time']):
                        ax.text(v + 0.5, i - 0.1, str(v), fontsize=8)
                    canvas = plt.pyplot.get_current_fig_manager().canvas
                    canvas.draw()
                    image = np.frombuffer(canvas.tostring_rgb(), dtype='uint8')
                    image = image.reshape(canvas.get_width_height()[::-1] + (3,))
                    st.image(image)

            else:
                st.warning("Please select at least one attraction to display the graph.")


        else:
            st.write("Select at least one attraction to display the map.")

    elif choice == 'About Disney World Resorts':

        st.title("🏰✨🎢 Welcome to the magical world of Disney! 🌟🎠🦁")
        # Define the URL for the request
        st.write('In Orlando, there are four Disney theme parks that offer unforgettable experiences for visitors of all ages')
        st.subheader('1. Magic Kingdom')
        st.image('https://s2.glbimg.com/grcDswhIvM5Bt3V0x6BHBY3J15A=/620x413/smart/e.glbimg.com/og/ed/f/original/2021/09/30/look_dos_personagens_2_1.jpg',caption='Magic Kingdom',width=450)
        st.write("🏰 The first park is the iconic Magic Kingdom, where you can immerse yourself in the world of classic Disney stories and enjoy thrilling rides like Splash Mountain and Pirates of the Caribbean.")
        st.subheader('2. Epcot')
        st.image('https://www.gannett-cdn.com/presto/2023/04/12/USAT/aed1c448-bb27-4ce5-9f02-a845b316eb67-EPCOT-World-Celebration-1.jpeg',caption='Epcot',width=450)
        st.write("🌍 At Epcot, you can explore the future and travel around the world in a day! From the iconic Spaceship Earth to the World Showcase pavilions, Epcot offers a unique blend of innovation and culture.")
        st.subheader("3. Disney's Hollywood Studios")
        st.image('https://upload.wikimedia.org/wikipedia/commons/b/bb/The_Great_Movie_Ride_and_Chinese_Theater_at_Walt_Disney_World.jpg', caption="Disney's Hollywood Studios", width=450)
        st.write("🎢 Disney's Hollywood Studios is a paradise for movie lovers, with thrilling rides like Tower of Terror and Rock 'n' Roller Coaster, and the immersive Star Wars: Galaxy's Edge area.")
        st.subheader("4. Disney's Animal Kingdom")
        st.image('https://cdn1.parksmedia.wdprapps.disney.com/media/blog/wp-content/uploads/2021/09/3uhbjughvewdhgty7t3u1.jpg',caption="Disney's Animal Kingdom", width=450)
        st.write("🐒 Last but not least, Disney's Animal Kingdom celebrates wildlife and nature. Take a safari through the African savanna, journey to the top of Everest, and explore the mystical world of Pandora.")
        st.write("No matter which park you choose, you're in for a magical adventure that will leave you with memories that last a lifetime!")


    elif choice == 'Theme Parks World Map':
        # Scroll to top of the page
        st.write("Oh, theme parks! They're like a magical world where the fun never ends! 🌎 In every corner of the world, there are incredible theme parks waiting to be explored. 🐬 You can dive into the depths of the ocean at SeaWorld in Orlando, 🎬 travel through time at Universal Studios in Hollywood, or even take a ride on the 'Craziest Roller Coaster in the World' at Six Flags in New Jersey. 🍔🍭 Oh, and don't forget to try the gastronomic delights, from the famous hot dogs to giant cotton candy! 🤣🎉 If you want to have fun, laugh, scream, and delight yourself, theme parks are definitely the place to be!\n\nHere, you'll find an overview of all the theme parks in the world, and you can even experiment with different cartographic views. 🗺️👀\n\n🚧 Under construction...")
        st.header("🎢Theme Parks Around the World 🎡")
        tab1, tab2 = st.tabs(["Heat Map", "Marker Map"])
        with tab1:
            st.subheader('Heat Map')
            st.write("Heat maps are like a magic wand for data visualization. They use colors to show the intensity of a certain variable in a specific map or image. Think of it like a mood ring for data! Warm colors like red or yellow indicate areas of high intensity, while cool colors like blue or green show lower intensity. Heat maps are a great way to identify patterns of concentration or dispersion in data, and they're widely used in various fields, from data analysis to marketing and geography. Plus, with today's technology, creating heat maps has never been easier, making it accessible to more people for their analysis and decision-making needs.")
            # Defina a URL da solicitação
            url = "https://queue-times.com/pt-BR/parks.json"
            # Envie a solicitação HTTP GET
            response = requests.get(url)
            # Verifique se a solicitação foi bem-sucedida
            if response.status_code == 200:
                # A solicitação foi bem-sucedida, pegue todos os parques
                parks = response.json()

                # Criar mapa centrado na latitude e longitude do primeiro parque
                latitude = float(parks[0]['parks'][0]['latitude'])
                longitude = float(parks[0]['parks'][0]['longitude'])
                mapa = folium.Map(location=[0, 0], zoom_start=1, tiles=monochrome)

                # Criar lista de pontos para o heatmap
                points = []
                for park_group in parks:
                    for parque in park_group['parks']:
                        latitude = float(parque['latitude'])
                        longitude = float(parque['longitude'])
                        points.append([latitude, longitude])

                # Adicionar o heatmap ao mapa
                heatmap = HeatMap(points)
                heatmap.add_to(mapa, name="Heat Map")
                fantasyland.add_to(mapa)
                supermario.add_to(mapa)
                totoro.add_to(mapa)
                folium.LayerControl().add_to(mapa)
                folium_static(mapa, width=915)

            else:
                # A solicitação falhou, exiba o código de erro
                print(f"A solicitação falhou com o código de erro {response.status_code}.")
        with tab2:
            st.subheader('Marker Map')
            st.write("")
            # Defina a URL da solicitação
            url = "https://queue-times.com/pt-BR/parks.json"
            # Envie a solicitação HTTP GET
            response = requests.get(url)
            # Verifique se a solicitação foi bem-sucedida
            if response.status_code == 200:
                # A solicitação foi bem-sucedida, pegue todos os parques
                parks = response.json()

                # Criar mapa centrado na latitude e longitude do primeiro parque
                latitude = float(parks[0]['parks'][0]['latitude'])
                longitude = float(parks[0]['parks'][0]['longitude'])
                mapa = folium.Map(location=[0, 0],  zoom_start=1, tiles=monochrome)

                # Adicionar marcadores para cada parque
                locations = []
                for park_group in parks:
                    for parque in park_group['parks']:
                        icon_pq= 'parques.png'
                        iconparques = folium.features.CustomIcon(icon_pq, icon_size=(30, 40))
                        latitude = float(parque['latitude'])
                        longitude = float(parque['longitude'])
                        popup = folium.Popup(park_group['name'], max_width=300)
                        folium.Marker(location=[latitude, longitude], popup=popup, icon=iconparques).add_to(mapa)
                        locations.append([latitude, longitude])
                # Adicionar o controle de camadas ao mapa
                fantasyland.add_to(mapa)
                supermario.add_to(mapa)
                totoro.add_to(mapa)
                folium.LayerControl().add_to(mapa)
                folium_static(mapa, width=915)
            else:
                # A solicitação falhou, exiba o código de erro
                print(f"A solicitação falhou com o código de erro {response.status_code}.")

    else:
        st.subheader("")
if __name__ == '__main__':
    main()
