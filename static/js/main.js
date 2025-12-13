// API Configuration
const API_BASE = window.location.origin + '/api';

// Hardcoded hospitals data - Real addresses from Bishkek
const HOSPITALS = [
    {
        id: 1,
        name: "Национальный госпиталь",
        lat: 42.875086,
        lng: 74.598375,
        address: "ул. Ахунбаева 190, Бишкек",
        ambulance_count: 8
    },
    {
        id: 2,
        name: "Городская клиническая больница №1",
        lat: 42.875144,
        lng: 74.562028,
        address: "ул. Тоголок Молдо 1, Бишкек",
        ambulance_count: 6
    },
    {
        id: 3,
        name: "Городская клиническая больница №4 (Скорая помощь)",
        lat: 42.846505,
        lng: 74.604471,
        address: "ул. Токтогула 170, Бишкек",
        ambulance_count: 12
    },
    {
        id: 4,
        name: "Национальный центр кардиологии",
        lat: 42.874136,
        lng: 74.598918,
        address: "ул. Тоголок Молдо 3, Бишкек",
        ambulance_count: 5
    },
    {
        id: 5,
        name: "Национальный онкологический центр",
        lat: 42.83965,
        lng: 74.61374,
        address: "ул. Ахунбаева 92, Бишкек",
        ambulance_count: 4
    },
    {
        id: 6,
        name: "Детская больница №3",
        lat: 42.840278,
        lng: 74.606667,
        address: "ул. Боконбаева 144, Бишкек",
        ambulance_count: 7
    },
    {
        id: 7,
        name: "Больница Ала-Тоо",
        lat: 42.837880,
        lng: 74.568470,
        address: "ул. Киевская 77, Бишкек",
        ambulance_count: 5
    },
    {
        id: 8,
        name: "Клиника Азми",
        lat: 42.883792,
        lng: 74.629818,
        address: "ул. Жибек Жолу 543, Бишкек",
        ambulance_count: 3
    },
    {
        id: 9,
        name: "Клиника Life",
        lat: 42.872714,
        lng: 74.582845,
        address: "ул. Московская 189, Бишкек",
        ambulance_count: 4
    },
    {
        id: 10,
        name: "Клиника M.A.G",
        lat: 42.868779,
        lng: 74.614392,
        address: "ул. Ибраимова 42, Бишкек",
        ambulance_count: 3
    }
];

// State
let map = null;
let selectedHospital = null;
let destinationMarker = null;
let startMarker = null;
let routeLayer = null;
let ambulanceMarker = null;
let trafficLayers = [];
let animationFrameId = null;
let streetsData = [];

// Constants
const BISHKEK_CENTER = [42.8746, 74.5698];

// Traffic color function (2GIS style)
function getTrafficColor(congestion) {
    if (congestion < 30) return '#22c55e';      // Green - Free flow
    if (congestion < 50) return '#eab308';      // Yellow - Light
    if (congestion < 70) return '#f97316';      // Orange - Moderate
    if (congestion < 90) return '#ef4444';      // Red - Heavy
    return '#991b1b';                            // Dark Red - Jam
}

function getTrafficLevel(congestion) {
    if (congestion < 30) return 'Свободно';
    if (congestion < 50) return 'Легкий трафик';
    if (congestion < 70) return 'Умеренный';
    if (congestion < 90) return 'Плотный';
    return 'Пробка';
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadHospitals();
    loadRealStreetTraffic();
    setupEventListeners();

    // Update traffic every 60 seconds
    setInterval(loadRealStreetTraffic, 60000);
});

function initMap() {
    map = L.map('map', {
        zoomControl: true,
        attributionControl: false
    }).setView(BISHKEK_CENTER, 13);

    // Dark theme map (2GIS style)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Map click handler
    map.on('click', handleMapClick);
}

function setupEventListeners() {
    document.getElementById('hospital-select').addEventListener('change', onHospitalSelect);
    document.getElementById('calculate-btn').addEventListener('click', calculateRoute);
    document.getElementById('clear-btn').addEventListener('click', clearRoute);
}

