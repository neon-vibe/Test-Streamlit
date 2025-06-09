import os
import datetime

import streamlit as st
from streamlit_folium import st_folium
import folium
import folium.plugins
from streamlit.components.v1 import html
import geopandas as gpd
from shapely.geometry import shape

# --------------------------------------------------------------------------------
# Config: file paths for persistence
# --------------------------------------------------------------------------------
GPKG_PATH = "aois.gpkg"
GEOJSON_PATH = "aois.geojson"
PARQUET_PATH = "aois.parquet"

# --------------------------------------------------------------------------------
# Load or initialize GeoDataFrame
# --------------------------------------------------------------------------------
def load_gdf():
    if os.path.exists(GPKG_PATH):
        return gpd.read_file(GPKG_PATH)
    elif os.path.exists(GEOJSON_PATH):
        return gpd.read_file(GEOJSON_PATH)
    elif os.path.exists(PARQUET_PATH):
        return gpd.read_parquet(PARQUET_PATH)
    else:
        # empty GeoDataFrame with proper schema
        return gpd.GeoDataFrame(
            columns=["name", "timestamp", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

if "gdf" not in st.session_state:
    st.session_state.gdf = load_gdf()

# --------------------------------------------------------------------------------
# Page config & styling (same neon‐on‐dark theme)
# --------------------------------------------------------------------------------
st.title("🗺️  Draw Your Area of Interest (v2.1)")

# CSS for responsive map height
st.markdown(
    """
    <style>
      iframe[title="streamlit_folium.st_folium"] {
        height: 70vh !important;
        max-height: 800px !important;
      }
      @media (max-width: 768px) {
        iframe[title="streamlit_folium.st_folium"] {
          height: 50vh !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# JS snippet to fix Leaflet sizing
html(
    """
    <script>
      function fixMap() {
        const mapIframe = document.querySelector('iframe[title="streamlit_folium.st_folium"]');
        if (!mapIframe) return;
        mapIframe.contentWindow.dispatchEvent(new Event('resize'));
      }
      window.addEventListener('load', fixMap);
      window.addEventListener('resize', fixMap);
    </script>
    """,
    height=0,
)

# --------------------------------------------------------------------------------
# Render Folium map with drawing tools
# --------------------------------------------------------------------------------
leaflet_map = folium.Map(
    location=[52.52, 13.405],
    zoom_start=5,
    tiles="cartodbdark_matter",
)
folium.plugins.Draw(
    export=False,
    position="topleft",
    draw_options={
        "polyline": False,
        "circle": False,
        "circlemarker": False,
        "marker": False,
    },
    edit_options={"edit": False},
).add_to(leaflet_map)

output = st_folium(
    leaflet_map,
    height=600,           # overridden by CSS
    returned_objects=["all_drawings"],
)

# --------------------------------------------------------------------------------
# Handle new drawing: validate and save
# --------------------------------------------------------------------------------
if output and output.get("all_drawings"):
    last_draw = output["all_drawings"][-1]
    geom = shape(last_draw["geometry"])

    st.subheader("📝 Current Geometry")
    with st.expander("GeoJSON", expanded=False):
        st.json(last_draw["geometry"], expanded=False)

    # Rudimentary validity checks
    if geom.is_empty:
        st.error("❌ Geometry is empty. Please draw a valid polygon.")
    elif not geom.is_valid:
        st.error("❌ Geometry is invalid. Please simplify or redraw and avoid self intersections and holes.")
    else:
        default_name = f"AOI {len(st.session_state.gdf) + 1}"
        name = st.text_input("Give this AOI a name", value=default_name)
        if st.button("💾 Save AOI"):
            # Append to GeoDataFrame
            new_record = {
                "name": name,
                "timestamp": datetime.datetime.utcnow(),
                "geometry": geom,
            }
            gdf = st.session_state.gdf
            gdf = gdf.append(new_record, ignore_index=True)
            gdf.set_crs(epsg=4326, inplace=True)
            st.session_state.gdf = gdf

            # Persist to disk in three formats
            gdf.to_file(GPKG_PATH, driver="GPKG")
            gdf.to_file(GEOJSON_PATH, driver="GeoJSON")
            gdf.to_parquet(PARQUET_PATH)

            st.success(f"✅ Saved AOI '{name}' to files.")
else:
    st.info("Use the drawing tool (upper left) to sketch your Area of Interest.")

# --------------------------------------------------------------------------------
# Display and download saved AOIs
# --------------------------------------------------------------------------------
gdf = st.session_state.gdf
if not gdf.empty:
    st.subheader("📦 Saved AOIs")
    # Table of attributes (excluding geometry for clarity)
    st.dataframe(gdf.drop(columns="geometry"))
    # Quick map preview
    st.map(gdf)

    # Download buttons
    # GeoJSON
    geojson_str = gdf.to_json()
    st.download_button(
        label="⬇️ Download GeoJSON",
        data=geojson_str,
        file_name="aois.geojson",
        mime="application/geo+json",
    )
    # GeoPackage
    with open(GPKG_PATH, "rb") as f:
        gpkg_bytes = f.read()
    st.download_button(
        label="⬇️ Download GeoPackage",
        data=gpkg_bytes,
        file_name="aois.gpkg",
        mime="application/geopackage+sqlite3",
    )
    # Parquet
    with open(PARQUET_PATH, "rb") as f:
        pq_bytes = f.read()
    st.download_button(
        label="⬇️ Download Parquet",
        data=pq_bytes,
        file_name="aois.parquet",
        mime="application/octet-stream",
    )

st.caption("Built with ❤️ & neon vibes (front end only) at YourTechStartup")
