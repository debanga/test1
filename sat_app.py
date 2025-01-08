import streamlit as st
import numpy as np
from datetime import datetime, timedelta
import requests
import ephem
import pandas as pd
import plotly.graph_objects as go

def get_tle_data():
    """Fetch TLE data from Celestrak"""
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    response = requests.get(url)
    tle_data = response.text.strip().split('\n')
    
    satellites = []
    for i in range(0, len(tle_data), 3):
        if i + 2 < len(tle_data):
            name = tle_data[i].strip()
            line1 = tle_data[i + 1]
            line2 = tle_data[i + 2]
            # Extract NORAD ID from line 1 (positions 3-7)
            norad_id = line1[2:7]
            satellites.append({
                'name': name,
                'norad_id': norad_id,
                'line1': line1,
                'line2': line2
            })
    return satellites

def calculate_satellite_positions(sat, observer_lat, observer_lon, times):
    """Calculate satellite positions for given times"""
    positions = []
    
    # Set up observer location
    observer = ephem.Observer()
    observer.lat = str(observer_lat)
    observer.lon = str(observer_lon)
    
    # Create satellite object
    satellite = ephem.readtle(sat['name'], sat['line1'], sat['line2'])
    
    for time in times:
        observer.date = time
        satellite.compute(observer)
        
        # Convert satellite position to lat/lon
        lat = np.degrees(satellite.sublat)
        lon = np.degrees(satellite.sublong)
        
        positions.append({
            'time': time,
            'lat': lat,
            'lon': lon
        })
    
    return positions

def create_map(positions, observer_lat, observer_lon):
    """Create an interactive map using Plotly"""
    fig = go.Figure()
    
    # Add satellite path
    fig.add_trace(go.Scattergeo(
        lon=[pos['lon'] for pos in positions],
        lat=[pos['lat'] for pos in positions],
        mode='lines+markers',
        line=dict(width=2, color='red'),
        marker=dict(size=8, color='red'),
        name='Satellite Path'
    ))
    
    # Add observer location
    fig.add_trace(go.Scattergeo(
        lon=[observer_lon],
        lat=[observer_lat],
        mode='markers',
        marker=dict(size=10, color='blue'),
        name='Observer Location'
    ))
    
    # Update layout
    fig.update_layout(
        title='Satellite Position Visualization',
        showlegend=True,
        geo=dict(
            projection_type='equirectangular',
            showland=True,
            showcountries=True,
            showocean=True,
            countrycolor='rgb(204, 204, 204)',
            landcolor='rgb(243, 243, 243)',
            oceancolor='rgb(230, 230, 250)'
        )
    )
    
    return fig

# Streamlit app
st.title('Satellite Position Tracker')

# User inputs
st.sidebar.header('Observer Location')
observer_lat = st.sidebar.number_input('Latitude', min_value=-90.0, max_value=90.0, value=28.0)
observer_lon = st.sidebar.number_input('Longitude', min_value=-180.0, max_value=180.0, value=91.0)

# Time parameters
st.sidebar.header('Time Parameters')
num_samples = st.sidebar.number_input('Number of Samples', min_value=2, max_value=50, value=10,
                                    help="Number of positions to calculate")
time_interval = st.sidebar.number_input('Time Interval (seconds)', min_value=1, max_value=3600, value=60,
                                      help="Time between each position calculation")

# Fetch satellite data
if 'satellites' not in st.session_state:
    with st.spinner('Fetching satellite data...'):
        st.session_state.satellites = get_tle_data()

# Satellite selection method
selection_method = st.radio(
    "Select satellite by:",
    ["Name", "NORAD ID"],
    help="Choose whether to select satellite by name or NORAD ID"
)

if selection_method == "Name":
    # Satellite selection by name
    selected_satellite = st.selectbox(
        'Select Satellite',
        options=[sat['name'] for sat in st.session_state.satellites],
        index=0
    )
    satellite = next(sat for sat in st.session_state.satellites if sat['name'] == selected_satellite)
else:
    # Satellite selection by NORAD ID
    norad_input = st.text_input(
        'Enter NORAD ID',
        help="Enter the 5-digit NORAD catalog number"
    )
    
    if norad_input:
        try:
            satellite = next((sat for sat in st.session_state.satellites 
                            if sat['norad_id'] == norad_input.strip()), None)
            if satellite:
                st.write(f"Selected satellite: {satellite['name']}")
            else:
                st.error("No satellite found with this NORAD ID")
        except Exception as e:
            st.error("Please enter a valid NORAD ID")

# Calculate positions
if st.button('Track Satellite'):
    if 'satellite' not in locals():
        st.error("Please select a satellite first")
    else:
        # Generate times based on user input
        current_time = datetime.utcnow()
        times = [current_time + timedelta(seconds=i*time_interval) for i in range(num_samples)]
        
        # Calculate positions
        with st.spinner('Calculating satellite positions...'):
            positions = calculate_satellite_positions(satellite, observer_lat, observer_lon, times)
            
            # Create position table
            df = pd.DataFrame(positions)
            df['time'] = df['time'].apply(lambda x: x.strftime('%H:%M:%S'))
            
            # Display tracking information
            st.subheader('Tracking Details')
            st.write(f"Tracking {satellite['name']} (NORAD ID: {satellite['norad_id']})")
            st.write(f"Total tracking duration: {(num_samples-1) * time_interval} seconds")
            st.write(f"Position updates every {time_interval} seconds")
            
            # Display data and map
            st.subheader('Position Data')
            st.dataframe(df)
            
            st.subheader('Visualization')
            fig = create_map(positions, observer_lat, observer_lon)
            st.plotly_chart(fig)

# Add information about the app
st.sidebar.markdown("""
### About
This app visualizes satellite positions based on:
- Observer's latitude and longitude
- Real-time TLE data from Celestrak
- User-defined number of samples and time intervals
- Satellite selection by name or NORAD ID
""")