function loadHospitals() {
    const select = document.getElementById('hospital-select');
    select.innerHTML = '<option value="">Выберите больницу...</option>';

    HOSPITALS.forEach((hospital, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${hospital.name} (${hospital.ambulance_count} машин)`;
        select.appendChild(option);

        // Add hospital markers to map
        L.circleMarker([hospital.lat, hospital.lng], {
            radius: 8,
            fillColor: '#3b82f6',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.9
        })
            .bindPopup(`<b>${hospital.name}</b><br>${hospital.address}<br>Машин: ${hospital.ambulance_count}`)
            .addTo(map);
    });
}

/**
 * Load REAL street geometries from OpenStreetMap with traffic data
 * This replaces the old grid-based visualization
 */
async function loadRealStreetTraffic() {
    try {
        updateStatus('Загрузка данных о трафике...');

        // Fetch real street geometries with traffic from backend
        const response = await fetch(`${API_BASE}/traffic/streets_osm/`);
        const data = await response.json();

        if (!data.success && data.fallback) {
            console.warn('Using fallback street data');
        }

        streetsData = data.streets || [];

        // Clear existing traffic layers
        trafficLayers.forEach(layer => map.removeLayer(layer));
        trafficLayers = [];

        // Draw traffic on REAL street geometries
        drawTrafficOnStreets(streetsData);

        updateStatus(`Трафик обновлен (${streetsData.length} улиц)`);

    } catch (error) {
        console.error('Error loading street traffic:', error);
        updateStatus('Ошибка загрузки трафика');
    }
}

/**
 * Draw traffic visualization on real street geometries
 * Lines follow actual street paths, not a grid
 */
function drawTrafficOnStreets(streets) {
    streets.forEach(street => {
        const coords = street.coords;
        const congestion = street.congestion_percentage || 0;
        const color = street.color || getTrafficColor(congestion);
        const width = street.width || 4;
        const level = street.label || getTrafficLevel(congestion);
        const speed = street.average_speed || 40;

        // Create polyline for the street
        // Each street is drawn as a continuous line following its geometry
        const layer = L.polyline(coords, {
            color: color,
            weight: width,
            opacity: 0.8,
            lineCap: 'round',
            lineJoin: 'round',
            smoothFactor: 1.0
        })
            .bindPopup(`
            <div style="font-family: Inter, sans-serif;">
                <b style="font-size: 14px;">${street.name}</b><br>
                <span style="color: ${color}; font-weight: 600;">● ${level}</span><br>
                Загруженность: ${congestion}%<br>
                Средняя скорость: ${speed} км/ч
            </div>
        `)
            .addTo(map);

        trafficLayers.push(layer);
    });
}

function onHospitalSelect(e) {
    const index = e.target.value;
    if (index === '') {
        selectedHospital = null;
        if (startMarker) {
            map.removeLayer(startMarker);
            startMarker = null;
        }
        document.getElementById('calculate-btn').disabled = true;
        return;
    }

    selectedHospital = HOSPITALS[index];

    // Remove old start marker
    if (startMarker) map.removeLayer(startMarker);

    // Add new start marker
    const icon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        shadowSize: [41, 41]
    });

    startMarker = L.marker([selectedHospital.lat, selectedHospital.lng], { icon })
        .addTo(map)
        .bindPopup(`<b>${selectedHospital.name}</b><br>Точка старта`)
        .openPopup();

    map.flyTo([selectedHospital.lat, selectedHospital.lng], 14);

    checkCanCalculate();
}

function handleMapClick(e) {
    if (!selectedHospital) {
        showError('Сначала выберите больницу');
        return;
    }

    setDestination(e.latlng);
}

function setDestination(latlng) {
    // Remove old destination marker
    if (destinationMarker) map.removeLayer(destinationMarker);

    // Add new destination marker
    const icon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        shadowSize: [41, 41]
    });

    destinationMarker = L.marker(latlng, { icon })
        .addTo(map)
        .bindPopup('Пункт назначения')
        .openPopup();

    document.getElementById('destination-input').value =
        `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`;

    checkCanCalculate();
}

function checkCanCalculate() {
    const canCalculate = selectedHospital && destinationMarker;
    document.getElementById('calculate-btn').disabled = !canCalculate;
}

async function calculateRoute() {
    if (!selectedHospital || !destinationMarker) return;

    const btn = document.getElementById('calculate-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="loading"></div><span>Расчет...</span>';

    updateStatus('Расчет оптимального маршрута...');

    try {
        const destLatLng = destinationMarker.getLatLng();

        // Use our Backend API with ML Traffic Prediction
        const response = await fetch(`${API_BASE}/routes/calculate/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_lat: selectedHospital.lat,
                start_lng: selectedHospital.lng,
                end_lat: destLatLng.lat,
                end_lng: destLatLng.lng,
                alternatives: 3
            })
        });

        const data = await response.json();

        if (data.routes && data.routes.length > 0) {
            // Find recommended route or default to first
            const bestRoute = data.routes.find(r => r.is_recommended) || data.routes[0];

            drawRoute(bestRoute);
            showRouteInfo(bestRoute);
            startAmbulanceAnimation(bestRoute);

            const delay = bestRoute.traffic_delay_minutes || 0;
            const statusMsg = delay > 5
                ? `Маршрут построен (Задержка ${delay} мин)`
                : 'Оптимальный маршрут построен';

            updateStatus(statusMsg, 'enroute');
        } else {
            showError('Маршрут не найден');
        }
    } catch (error) {
        showError('Ошибка расчета маршрута');
        console.error(error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Рассчитать маршрут</span>';
    }
}

