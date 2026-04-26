import { useState, useEffect } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
import styles from "./login.module.css"

function Signup() {
  const navigate = useNavigate()
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)
  const [user, setUser] = useState({
    pseudo: "",
    email: "",
    password: ""
  })


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

  const handleSignup = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await axios.post("http://127.0.0.1:8000/auth/register", {
        pseudo: user.pseudo,
        email: user.email,
        password: user.password
      })


      setSuccess("Account created! Logging you in...")
      localStorage.setItem("access_token", response.data.access_token)
      localStorage.setItem("user_pseudo", response.data.user.pseudo)


      setTimeout(() => {
        navigate("/")
      }, 500)
    } catch (err) {
      setLoading(false)


      if (err.response?.data?.detail) {
        const detail = err.response.data.detail

  
        if (detail.includes("Email already in use")) {
          setError("This email is already registered. Try logging in instead.")
        } else if (detail.includes("Pseudo already in use")) {
          setError("This username is already taken. Choose another.")
        } else if (err.response.status === 400) {
          setError(`${detail}`)
        } else {
          setError(`${detail}`)
        }
      } else if (err.request) {
        setError("Unable to connect to server. Please check your connection.")
      } else {
        setError("An unexpected error occurred. Please try again.")
      }
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.gradientBg}></div>

      <div className={styles.formWrapper}>
        <div className={styles.formContainer}>
          <div className={styles.header}>
            <h1 className={styles.title}>Create Account</h1>
            <p className={styles.subtitle}>Join us today</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className={`${styles.message} ${styles.error}`}>
              <span>{error}</span>
            </div>
          )}


          {success && (
            <div className={`${styles.message} ${styles.success}`}>
              <span>{success}</span>
            </div>
          )}

          <form onSubmit={handleSignup} className={styles.form}>
            <div className={styles.inputGroup}>
              <label htmlFor="pseudo" className={styles.label}>
                Username
              </label>
              <input
                id="pseudo"
                type="text"
                placeholder="your_username"
                name="pseudo"
                value={user.pseudo}
                onChange={handleChange}
                disabled={loading}
                required
                className={styles.input}
              />
            </div>

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
              disabled={loading || !user.pseudo || !user.email || !user.password}
              className={styles.submitBtn}
            >
              {loading ? (
                <>
                  <span className={styles.spinner}></span>
                  Creating account...
                </>
              ) : (
                "Sign Up"
              )}
            </button>
          </form>

          <div className={styles.footer}>
            <p className={styles.footerText}>
              Already have an account?{" "}
              <a href="/login" className={styles.link}>
                Log in here
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Signup