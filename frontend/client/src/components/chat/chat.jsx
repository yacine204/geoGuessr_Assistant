import axios from "axios"
import { Fragment, useEffect, useRef, useState } from "react"
import {
  CircleMarker,
  MapContainer,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet"
import "leaflet/dist/leaflet.css"
import { useAuth } from "../../context/AuthContext"
import styles from "./chat.module.css"

const LIVE_CORD_STORAGE_KEY = "geoseer.chat.cord.v1"
const LIVE_CORD_EVENT = "geoseer:cord-update"

function safeParseJson(value) {
  if (value == null) {
    return null
  }

  if (typeof value === "object") {
    return value
  }

  if (typeof value !== "string") {
    return value
  }

  try {
    return JSON.parse(value)
  } catch {
    return value
  }
}

function extractReplyPayload(value) {
  let current = value

  for (let depth = 0; depth < 3; depth += 1) {
    if (current == null) {
      return null
    }

    if (typeof current === "object") {
      return current
    }

    if (typeof current !== "string") {
      return null
    }

    const trimmed = current.trim()
    if (!trimmed) {
      return null
    }

    const normalized = trimmed
      .replace(/^```json\s*/i, "")
      .replace(/^```\s*/i, "")
      .replace(/```$/i, "")
      .replace(/^json\s*/i, "")
      .trim()

    const parsed = safeParseJson(normalized)

    // If parsing failed, try extracting a JSON object substring once.
    if (typeof parsed === "string" && parsed === normalized) {
      const start = normalized.indexOf("{")
      const end = normalized.lastIndexOf("}")
      if (start !== -1 && end !== -1 && end > start) {
        const sliced = normalized.slice(start, end + 1)
        const slicedParsed = safeParseJson(sliced)
        if (typeof slicedParsed === "object" && slicedParsed !== null) {
          return slicedParsed
        }
        current = slicedParsed
        continue
      }

      return null
    }

    current = parsed
  }

  return typeof current === "object" && current !== null ? current : null
}

function formatResponseText(value) {
  const parsed = safeParseJson(value)
  if (parsed && typeof parsed === "object") {
    return JSON.stringify(parsed, null, 2)
  }

  return parsed ?? ""
}

function getConversationId(conversation) {
  return conversation?.conversation_id || conversation?.id || null
}

function normalizeConversationId(conversationId) {
  const parsedId = Number(conversationId)
  return Number.isFinite(parsedId) ? parsedId : conversationId
}

function getConversationImages(conversation) {
  return Array.isArray(conversation?.images) ? conversation.images : []
}

function getConversationPreview(conversation) {
  const images = getConversationImages(conversation)
  const firstImage = images[0]
  const firstReply = firstImage?.reply?.content

  return {
    imageCount: images.length,
    firstImage,
    firstReply,
  }
}

function ReplyMapFitBounds({ points }) {
  const map = useMap()

  useEffect(() => {
    if (!Array.isArray(points) || points.length === 0) {
      return
    }

    if (points.length === 1) {
      map.setView(points[0], 6)
      return
    }

    map.fitBounds(points, { padding: [20, 20] })
  }, [map, points])

  return null
}

function normalizeReplyMapData(replyContent) {
  const parsed = extractReplyPayload(replyContent)

  const asCoordinate = (latValue, lngValue) => {
    const lat = Number(latValue)
    const lng = Number(lngValue)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return null
    }
    return [lat, lng]
  }

  const payload = parsed && typeof parsed === "object" ? parsed : null
  if (!payload) {
    return {
      payload: null,
      safePoint: null,
      primary: null,
      alternates: [],
      topCountries: [],
      hasCoordinates: false,
    }
  }

  const safe = payload.safe_geolocalization || {}
  const safePoint = asCoordinate(safe.lat ?? safe.latitude, safe.lon ?? safe.lng ?? safe.longitude)

  const alternates = Array.isArray(payload.candidates)
    ? payload.candidates
      .map((candidate, index) => {
        const point = asCoordinate(
          candidate?.lat ?? candidate?.latitude ?? candidate?.coords?.lat,
          candidate?.lon ?? candidate?.lng ?? candidate?.longitude ?? candidate?.coords?.lon ?? candidate?.coords?.lng,
        )
        if (!point) {
          return null
        }
        return {
          id: `${index}-${point[0]}-${point[1]}`,
          point,
          label: candidate?.country || candidate?.label || `Candidate ${index + 1}`,
        }
      })
      .filter(Boolean)
      .slice(0, 6)
    : []

  const topCountries = Array.isArray(payload.top_countries)
    ? payload.top_countries.filter((country) => typeof country === "string").slice(0, 10)
    : []

  const primary = safePoint || alternates[0]?.point || null

  return {
    payload,
    safePoint,
    primary,
    alternates,
    topCountries,
    hasCoordinates: Boolean(primary),
  }
}

function ReplyMiniMap({ replyContent }) {
  const mapData = normalizeReplyMapData(replyContent)
  const hasMap = mapData.hasCoordinates

  const tile = {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution: "&copy; OpenStreetMap &copy; CARTO",
    subdomains: "abcd",
  }

  const points = hasMap ? [mapData.primary, ...mapData.alternates.map((alt) => alt.point)] : []

  return (
    <div style={{ marginTop: "8px" }}>
      {hasMap ? (
        <div style={{ border: "1px solid rgba(60, 60, 60, 0.2)", borderRadius: "8px", overflow: "hidden", background: "#eef3f8" }}>
          <MapContainer
            center={mapData.primary}
            zoom={6}
            style={{ height: "150px", width: "100%", background: "#eef3f8" }}
            scrollWheelZoom={false}
          >
            <TileLayer
              url={tile.url}
              attribution={tile.attribution}
              subdomains={tile.subdomains}
            />
            {mapData.safePoint && (
              <CircleMarker
                center={mapData.safePoint}
                radius={7}
                pathOptions={{ color: "#22c55e", fillColor: "#22c55e", fillOpacity: 0.85, weight: 1.2 }}
              >
                <Tooltip>Safe geolocalization</Tooltip>
              </CircleMarker>
            )}

            {mapData.alternates.map((alternate) => (
              <Fragment key={alternate.id}>
                <Polyline
                  positions={[mapData.primary, alternate.point]}
                  pathOptions={{ color: "#f5f1e8", opacity: 0.22, weight: 1, dashArray: "4 5" }}
                />
                <CircleMarker
                  center={alternate.point}
                  radius={4}
                  pathOptions={{ color: "#d9d4c7", fillColor: "#1c1c1c", fillOpacity: 1, weight: 1 }}
                >
                  <Tooltip>{alternate.label}</Tooltip>
                </CircleMarker>
              </Fragment>
            ))}

            {!mapData.safePoint && mapData.primary && (
              <CircleMarker
                center={mapData.primary}
                radius={6}
                pathOptions={{ color: "#f5f1e8", fillColor: "#f5f1e8", fillOpacity: 0.8, weight: 1.2 }}
              >
                <Tooltip>Best candidate</Tooltip>
              </CircleMarker>
            )}

            <ReplyMapFitBounds points={points} />
          </MapContainer>
        </div>
      ) : (
        <div style={{
          border: "1px solid rgba(120, 140, 160, 0.28)",
          background: "rgba(240, 245, 250, 0.95)",
          borderRadius: "8px",
          padding: "8px 10px",
        }}>
          <p style={{ margin: 0, color: "#e7c77a", fontSize: "10px" }}>
            No accurate coordinate — showing top countries only.
          </p>
        </div>
      )}

      {!hasMap && mapData.topCountries.length > 0 && (
        <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {mapData.topCountries.map((country) => (
            <span
              key={country}
              style={{
                padding: "3px 7px",
                borderRadius: "999px",
                border: "1px solid #2a2a2a",
                background: "#141414",
                color: "#d6d6d6",
                fontSize: "9px",
              }}
            >
              {country}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function formatReplyRawJson(replyContent) {
  const parsed = extractReplyPayload(replyContent)
  if (parsed && typeof parsed === "object") {
    return JSON.stringify(parsed, null, 2)
  }
  if (typeof replyContent === "string") {
    return replyContent
  }
  return "No raw payload available"
}

function formatAssistantVisibleText(replyContent) {
  const parsed = extractReplyPayload(replyContent)

  if (parsed && typeof parsed === "object") {
    const topCountries = Array.isArray(parsed.top_countries)
      ? parsed.top_countries.filter((country) => typeof country === "string").slice(0, 3)
      : []

    const language = typeof parsed.language === "string" && parsed.language.trim()
      ? parsed.language.trim()
      : null

    const details = []
    if (language) {
      details.push(`Language: ${language}`)
    }
    if (topCountries.length > 0) {
      details.push(`Top countries: ${topCountries.join(", ")}`)
    }

    if (details.length > 0) {
      return `Geolocation analysis ready. ${details.join(" · ")}`
    }

    return "Geolocation analysis ready. Use Show more to see the full JSON payload."
  }

  if (typeof replyContent === "string" && replyContent.trim()) {
    return replyContent
  }

  return "No reply recorded for this image yet."
}

function publishCordToGlobe(payload) {
  try {
    if (!payload || typeof payload !== "object") {
      window.localStorage.removeItem(LIVE_CORD_STORAGE_KEY)
      window.dispatchEvent(new CustomEvent(LIVE_CORD_EVENT, { detail: null }))
      return
    }

    window.localStorage.setItem(LIVE_CORD_STORAGE_KEY, JSON.stringify(payload))
    window.dispatchEvent(new CustomEvent(LIVE_CORD_EVENT, { detail: payload }))
  } catch (error) {
    console.error("Failed to publish coordinates to globe", error)
  }
}

function Chat({ compact = true, panelHeight = "78vh" }) {
  const { token } = useAuth()
  
  // State Management
  const [conversations, setConversations] = useState([])
  const [selectedConversationId, setSelectedConversationId] = useState(null)
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [image, setImage] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [userAvatarUrl, setUserAvatarUrl] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [loadingConvos, setLoadingConvos] = useState(false)
  const [expandedReplies, setExpandedReplies] = useState({})
  const [forceNewConversation, setForceNewConversation] = useState(false)
  const [panelSize, setPanelSize] = useState(() => {
    const initialHeight =
      typeof window !== "undefined" && typeof panelHeight === "string" && panelHeight.endsWith("vh")
        ? Math.round((window.innerHeight * Number(panelHeight.replace("vh", ""))) / 100)
        : 700

    return {
      width: compact ? 420 : 960,
      height: Number.isFinite(initialHeight) ? initialHeight : 700,
    }
  })
  
  const fileInputRef = useRef(null)
  const resizeRef = useRef({
    mode: null,
    startX: 0,
    startY: 0,
    startWidth: 420,
    startHeight: 700,
  })

  // Axios instance with auth header
  const api = axios.create({
    baseURL: "http://127.0.0.1:8000",
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

  // Load conversations on mount
  useEffect(() => {
    if (token) {
      fetchUserConversations()
      fetchCurrentUser()
    }
  }, [token])

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get("/auth/me")
      setUserAvatarUrl(response.data?.avatar_url || null)
    } catch (err) {
      console.error("Failed to fetch current user profile", err)
    }
  }

  // Auto-dismiss messages
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [error])

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [success])

  // Fetch all user conversations
  const fetchUserConversations = async () => {
    setLoadingConvos(true)
    try {
      const response = await api.get("/conversation/my_convos")
      const nextConversations = response.data || []
      setConversations(nextConversations)

      const refreshedSelectedConversation = nextConversations.find(
        (conversation) => normalizeConversationId(getConversationId(conversation)) === normalizeConversationId(selectedConversationId)
      )

      if (refreshedSelectedConversation) {
        setSelectedConversation(refreshedSelectedConversation)
      }
    } catch (err) {
      setError("Failed to load conversations")
      console.error(err)
    } finally {
      setLoadingConvos(false)
    }
  }

  const fetchConversationDetail = async (conversationId) => {
    const normalizedConversationId = normalizeConversationId(conversationId)

    if (!normalizedConversationId) {
      return null
    }

    try {
      const response = await api.get(`/conversation/detail/${normalizedConversationId}`)
      setSelectedConversation(response.data)
      setSelectedConversationId(normalizedConversationId)
      return response.data
    } catch (err) {
      setError("Failed to load conversation details")
      console.error(err)
      return null
    }
  }

  // Load specific conversation
  const loadConversation = async (conversation) => {
    const conversationId = normalizeConversationId(getConversationId(conversation))
    setSelectedConversationId(conversationId)
    setSelectedConversation(conversation)
    setForceNewConversation(false)
    setError(null)
    setSuccess(null)
  }

  // Handle file selection
  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file is image
      if (!file.type.startsWith("image/")) {
        setError("Please select a valid image file")
        return
      }
      setImage(file)
      setError(null)
    }
  }

  // Handle image upload and message creation
  const handleUpload = async () => {
    if (!image) {
      setError("Please select an image first")
      return
    }

    setUploading(true)
    setError(null)

    try {
      // Step 1: Upload image to /guess endpoint to get guess result
      const guessFormData = new FormData()
      guessFormData.append("image", image)

      const guessResponse = await api.post("/guess", guessFormData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      })

      const guessResult = JSON.stringify(guessResponse.data)
      const guessPayload = extractReplyPayload(guessResponse.data)
      const hasCoordinates = Boolean(
        guessPayload && typeof guessPayload === "object" && (
          guessPayload.safe_geolocalization ||
          (Array.isArray(guessPayload.candidates) && guessPayload.candidates.length > 0)
        )
      )
      publishCordToGlobe(hasCoordinates ? guessPayload : null)

      // Step 2: Create or append to conversation
      const conversationFormData = new FormData()
      conversationFormData.append("image", image)
      conversationFormData.append("guess_result", guessResult)

      const shouldCreateFreshConversation = forceNewConversation

      if (!shouldCreateFreshConversation && selectedConversationId) {
        conversationFormData.append("conversation_id", String(selectedConversationId))
      }

      const conversationEndpoint = shouldCreateFreshConversation
        ? "/conversation/init"
        : "/conversation/message"

      const conversationResponse = await api.post(
        conversationEndpoint,
        conversationFormData,
        {
          headers: { "Content-Type": "multipart/form-data" }
        }
      )

      // Update UI
      const updatedConversationId = getConversationId(conversationResponse.data) || selectedConversationId
      setSelectedConversationId(normalizeConversationId(updatedConversationId))
      setForceNewConversation(false)
      setSuccess("Message sent successfully!")

      // Refresh conversation list
      await fetchUserConversations()

      // Refresh selected conversation with nested images/replies when the summary response is shallow
      await fetchConversationDetail(updatedConversationId)

      // Clear input
      setImage(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || "Failed to send message"
      setError(errorMsg)
      console.error(err)
    } finally {
      setUploading(false)
    }
  }

  // Delete conversation
  const deleteConversation = async (conversationId) => {
    const normalizedConversationId = normalizeConversationId(conversationId)

    if (!window.confirm("Are you sure you want to delete this conversation?")) {
      return
    }

    try {
      await api.delete(`/conversation/delete/${normalizedConversationId}`)
      
      // Remove from list
      setConversations(prev =>
        prev.filter(c => normalizeConversationId(c.conversation_id || c.id) !== normalizedConversationId)
      )

      // Clear if it was selected
      if (normalizeConversationId(selectedConversationId) === normalizedConversationId) {
        setSelectedConversationId(null)
        setSelectedConversation(null)
      }

      setSuccess("Conversation deleted")
    } catch (err) {
      setError("Failed to delete conversation")
      console.error(err)
    }
  }

  // Create new conversation (clear selection)
  const startNewConversation = () => {
    setSelectedConversationId(null)
    setSelectedConversation(null)
    setForceNewConversation(true)
    setImage(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const currentConversationImages = getConversationImages(selectedConversation)

  useEffect(() => {
    const onMouseMove = (event) => {
      const { mode, startX, startY, startWidth, startHeight } = resizeRef.current
      if (!mode) {
        return
      }

      const deltaX = event.clientX - startX
      const deltaY = event.clientY - startY

      const nextWidth = Math.min(980, Math.max(320, startWidth + deltaX))
      const nextHeight = Math.min(1200, Math.max(420, startHeight + deltaY))

      setPanelSize((previous) => ({
        width: mode === "right" || mode === "corner" ? nextWidth : previous.width,
        height: mode === "bottom" || mode === "corner" ? nextHeight : previous.height,
      }))
    }

    const onMouseUp = () => {
      resizeRef.current.mode = null
    }

    window.addEventListener("mousemove", onMouseMove)
    window.addEventListener("mouseup", onMouseUp)

    return () => {
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseup", onMouseUp)
    }
  }, [])

  const beginResize = (mode, event) => {
    event.preventDefault()
    resizeRef.current = {
      mode,
      startX: event.clientX,
      startY: event.clientY,
      startWidth: panelSize.width,
      startHeight: panelSize.height,
    }
  }

  const toggleReplyExpanded = (replyId) => {
    setExpandedReplies((previous) => ({
      ...previous,
      [replyId]: !previous[replyId],
    }))
  }

  return (
    <div className={styles.root} style={{ width: compact ? `${panelSize.width}px` : "100%" }}>
      <div className={styles.panel} style={{ height: `${panelSize.height}px` }}>
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>
              Assistant
            </h2>
            <p className={styles.subtitle}>
              {selectedConversation ? selectedConversation.title || `Chat ${selectedConversationId}` : "Select a convo to start"}
            </p>
          </div>

          <div className={styles.historyWrap}>
            <button
              onClick={() => setShowHistory((current) => !current)}
              className={styles.historyButton}
            >
              ☰ History
            </button>

            {showHistory && (
              <div className={styles.historyDropdown}>
                <div className={styles.historyHeader}>
                  <strong className={styles.historyHeaderTitle}>History</strong>
                  <button
                    onClick={startNewConversation}
                    className={styles.historyNewButton}
                  >
                    + New Chat
                  </button>
                </div>
                {loadingConvos ? (
                  <p className={styles.historyEmpty}>Loading...</p>
                ) : conversations.length === 0 ? (
                  <p className={styles.historyEmpty}>No conversations yet</p>
                ) : (
                  conversations.map((convo) => {
                    const convoId = convo.conversation_id || convo.id
                    const isSelected = normalizeConversationId(selectedConversationId) === normalizeConversationId(convoId)
                    const preview = getConversationPreview(convo)

                    return (
                      <div
                        key={convoId}
                        onClick={() => loadConversation(convo)}
                        className={`${styles.historyItem} ${isSelected ? styles.historyItemSelected : ""}`}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <p style={{ margin: 0, color: "#e8e8e8", fontSize: "11px" }}>
                              {convo.title || `Chat ${convoId}`}
                            </p>
                            <p style={{ margin: "3px 0 0 0", color: "#9a9a9a", fontSize: "9px" }}>
                              {new Date(convo.created_at).toLocaleDateString()} · {preview.imageCount} image{preview.imageCount === 1 ? "" : "s"}
                            </p>
                            {preview.firstReply && (
                              <p style={{
                                margin: "4px 0 0 0",
                                color: "#7f8a9a",
                                fontSize: "9px",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap"
                              }}>
                                {formatResponseText(preview.firstReply)}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              deleteConversation(convoId)
                            }}
                            style={{
                              border: "none",
                              background: "transparent",
                              color: "#9a9a9a",
                              cursor: "pointer",
                              fontSize: "11px"
                            }}
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        </div>

        <div className={styles.messagesArea}>
          {selectedConversation ? (
            currentConversationImages.length > 0 ? (
              currentConversationImages.map((message, idx) => {
                const userImage = message.storage_key || message.image_url
                const assistantReply = formatAssistantVisibleText(message.reply?.content)
                const replyId = message.reply?.reply_id || message.image_id || idx
                const isExpanded = Boolean(expandedReplies[replyId])
                const rawJson = formatReplyRawJson(message.reply?.content)

                return (
                  <div key={`${message.image_id || idx}`} className={styles.messageStack}>
                    <div style={{ display: "flex", justifyContent: "flex-end" }}>
                      <div className={styles.userBubble}>
                        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "6px" }}>
                          {userAvatarUrl ? (
                            <img
                              src={userAvatarUrl}
                              alt="user avatar"
                              style={{
                                width: "20px",
                                height: "20px",
                                borderRadius: "999px",
                                border: "1px solid #2a2a2a",
                                background: "#4a4a4a"
                              }}
                            />
                          ) : (
                            <div style={{
                              width: "20px",
                              height: "20px",
                              borderRadius: "999px",
                              background: "#4a4a4a",
                              color: "#fff",
                              display: "grid",
                              placeItems: "center",
                              fontSize: "9px",
                              fontWeight: 700
                            }}>
                              U
                            </div>
                          )}
                        </div>
                        {userImage ? (
                          <img
                            src={userImage}
                            alt={`user upload ${idx + 1}`}
                            style={{
                              width: "100%",
                              maxHeight: "170px",
                              objectFit: "cover",
                              borderRadius: "8px",
                              border: "1px solid #2a2a2a"
                            }}
                          />
                        ) : (
                          <p style={{ margin: 0, color: "#9a9a9a", fontSize: "11px" }}>Image unavailable</p>
                        )}
                      </div>
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-start" }}>
                      <div className={styles.assistantBubble}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                          <div style={{
                            width: "20px",
                            height: "20px",
                            borderRadius: "999px",
                            background: "#2a2a2a",
                            color: "#f5f1e8",
                            display: "grid",
                            placeItems: "center",
                            fontSize: "9px",
                            fontWeight: 700
                          }}>
                            A
                          </div>
                          <span style={{ color: "#9a9a9a", fontSize: "10px" }}>Assistant</span>
                        </div>
                        <pre style={{
                          margin: 0,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          color: "#e8e8e8",
                          fontSize: "11px",
                          lineHeight: 1.4,
                          fontFamily: "inherit"
                        }}>
                          {assistantReply}
                        </pre>
                        <ReplyMiniMap replyContent={message.reply?.content} />
                        <div style={{ marginTop: "8px" }}>
                          <button
                            onClick={() => toggleReplyExpanded(replyId)}
                            style={{
                              border: "1px solid #2a2a2a",
                              background: "#141414",
                              color: "#d0d0d0",
                              borderRadius: "6px",
                              padding: "4px 8px",
                              fontSize: "10px",
                              cursor: "pointer",
                            }}
                          >
                            {isExpanded ? "Show less" : "Show more"}
                          </button>
                        </div>

                        {isExpanded && (
                          <pre style={{
                            margin: "8px 0 0 0",
                            padding: "8px",
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            color: "#d8d8d8",
                            fontSize: "10px",
                            lineHeight: 1.35,
                            border: "1px solid #2a2a2a",
                            borderRadius: "8px",
                            background: "#111111",
                            maxHeight: "220px",
                            overflow: "auto",
                          }}>
                            {rawJson}
                          </pre>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })
            ) : (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ fontSize: "11px", color: "#9a9a9a" }}>No messages in this conversation yet</p>
              </div>
            )
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <p style={{ fontSize: "11px", color: "#9a9a9a" }}>Select a conversation or start a new one</p>
            </div>
          )}
        </div>

        <div className={styles.dock}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            disabled={uploading}
            style={{ display: "none" }}
          />

          {image && (
            <p style={{ margin: 0, color: "#9a9a9a", fontSize: "10px" }}>
              Selected: {image.name}
            </p>
          )}

          <div className={styles.dockButtons}>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className={styles.dockButton}
            >
              + Upload
            </button>
            <button
              onClick={handleUpload}
              disabled={!image || uploading}
              className={styles.dockButton}
            >
              {uploading ? "Sending..." : "Send"}
            </button>
          </div>
        </div>

        {error && (
          <div className={`${styles.alert} ${styles.alertError}`}>
            {error}
          </div>
        )}

        {success && (
          <div className={`${styles.alert} ${styles.alertSuccess}`}>
            {success}
          </div>
        )}

        {compact && (
          <>
            <div
              onMouseDown={(event) => beginResize("right", event)}
              className={styles.resizeRight}
            />
            <div
              onMouseDown={(event) => beginResize("bottom", event)}
              className={styles.resizeBottom}
            />
            <div
              onMouseDown={(event) => beginResize("corner", event)}
              className={styles.resizeCorner}
            />
          </>
        )}
      </div>
    </div>
  )
}

export default Chat