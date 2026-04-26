import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import WorldData from 'geojson-world-map';
import { CITY_CENTROIDS, COUNTRY_CENTROIDS } from '../../types/regions';
import NavMenu from '../navMenu/navMenu';
import CameraInfo from '../cameraInfo/cameraInfo';
import styles from './globe.module.css';

const clamp01 = (value) => Math.min(1, Math.max(0, value));

const COUNTRY_NAME_ALIASES = {
  'united states': 'united states of america',
  usa: 'united states of america',
  'south korea': 'korea',
  'north korea': 'dem rep korea',
  russia: 'russian federation',
  'czech republic': 'czechia',
  'dominican republic': 'dominican rep',
  'bosnia and herzegovina': 'bosnia and herz',
  'central african republic': 'central african rep',
  'united arab emirates': 'u arab emirates',
  'ivory coast': "cote d'ivoire",
};

function normalizeCountryName(value) {
  if (typeof value !== 'string') return '';
  const normalized = value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return COUNTRY_NAME_ALIASES[normalized] ?? normalized;
}

function topCountryRankHue(index, total) {
  if (total <= 1) return 110 / 360;
  const t = index / (total - 1);
  const startHue = 110 / 360;
  const endHue = 0 / 360;
  return THREE.MathUtils.lerp(startHue, endHue, t);
}

function latLonToVector3(lat, lon, radius) {
  const latRad = (lat * Math.PI) / 180;
  const lonRad = (lon * Math.PI) / 180;
  const x = radius * Math.cos(latRad) * Math.cos(lonRad);
  const y = radius * Math.sin(latRad);
  const z = -radius * Math.cos(latRad) * Math.sin(lonRad);
  return new THREE.Vector3(x, y, z);
}

function readLatLon(coordinate) {
  if (Array.isArray(coordinate) && coordinate.length >= 2) {
    return { lat: Number(coordinate[0]), lon: Number(coordinate[1]) };
  }
  if (coordinate && typeof coordinate === 'object') {
    return {
      lat: Number(coordinate.lat ?? coordinate.latitude),
      lon: Number(coordinate.lon ?? coordinate.lng ?? coordinate.longitude),
    };
  }
  return { lat: NaN, lon: NaN };
}

function pointsFromCord(cord) {
  if (!cord || typeof cord !== 'object') return [];
  const mapped = [];
  const safe = cord.safe_geolocalization;
  const safeCoords = readLatLon(safe);
  if (Number.isFinite(safeCoords.lat) && Number.isFinite(safeCoords.lon)) {
    mapped.push({ coordinate: safeCoords, confidence: 1, source: 'safe' });
  }
  if (Array.isArray(cord.candidates)) {
    cord.candidates.forEach((candidate, index) => {
      const candidateCoords = readLatLon(candidate);
      if (!Number.isFinite(candidateCoords.lat) || !Number.isFinite(candidateCoords.lon)) return;
      mapped.push({
        coordinate: candidateCoords,
        confidence: Math.max(0.2, 0.85 - index * 0.12),
        source: 'candidate',
      });
    });
  }
  return mapped;
}

function topCountryCentersFromCord(cord) {
  if (!cord || typeof cord !== 'object' || !Array.isArray(cord.top_countries)) return [];
  return cord.top_countries
    .map((countryName) => {
      const center = COUNTRY_CENTROIDS[countryName];
      if (!center) return null;
      return { name: countryName, ...center };
    })
    .filter((center) => Boolean(center));
}

function nearestCityLabel(lat, lon) {
  let nearest = null;
  let nearestScore = Number.POSITIVE_INFINITY;
  Object.entries(CITY_CENTROIDS).forEach(([cityName, value]) => {
    const score = Math.hypot(value.lat - lat, value.lon - lon);
    if (score < nearestScore) {
      nearestScore = score;
      nearest = `${cityName}, ${value.country}`;
    }
  });
  return nearest ?? `Lat ${lat.toFixed(3)}, Lon ${lon.toFixed(3)}`;
}

