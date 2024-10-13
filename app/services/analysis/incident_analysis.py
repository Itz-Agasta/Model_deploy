import os
import numpy as np
import logging
from shapely.geometry import Point
import geopandas as gpd
import requests
import json
from datetime import datetime, timedelta
import ee
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import locale
import matplotlib.dates as mdates
from io import BytesIO
import base64


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to set locale to French
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    pass

def analyze_incident_zone(lat, lon,incident_location, incident_type, start_date, end_date) -> dict:
    """
    Analyze the incident zone using satellite data.

    Returns:
    dict: A dictionary containing analysis results and plot data.
    """
    logging.info(f"Analyzing incident zone for {incident_type} at {incident_location}")
    
    
    # Create Earth Engine point and buffered area
    point = ee.Geometry.Point([lon, lat])
    buffered_point = point.buffer(500)  # 500-meter buffer

    # Convert dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.strptime(end_date, '%Y%m%d')

    # Perform satellite data analysis
    ndvi_data, ndwi_data = analyze_vegetation_and_water(point, buffered_point, start_date, end_date)
    landcover_data = analyze_land_cover(buffered_point)

    # Generate plots
    ndvi_ndwi_plot = generate_ndvi_ndwi_plot(ndvi_data, ndwi_data)
    ndvi_heatmap = generate_ndvi_heatmap(ndvi_data)
    landcover_plot = generate_landcover_plot(landcover_data)

    # Prepare textual analysis
    textual_analysis = generate_textual_analysis(ndvi_data, ndwi_data, landcover_data, incident_type)

    # Prepare return dictionary
    result = {
        'textual_analysis': textual_analysis,
        'ndvi_ndwi_plot': ndvi_ndwi_plot,
        'ndvi_heatmap': ndvi_heatmap,
        'landcover_plot': landcover_plot,
        'raw_data': {
            'ndvi': ndvi_data.to_dict(),
            'ndwi': ndwi_data.to_dict(),
            'landcover': landcover_data
        }
    }

    return result


def analyze_vegetation_and_water(point, buffered_point, start_date, end_date):
    """
    Analyze NDVI and NDWI for the given point and buffered area over the specified date range.
    """
    # Load Sentinel-2 data
    s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterBounds(buffered_point)
                     .filterDate(start_date, end_date)
                     .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 20)))

    # Calculate NDVI and NDWI
    def get_ndvi(image):
        return image.normalizedDifference(['B8', 'B4']).rename('NDVI').copyProperties(image, ['system:time_start'])

    def get_ndwi(image):
        return image.normalizedDifference(['B3', 'B8']).rename('NDWI').copyProperties(image, ['system:time_start'])

    ndvi_collection = s2_collection.map(get_ndvi)
    ndwi_collection = s2_collection.map(get_ndwi)

    # Get time series data for the point
    ndvi_timeseries = ndvi_collection.getRegion(point, scale=10).getInfo()
    ndwi_timeseries = ndwi_collection.getRegion(point, scale=10).getInfo()

    # Get mean values for the buffered area
    ndvi_mean = ndvi_collection.mean().reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffered_point,
        scale=10
    ).getInfo()['NDVI']

    ndwi_mean = ndwi_collection.mean().reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffered_point,
        scale=10
    ).getInfo()['NDWI']

    # Prepare dataframes
    dates = [ee.Date(feature[3]).format('YYYY-MM-dd').getInfo() for feature in ndvi_timeseries[1:]]
    ndvi_values = [feature[4] for feature in ndvi_timeseries[1:]]
    ndwi_values = [feature[4] for feature in ndwi_timeseries[1:]]

    df_ndvi = pd.DataFrame({'Date': dates, 'NDVI': ndvi_values, 'NDWI': ndwi_values})
    df_ndvi['Date'] = pd.to_datetime(df_ndvi['Date'])

    return df_ndvi[['Date', 'NDVI']], df_ndvi[['Date', 'NDWI']], ndvi_mean, ndwi_mean

