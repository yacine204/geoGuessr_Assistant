import {Routes, Route} from "react-router-dom"
import './App.css'
import Globe from './components/globe/globe'
import Login from "./components/auth/login"
import Signup from "./components/auth/signup"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Globe></Globe>}></Route>
      <Route path="/login" element={<Login></Login>}/>
      <Route path="/register" element={<Signup/>}></Route>
      {/* testing components */}
    </Routes>
  )
}

export default App