function drawRoute(route) {
    // Remove old route
    if (routeLayer) map.removeLayer(routeLayer);

    // Draw new route (blue line on top of traffic)
    routeLayer = L.geoJSON(route.geometry, {
        style: {
            color: '#3b82f6',
            weight: 6,
            opacity: 0.9,
            lineCap: 'round',
            zIndex: 1000
        }
    }).addTo(map);

    // Fit map to route
    map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });
}

function showRouteInfo(route) {
    // Use ML predicted values if available, otherwise fallback
    const distance = (route.distance / 1000).toFixed(1);

    // Check for ML prediction data
    let duration, durationText, extraInfo = '';

    if (route.traffic_aware_duration_minutes) {
        // We have specific ML prediction
        const trafficMinutes = route.traffic_aware_duration_minutes;
        const minTime = route.min_time_minutes;
        const maxTime = route.max_time_minutes;
        const confidence = route.confidence || 0;
        const speed = route.average_speed || 0;

        duration = Math.round(trafficMinutes) || 0;

        const minT = Math.round(minTime) || 0;
        const maxT = Math.round(maxTime) || 0;

        if (minT === maxT) {
            durationText = `${minT}`;
        } else {
            durationText = `${minT}-${maxT}`;
        }

        // Traffic badge color
        let badgeClass = 'badge-success';
        if (route.quality === 'fair') badgeClass = 'badge-warning';
        if (route.quality === 'poor') badgeClass = 'badge-danger';

        extraInfo = `
            <div style="margin-top: 10px; font-size: 13px; color: #666; border-top: 1px solid #eee; padding-top: 8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span>Пробки:</span>
                    <span class="badge ${badgeClass}" style="padding: 2px 6px; border-radius: 4px; font-size: 11px;">
                        ${route.traffic_delay_minutes > 0 ? '+' + route.traffic_delay_minutes + ' мин' : 'Нет'}
                    </span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span>Ср. скорость:</span>
                    <strong>${speed} км/ч</strong>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span>Точность ML:</span>
                    <strong>${Math.round(confidence)}%</strong>
                </div>
            </div>
        `;
    } else {
        // Fallback to standard OSRM duration
        duration = Math.round(route.duration / 60);
        durationText = duration;
    }

    document.getElementById('route-distance').innerHTML =
        `${distance}<span class="stat-unit">км</span>`;

    document.getElementById('route-duration').innerHTML =
        `${durationText}<span class="stat-unit">мин</span>`;

    // Insert extra info if container exists or append it
    let infoContainer = document.getElementById('route-extra-info');
    if (!infoContainer) {
        infoContainer = document.createElement('div');
        infoContainer.id = 'route-extra-info';
        document.getElementById('route-info').appendChild(infoContainer);
    }
    infoContainer.innerHTML = extraInfo;

    document.getElementById('route-info').style.display = 'block';
}

function startAmbulanceAnimation(route) {
    // Remove old ambulance
    if (ambulanceMarker) map.removeLayer(ambulanceMarker);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);

    const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);

    const ambulanceIcon = L.divIcon({
        html: '<div class="ambulance-marker" style="font-size: 40px; line-height: 1; transform: translate(-50%, -50%);">🚑</div>',
        className: 'ambulance-emoji-icon',
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    });

    ambulanceMarker = L.marker(coordinates[0], {
        icon: ambulanceIcon,
        zIndexOffset: 2000
    }).addTo(map);

    let index = 0;
    const animate = () => {
        if (index < coordinates.length) {
            ambulanceMarker.setLatLng(coordinates[Math.floor(index)]);
            index += 0.5;
            animationFrameId = requestAnimationFrame(animate);
        } else {
            updateStatus('Скорая прибыла в пункт назначения', 'active');
        }
    };

    animate();
}

function clearRoute() {
    // Remove markers
    if (destinationMarker) {
        map.removeLayer(destinationMarker);
        destinationMarker = null;
    }
    if (startMarker) {
        map.removeLayer(startMarker);
        startMarker = null;
    }
    if (routeLayer) {
        map.removeLayer(routeLayer);
        routeLayer = null;
    }
    if (ambulanceMarker) {
        map.removeLayer(ambulanceMarker);
        ambulanceMarker = null;
    }

    // Cancel animation
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }

    // Reset UI
    document.getElementById('hospital-select').value = '';
    document.getElementById('destination-input').value = '';
    document.getElementById('route-info').style.display = 'none';
    document.getElementById('calculate-btn').disabled = true;

    selectedHospital = null;

    // Reset map view
    map.setView(BISHKEK_CENTER, 13);

    updateStatus('Система готова', 'active');
    hideError();
}

function updateStatus(text, type = 'active') {
    document.getElementById('status-text').textContent = text;
    const dot = document.querySelector('.status-dot');
    dot.className = `status-dot ${type}`;
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.innerHTML = `
        <div class="alert alert-error">
            ⚠️ ${message}
        </div>
    `;
    setTimeout(hideError, 5000);
}

function hideError() {
    document.getElementById('error-message').innerHTML = '';
}