function Globe({ cord = null }) {
  const mountRef = useRef(null);
  const focusLocationRef = useRef(null);
  const controlsRef = useRef(null);
  const isPausedRef = useRef(false);

  const defaultLocationLabel = 'Choose a section to focus the globe.';
  const [locationLabel, setLocationLabel] = useState(defaultLocationLabel);
  const [candidateIndex, setCandidateIndex] = useState(-1);
  const [isPaused, setIsPaused] = useState(false);
  const [selectedCountryName, setSelectedCountryName] = useState(null);

  const resolvedPoints = pointsFromCord(cord);
  const topCountryCenters = topCountryCentersFromCord(cord);

  const safePoint = resolvedPoints.find((point) => point?.source === 'safe');
  const candidatePoints = resolvedPoints.filter((point) => point?.source === 'candidate');

  const onGoToNextCandidate = () => {
    if (candidatePoints.length === 0) {
      setLocationLabel('No candidates available.');
      return;
    }
    const nextIndex = (candidateIndex + 1) % candidatePoints.length;
    setCandidateIndex(nextIndex);
    const { lat, lon } = readLatLon(candidatePoints[nextIndex]?.coordinate);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    focusLocationRef.current?.(lat, lon);
    setLocationLabel(`Candidate ${nextIndex + 1}/${candidatePoints.length}: ${nearestCityLabel(lat, lon)}`);
  };

  const onGoToCountry = (country) => {
    if (!country || !Number.isFinite(country.lat) || !Number.isFinite(country.lon)) {
      setLocationLabel('Country coordinates not available.');
      return;
    }
    setSelectedCountryName(country.name);
    focusLocationRef.current?.(country.lat, country.lon);
    setCandidateIndex(-1);
    setLocationLabel(`Country: ${country.name}`);
  };

  const onUnlockCountry = () => {
    if (selectedCountryName) {
      setSelectedCountryName(null);
      setLocationLabel(defaultLocationLabel);
      if (controlsRef.current) {
        const controls = controlsRef.current;
        const targetPos = { x: controls.target.x, y: controls.target.y, z: controls.target.z };
        const startTime = Date.now();
        const duration = 800;

        const animateReset = () => {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const easeProgress = progress < 0.5 ? 2 * progress * progress : -1 + (4 - 2 * progress) * progress;

          controls.target.x = targetPos.x * (1 - easeProgress);
          controls.target.y = targetPos.y * (1 - easeProgress);
          controls.target.z = targetPos.z * (1 - easeProgress);

          if (progress < 1) {
            requestAnimationFrame(animateReset);
          } else {
            controls.target.set(0, 0, 0);
            controls.autoRotate = !isPausedRef.current;
          }
        };

        animateReset();
      }
    }
  };

  const onTogglePause = () => {
    setIsPaused((prev) => {
      const next = !prev;
      isPausedRef.current = next;
      if (controlsRef.current) controlsRef.current.autoRotate = !next;
      return next;
    });
  };

  useEffect(() => {
    if (!mountRef.current) return;

    const container = mountRef.current;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#000000');

    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 3.5;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enablePan = false;
    controls.minDistance = 2;
    controls.maxDistance = 6;
    controls.autoRotate = !isPausedRef.current;
    controls.autoRotateSpeed = 0.25;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 2.2);
    sunLight.position.set(0, 0, 6);
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x8eb9ff, 0.1);
    fillLight.position.set(-4, -1, -2);
    scene.add(fillLight);

    const starsGeometry = new THREE.BufferGeometry();
    const starsCount = 3500;
    const starsPositions = new Float32Array(starsCount * 3);

    for (let i = 0; i < starsCount; i += 1) {
      const radius = THREE.MathUtils.randFloat(14, 26);
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(THREE.MathUtils.randFloatSpread(2));
      starsPositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      starsPositions[i * 3 + 1] = radius * Math.cos(phi);
      starsPositions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);
    }

    starsGeometry.setAttribute('position', new THREE.BufferAttribute(starsPositions, 3));

    const starsMaterial = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.03,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      sizeAttenuation: true,
    });

    const stars = new THREE.Points(starsGeometry, starsMaterial);
    scene.add(stars);

    const textureLoader = new THREE.TextureLoader();
    const earthDayMap = textureLoader.load('/textures/earth_daymap.jpg');
    const earthNormalMap = textureLoader.load('/textures/earth_normal.jpg');
    const earthSpecularMap = textureLoader.load('/textures/earth_specular.jpg');
    const earthCloudsMap = textureLoader.load('/textures/earth_clouds.png');

    earthDayMap.colorSpace = THREE.SRGBColorSpace;
    earthCloudsMap.colorSpace = THREE.SRGBColorSpace;

    const globeGeometry = new THREE.SphereGeometry(1, 96, 96);
    const globeMaterial = new THREE.MeshStandardMaterial({
      map: earthDayMap,
      normalMap: earthNormalMap,
      normalScale: new THREE.Vector2(0.85, 0.85),
      roughness: 0.92,
      metalness: 0.02,
      metalnessMap: earthSpecularMap,
    });

    const globe = new THREE.Mesh(globeGeometry, globeMaterial);
    const axialTilt = THREE.MathUtils.degToRad(23.4);
    const rotationAxis = new THREE.Vector3(0, 0, 1);
    globe.rotation.z = axialTilt;
    scene.add(globe);

    focusLocationRef.current = (lat, lon) => {
      const target = latLonToVector3(lat, lon, 1).applyAxisAngle(rotationAxis, axialTilt);
      controls.target.copy(target);
      camera.position.copy(target.clone().multiplyScalar(2.6));
      controls.autoRotate = !isPausedRef.current;
      controls.update();
    };

    const markerGroup = new THREE.Group();
    markerGroup.rotation.z = axialTilt;
    scene.add(markerGroup);

    const topCountriesGroup = new THREE.Group();
    topCountriesGroup.rotation.z = axialTilt;
    scene.add(topCountriesGroup);

    const markerGeometry = new THREE.SphereGeometry(0.015, 12, 12);

    resolvedPoints.forEach((entry) => {
      const { lat, lon } = readLatLon(entry?.coordinate);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

      let markerColor;
      let emissiveIntensity = 0.18;

      if (entry?.source === 'safe') {
        markerColor = new THREE.Color('#22c55e');
        emissiveIntensity = 0.25;
      } else if (entry?.source === 'candidate') {
        markerColor = new THREE.Color('#a3e635');
        emissiveIntensity = 0.2;
      } else {
        const confidence = clamp01(Number(entry?.confidence ?? 0));
        markerColor = new THREE.Color().setHSL((1 - confidence) * 0.33, 0.75, 0.62);
      }

      const markerMaterial = new THREE.MeshStandardMaterial({
        color: markerColor,
        emissive: markerColor,
        emissiveIntensity,
      });

      const marker = new THREE.Mesh(markerGeometry, markerMaterial);
      marker.position.copy(latLonToVector3(lat, lon, 1.03));
      marker.lookAt(marker.position.clone().multiplyScalar(2));
      markerGroup.add(marker);
    });

    const worldFeaturesByName = new Map(
      (WorldData?.features ?? []).map((feature) => [normalizeCountryName(feature?.properties?.name), feature]),
    );

    const addBorderLineFromRing = (ring, color) => {
      if (!Array.isArray(ring) || ring.length < 2) return;
      const ringCoordinates = [...ring];
      const first = ringCoordinates[0];
      const last = ringCoordinates[ringCoordinates.length - 1];
      if (first && last && (first[0] !== last[0] || first[1] !== last[1])) {
        ringCoordinates.push(first);
      }

      const segments = [];
      let currentSegment = [];
      let previousLon = null;

      ringCoordinates.forEach((coordinate) => {
        if (!Array.isArray(coordinate) || coordinate.length < 2) return;
        const lon = Number(coordinate[0]);
        const lat = Number(coordinate[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

        if (previousLon !== null && Math.abs(lon - previousLon) > 180 && currentSegment.length >= 2) {
          segments.push(currentSegment);
          currentSegment = [];
        }

        const point = latLonToVector3(lat, lon, 1.005);
        currentSegment.push(point.x, point.y, point.z);
        previousLon = lon;
      });

      if (currentSegment.length >= 6) {
        segments.push(currentSegment);
      }

      segments.forEach((positions) => {
        if (positions.length < 6) return;
        const borderGeometry = new THREE.BufferGeometry();
        borderGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        const borderMaterial = new THREE.LineBasicMaterial({
          color,
          transparent: true,
          opacity: 0.9,
          depthWrite: false,
        });
        const border = new THREE.Line(borderGeometry, borderMaterial);
        topCountriesGroup.add(border);
      });
    };

    topCountryCenters.forEach((center, index) => {
      const feature = worldFeaturesByName.get(normalizeCountryName(center.name));
      if (!feature?.geometry) return;

      const color = new THREE.Color().setHSL(topCountryRankHue(index, topCountryCenters.length), 0.82, 0.55);

      if (feature.geometry.type === 'Polygon') {
        feature.geometry.coordinates?.forEach((ring) => {
          addBorderLineFromRing(ring, color);
        });
        return;
      }

      if (feature.geometry.type === 'MultiPolygon') {
        feature.geometry.coordinates?.forEach((polygon) => {
          polygon?.forEach((ring) => {
            addBorderLineFromRing(ring, color);
          });
        });
      }
    });

    const cloudsGeometry = new THREE.SphereGeometry(1.015, 96, 96);
    const cloudsMaterial = new THREE.MeshStandardMaterial({
      map: earthCloudsMap,
      transparent: true,
      opacity: 0.14,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });
    const clouds = new THREE.Mesh(cloudsGeometry, cloudsMaterial);
    clouds.rotation.z = axialTilt;
    scene.add(clouds);

    let animationFrameId;
    const animate = () => {
      sunLight.position.copy(camera.position).normalize().multiplyScalar(6);
      stars.rotation.y += 0.00008;
      if (!isPausedRef.current) clouds.rotation.y += 0.0008;
      controls.update();
      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };
    animate();

    const onResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener('resize', onResize);

    return () => {
      focusLocationRef.current = null;
      controlsRef.current = null;
      window.removeEventListener('resize', onResize);
      cancelAnimationFrame(animationFrameId);
      globeGeometry.dispose();
      cloudsGeometry.dispose();
      starsGeometry.dispose();
      earthDayMap.dispose();
      earthNormalMap.dispose();
      earthSpecularMap.dispose();
      earthCloudsMap.dispose();
      globeMaterial.dispose();
      cloudsMaterial.dispose();
      starsMaterial.dispose();
      markerGeometry.dispose();
      markerGroup.children.forEach((marker) => marker.material.dispose());
      topCountriesGroup.children.forEach((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
          else child.material.dispose();
        }
      });
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) container.removeChild(renderer.domElement);
    };
  }, [cord]);

  return (
    <div className={styles.container}>
      <div ref={mountRef} className={styles.canvasContainer} />
      <div className={styles.navMenuWrapper}>
        <NavMenu
          cord={cord}
          currentCord={safePoint?.coordinate || candidatePoints[0]?.coordinate}
          isPaused={isPaused}
          onTogglePause={onTogglePause}
          onNextCandidate={onGoToNextCandidate}
          onCountrySelect={onGoToCountry}
          topCountryCenters={topCountryCenters}
          selectedCountryName={selectedCountryName}
          onUnlockCountry={onUnlockCountry}
        />
      </div>
      <div className={styles.infoPanel}>
        <CameraInfo locationLabel={locationLabel} />
      </div>
    </div>
  );
}

export default Globe;