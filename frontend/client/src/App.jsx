import {Routes, Route} from "react-router-dom"
import './App.css'
import Globe from './pages/globe'
import NavMenu from "./pages/navMenu"

const sampleCord = {
    "YOLO_detections": {
        "dominant_convention": "vienna",
        "bias": 1.0
    },
    "sign_detection": {
        "detected": "vienna",
        "conf": 0.8475127816200256
    },
    "ocr_detections": "22 D34\nLe Perreux-sur-Marne, Ile-de-France\nGoogle Street View\njuil: 2022\nVoir plus de dates\nLa;\nD 34\n0108\nCHELLES\nNEuILLY\n4\nMARNE\nBOULANGER\nPATISSIER\nLA\nMALTOURNEE\nCpoottno\nPiscine\n8\n23\nPourquoi Pas?\nReq\n016\nGoogle Maps\nDudol\nDe\nJadera\n2\nJveco\natodie\nVictor =\nRue",
    "language": "fr",
    "safe_geolocalization": {
        "lon": 2.8141723333333335,
        "lat": 48.5265485
    },
    "candidates": [
        {
            "lat": 48.8406252,
            "lon": 2.5076601
        },
        {
            "lat": 49.3549458,
            "lon": 3.0344372
        },
        {
            "lat": 48.9321383,
            "lon": 1.4209125
        },
        {
            "lat": 48.961264,
            "lon": 4.3122436
        },
        {
            "lat": 43.4881697,
            "lon": 1.0792114
        }
    ],
    "top_countries": [
        "France",
        "Belgium",
        "Switzerland",
        "Germany",
        "United Kingdom",
        "Spain",
        "Netherlands",
        "Italy",
        "Russia",
        "Luxembourg"
    ]
}

function App() {

  return (
    <Routes>
      <Route path="/" element={<Globe cord={sampleCord}></Globe>}></Route>

      {/* testing components */}
      <Route path="/navmenu" element={<NavMenu cord={sampleCord}></NavMenu>}/>
    </Routes>
  )
}

export default App