def analyze_land_cover(buffered_point):
    """
    Analyze land cover for the given buffered area.
    """
    landcover = ee.Image('ESA/WorldCover/v200/2021').select('Map')
    sampled_data = landcover.sample(
        region=buffered_point,
        scale=10,
        projection='EPSG:4326',
        numPixels=1000
    ).aggregate_histogram('Map').getInfo()

    land_cover_types = {
        10: 'Couverture arborée', 20: 'Arbustes', 30: 'Prairies', 40: 'Terres cultivées',
        50: 'Zones bâties', 60: 'Végétation clairsemée/nue', 70: 'Neige/Glace',
        80: 'Plans d\'eau permanents', 90: 'Zones humides herbacées',
        95: 'Mangroves', 100: 'Mousses/Lichens'
    }

    landcover_data = {land_cover_types.get(int(k), 'Inconnu'): v for k, v in sampled_data.items()}
    return landcover_data

def generate_ndvi_ndwi_plot(ndvi_data, ndwi_data):
    """
    Generate a plot of NDVI and NDWI time series.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(ndvi_data['Date'], ndvi_data['NDVI'], label='NDVI (végétation)', color='green', marker='o')
    plt.plot(ndwi_data['Date'], ndwi_data['NDWI'], label='NDWI (eau)', color='blue', marker='o')

    locator = mdates.MonthLocator(interval=3)
    formatter = mdates.DateFormatter('%b %Y')
    plt.gca().xaxis.set_major_locator(locator)
    plt.gca().xaxis.set_major_formatter(formatter)

    plt.xticks(rotation=45, ha='right')
    plt.xlabel('Date')
    plt.ylabel('Valeur de l\'indice')
    plt.title('Séries temporelles du NDVI et du NDWI\nNDVI : Indice de végétation, NDWI : Indice d\'humidité')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()

    return img_str

def generate_ndvi_heatmap(ndvi_data):
    """
    Generate a heatmap of NDVI values.
    """
    ndvi_data['NumMois'] = ndvi_data['Date'].dt.month
    mois_abbr_francais = {
        1: 'Janv', 2: 'Févr', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin',
        7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'
    }
    ndvi_data['Mois'] = ndvi_data['NumMois'].map(mois_abbr_francais)
    ndvi_data['Jour'] = ndvi_data['Date'].dt.day

    heatmap_data = ndvi_data.pivot_table(index='Jour', columns='Mois', values='NDVI', aggfunc='mean')

    plt.figure(figsize=(12, 8))
    sns.heatmap(heatmap_data, cmap='YlGn', annot=False, cbar=True)
    plt.title('Carte thermique du NDVI (12 derniers mois)\nLe NDVI mesure la santé de la végétation')
    plt.xlabel('Mois')
    plt.ylabel('Jour du mois')
    plt.tight_layout()

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()

    return img_str

def generate_landcover_plot(landcover_data):
    """
    Generate a pie chart of land cover distribution.
    """
    plt.figure(figsize=(8, 8))
    wedges, texts, autotexts = plt.pie(
        landcover_data.values(),
        labels=None,
        autopct='%1.1f%%',
        startangle=140,
        textprops={'fontsize': 10}
    )
    plt.title('Distribution de la couverture terrestre (zone tampon)\nRépartition des types de surfaces')

    plt.legend(
        wedges,
        landcover_data.keys(),
        title="Types de couverture terrestre",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=10
    )

    plt.tight_layout()

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()

    return img_str

def generate_textual_analysis(ndvi_data, ndwi_data, landcover_data, incident_type):
    """
    Generate textual analysis based on the satellite data and incident type.
    """
    analysis = f"Analyse de l'incident de type '{incident_type}':\n\n"

    # NDVI analysis
    avg_ndvi = ndvi_data['NDVI'].mean()
    ndvi_trend = 'augmentation' if ndvi_data['NDVI'].iloc[-1] > ndvi_data['NDVI'].iloc[0] else 'diminution'
    analysis += f"L'indice de végétation (NDVI) moyen est de {avg_ndvi:.2f}, avec une tendance à la {ndvi_trend} sur la période analysée. "
    analysis += "Cela indique une santé de la végétation "
    if avg_ndvi > 0.5:
        analysis += "généralement bonne.\n"
    elif avg_ndvi > 0.3:
        analysis += "modérée.\n"
    else:
        analysis += "potentiellement faible ou une zone avec peu de végétation.\n"

    # NDWI analysis
    avg_ndwi = ndwi_data['NDWI'].mean()
    ndwi_trend = 'augmentation' if ndwi_data['NDWI'].iloc[-1] > ndwi_data['NDWI'].iloc[0] else 'diminution'
    analysis += f"\nL'indice d'eau (NDWI) moyen est de {avg_ndwi:.2f}, avec une tendance à la {ndwi_trend}. "
    analysis += "Cela suggère "
    if avg_ndwi > 0:
        analysis += "la présence significative d'eau dans la zone.\n"
    else:
        analysis += "une zone relativement sèche ou avec peu d'eau de surface.\n"

    # Land cover analysis
    dominant_cover = max(landcover_data, key=landcover_data.get)
    analysis += f"\nLa couverture terrestre dominante dans la zone est '{dominant_cover}', "
    analysis += f"représentant {landcover_data[dominant_cover]/sum(landcover_data.values())*100:.1f}% de la surface analysée.\n"

    # Incident-specific analysis
    if incident_type == 'Déforestation':
        analysis += "\nEn ce qui concerne la déforestation, "
        if 'Couverture arborée' in landcover_data:
            tree_cover_percent = landcover_data['Couverture arborée'] / sum(landcover_data.values()) * 100
            analysis += f"la zone présente actuellement {tree_cover_percent:.1f}% de couverture arborée. "
            if ndvi_trend == 'diminution':
                analysis += "La tendance à la baisse du NDVI pourrait indiquer une perte récente de végétation, "
                analysis += "potentiellement liée à des activités de déforestation."
            else:
                analysis += "Malgré la préoccupation de déforestation, le NDVI ne montre pas de tendance à la baisse, "
                analysis += "ce qui pourrait suggérer que la déforestation n'est pas active ou est compensée par la croissance ailleurs."
        else:
            analysis += "la zone ne semble pas avoir une couverture forestière significative actuellement. "
            analysis += "Cela pourrait indiquer une déforestation passée ou une zone naturellement non boisée."

    elif incident_type == 'Pollution de l\'eau':
        analysis += "\nConcernant la pollution de l'eau, "
        if avg_ndwi > 0:
            analysis += "la présence d'eau est confirmée par l'indice NDWI positif. "
            if ndwi_trend == 'diminution':
                analysis += "La tendance à la baisse du NDWI pourrait indiquer une réduction des surfaces d'eau, "
                analysis += "potentiellement liée à la pollution ou à d'autres facteurs environnementaux."
            else:
                analysis += "Le NDWI stable ou en augmentation suggère que la quantité d'eau de surface n'a pas diminué. "
                analysis += "Cependant, cela n'exclut pas la possibilité de pollution, qui nécessiterait des analyses in situ pour être confirmée."
        else:
            analysis += "l'indice NDWI faible suggère peu d'eau de surface dans la zone. "
            analysis += "La pollution de l'eau pourrait concerner des sources d'eau souterraines ou des cours d'eau temporaires non détectés par l'analyse satellite."

    # Add more incident-specific analyses as needed

    return analysis

def create_geojson_from_location(location, output_dir):
    """
    Create a GeoJSON file from a location string using a geocoding service.
    """
    # Use OpenStreetMap's Nominatim service for geocoding
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
    response = requests.get(geocode_url)
    if response.status_code == 200:
        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            point = Point(lon, lat)
        else:
            logging.warning(f"Could not find coordinates for {location}. Using default coordinates.")
            point = Point(0, 0)
    else:
        logging.warning(f"Geocoding service failed. Using default coordinates for {location}.")
        point = Point(0, 0)

    gdf = gpd.GeoDataFrame({'name': [location]}, geometry=[point], crs="EPSG:4326")
    
    geojson_path = os.path.join(output_dir, f"{location}.geojson")
    gdf.to_file(geojson_path, driver='GeoJSON')
    
    # Verify the created GeoJSON file
    try:
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        if 'features' not in geojson_data or not geojson_data['features']:
            raise ValueError("Invalid GeoJSON: No features found")
        if 'geometry' not in geojson_data['features'][0]:
            raise ValueError("Invalid GeoJSON: No geometry found in feature")
        if geojson_data['features'][0]['geometry']['type'] != 'Point':
            raise ValueError("Invalid GeoJSON: Geometry is not a Point")
    except Exception as e:
        logging.error(f"Error creating GeoJSON file: {str(e)}")
        raise
    
    return geojson_path