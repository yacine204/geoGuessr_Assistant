import apiClient from './apiClient';

const ANALYZE_ENDPOINT = import.meta.env.VITE_ANALYZE_ENDPOINT || '/guess';

function normalizeNumber(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function extractCoordinates(payload) {
  const latitude =
    payload?.latitude ??
    payload?.lat ??
    payload?.safe_geolocalization?.latitude ??
    payload?.safe_geolocalization?.lat ??
    payload?.coordinates?.latitude ??
    payload?.coordinates?.lat ??
    payload?.location?.latitude ??
    payload?.location?.lat;

  const longitude =
    payload?.longitude ??
    payload?.lng ??
    payload?.safe_geolocalization?.longitude ??
    payload?.safe_geolocalization?.lng ??
    payload?.coordinates?.longitude ??
    payload?.coordinates?.lng ??
    payload?.location?.longitude ??
    payload?.location?.lng;

  const lat = normalizeNumber(latitude);
  const lng = normalizeNumber(longitude);

  return lat !== null && lng !== null ? { lat, lng } : null;
}

export function normalizeAnalysisResult(payload = {}, fileName = 'upload') {
  const topCountries = Array.isArray(payload?.top_countries)
    ? payload.top_countries.filter(Boolean)
    : [];

  const guessedCountry =
    topCountries[0] ||
    payload?.country ||
    payload?.guessed_country ||
    payload?.prediction?.country ||
    payload?.result?.country ||
    'Unknown';

  const confidenceRaw =
    payload?.confidence ??
    payload?.score ??
    payload?.probability ??
    payload?.prediction?.confidence;

  const confidence = normalizeNumber(confidenceRaw);

  const summary =
    payload?.summary ||
    payload?.analysis ||
    payload?.result?.summary ||
    payload?.content ||
    payload?.message ||
    `Analysis ready for ${fileName}. ${topCountries.length > 0 ? `Top candidates: ${topCountries.join(', ')}` : ''}`;

  const language = payload?.language || null;
  const ocrText = payload?.ocr_detections || '';

  return {
    guessedCountry,
    confidence,
    summary,
    language,
    ocrText,
    topCountries,
    yoloDetections: payload?.YOLO_detections || {},
    signDetection: payload?.sign_detection || {},
    coordinates: extractCoordinates(payload),
    raw: payload,
  };
}

export async function analyzeImage(file, onProgress) {
  const formData = new FormData();

  // Backend expects UploadFile parameter named "image".
  formData.append('image', file);

  const response = await apiClient.post(ANALYZE_ENDPOINT, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
    onUploadProgress: (event) => {
      if (!event?.total || !onProgress) {
        return;
      }

      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress(percent);
    },
  });

  return normalizeAnalysisResult(response.data, file.name);
}
