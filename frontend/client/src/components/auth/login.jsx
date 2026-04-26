import { useState, useEffect } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
import styles from "./login.module.css"

function Login() {
  const navigate = useNavigate()
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)
  const [user, setUser] = useState({
    email: "",
    password: ""
  })

  // Clear messages after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(""), 5000)
      return () => clearTimeout(timer)
    }
  }, [error])

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(""), 3000)
      return () => clearTimeout(timer)
    }
  }, [success])

  const handleChange = (e) => {
    const { name, value } = e.target
    setUser((prev) => ({ ...prev, [name]: value }))
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await axios.post("http://127.0.0.1:8000/auth/login", {
        email: user.email,
        password: user.password
      })

      // Success handling
      setSuccess("Welcome back! Redirecting...")
      localStorage.setItem("access_token", response.data.access_token)
      localStorage.setItem("user_email", response.data.user.email)

      // Redirect after brief delay for better UX
      setTimeout(() => {
        navigate("/")
      }, 500)
    } catch (err) {
      setLoading(false)

      // Enhanced error handling with custom messages from backend
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail

        // Map backend errors to user-friendly messages
        if (err.response.status === 401) {
          setError("❌ Invalid email or password. Please try again.")
        } else if (detail.includes("Email already in use")) {
          setError("📧 This email is already registered. Try logging in or reset your password.")
        } else if (detail.includes("Pseudo already in use")) {
          setError("👤 This username is already taken. Please choose another.")
        } else {
          setError(`⚠️ ${detail}`)
        }
      } else if (err.request) {
        setError("🌐 Unable to connect to server. Please check your connection.")
      } else {
        setError("❌ An unexpected error occurred. Please try again.")
      }
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.gradientBg}></div>

      <div className={styles.formWrapper}>
        <div className={styles.formContainer}>
          <div className={styles.header}>
            <h1 className={styles.title}>Welcome Back</h1>
            <p className={styles.subtitle}>Sign in to continue</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className={`${styles.message} ${styles.error}`}>
              <span>{error}</span>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className={`${styles.message} ${styles.success}`}>
              <span>✅ {success}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className={styles.form}>
            <div className={styles.inputGroup}>
              <label htmlFor="email" className={styles.label}>
                Email Address
              </label>
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                name="email"
                value={user.email}
                onChange={handleChange}
                disabled={loading}
                required
                className={styles.input}
              />
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="password" className={styles.label}>
                Password
              </label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                name="password"
                value={user.password}
                onChange={handleChange}
                disabled={loading}
                required
                className={styles.input}
              />
            </div>

            <button
              type="submit"
              disabled={loading || !user.email || !user.password}
              className={styles.submitBtn}
            >
              {loading ? (
                <>
                  <span className={styles.spinner}></span>
                  Logging in...
                </>
              ) : (
                "Login"
              )}
            </button>
          </form>

          <div className={styles.footer}>
            <p className={styles.footerText}>
              Don't have an account?{" "}
              <a href="/register" className={styles.link}>
                Sign up here
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login