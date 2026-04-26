import axios from "axios";
import { useEffect, useRef, useState } from "react";

function Chat() {
  const [image, setImage] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!image) {
      setError("Please select an image first");
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("image", image);

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/guess",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      ).then(setResult(response.data))
      .then(
        async()=>{
            const message = await axios.post(
                "http://127.0.0.1:8000/conversation/message", 
            )
        }
      )
    } catch (err) {
      setError(err.response?.data?.message || err.message || "Upload failed");
    } finally {
      setUploading(false);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleHistory = async()=>{
    try{
        // todo : add proper auth
        const response = await axios.get("http://127.0.0.1:8000/conversation/my_convos")
        const data = await response.json()
        console.log(data)
    }catch(err){
        console.log(err)
        throw err
    }
  }
  return (
    <div>
      {/* right section */}
      <div>
        {/* chat */}
        <div></div>
        {/* upload */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
        ></input>
        <button onClick={handleUpload}>upload</button>
      </div>

      {/* left section */}
      <div>
        {/* history button */}
        <button></button>

        {/* history section hidden initially */}
        <div></div>
      </div>
    </div>
  );
}

export default Chat;
