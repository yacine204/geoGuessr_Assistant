import styles from './cameraInfo.module.css'

function CameraInfo({ locationLabel }) {
  return (
    <div className={styles.container}>
      <span className={styles.label}>{locationLabel}</span>
    </div>
  )
}

export default CameraInfo