import styles from './navMenu.module.css'

function NavMenu({
  cord,
  currentCord,
  isPaused,
  onTogglePause,
  onNextCandidate,
  onCountrySelect,
  onClearCurrentCord,
  topCountryCenters,
  selectedCountryName,
  onUnlockCountry,
}) {
  const pauseButtonLabel = isPaused ? 'Resume Rotation' : 'Pause Rotation'
  const hasCoordinateData = Boolean(
    currentCord ||
    (cord && typeof cord === 'object' && (
      (Array.isArray(cord.candidates) && cord.candidates.length > 0) ||
      (cord.safe_geolocalization && typeof cord.safe_geolocalization === 'object')
    ))
  )

  return (
    <div className={styles.container}>
      <div className={styles.innerContainer}>
        <div className={styles.buttonGroup}>
          <button 
            className={styles.button} 
            onClick={onTogglePause}
            title={pauseButtonLabel}
          >
            {pauseButtonLabel}
          </button>
          {hasCoordinateData && (
            <button 
              className={styles.button} 
              onClick={onNextCandidate}
              title="Cycle through candidate coordinates"
            >
              Next Candidate Coord
            </button>
          )}
          <button
            className={`${styles.button} ${styles.clearButton}`}
            onClick={onClearCurrentCord}
            title="Clear the current coordinates from the globe"
          >
            Clear Current Cords
          </button>
        </div>

        {hasCoordinateData && <div className={styles.title}>Top Countries</div>}

        {hasCoordinateData && (
          <div className={styles.listContainer}>
            <ul className={styles.list}>
              {topCountryCenters && topCountryCenters.length > 0 ? (
                topCountryCenters.map((country, index) => (
                  <li 
                    key={country.name} 
                    className={styles.listItem}
                    onClick={() => onCountrySelect(country)}
                    style={{
                      cursor: 'pointer',
                      opacity: selectedCountryName === country.name ? 1 : 0.8,
                      background: selectedCountryName === country.name 
                        ? 'rgba(255, 255, 255, 0.1)' 
                        : '#1a1a1a',
                    }}
                  >
                    <span style={{ marginRight: '8px', fontSize: '10px', opacity: 0.6 }}>
                      [{index + 1}/{topCountryCenters.length}]
                    </span>
                    {country.name}
                    {selectedCountryName === country.name && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          onUnlockCountry();
                        }}
                        style={{
                          marginLeft: '8px',
                          padding: '3px 8px',
                          fontSize: '10px',
                          background: '#444444',
                          border: '1px solid #666',
                          color: '#ff6b6b',
                          borderRadius: '2px',
                          cursor: 'pointer',
                          fontWeight: 'bold',
                          transition: 'all 0.2s',
                          display: 'inline-block',
                        }}
                        onMouseOver={(e) => {
                          e.target.style.background = '#555555';
                          e.target.style.borderColor = '#ff6b6b';
                        }}
                        onMouseOut={(e) => {
                          e.target.style.background = '#444444';
                          e.target.style.borderColor = '#666';
                        }}
                      >
                        UNLOCK
                      </button>
                    )}
                  </li>
                ))
              ) : (
                <li className={styles.listItem} style={{ opacity: 0.5 }}>
                  No countries available
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

export default NavMenu