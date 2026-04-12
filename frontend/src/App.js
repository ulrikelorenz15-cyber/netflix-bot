import { useEffect, useState } from "react";
import "./App.css";

const API = "https://YOUR-BACKEND.onrender.com";

export default function App() {
  const [movies, setMovies] = useState([]);
  const [current, setCurrent] = useState(null);

  useEffect(() => {
    fetch(API + "/movies")
      .then(r => r.json())
      .then(setMovies);
  }, []);

  return (
    <div className="app">

      {/* HERO */}
      <div className="hero">
        {movies[0]?.title}
      </div>

      {/* ROW */}
      <div className="row">
        {movies.map(m => (
          <div key={m.id} className="card" onClick={() => setCurrent(m)}>
            {m.title}
            <div className="progress" style={{width: m.progress + "%"}}></div>
          </div>
        ))}
      </div>

      {/* PLAYER */}
      {current && (
        <div className="modal">
          <h1>{current.title}</h1>
          <video
            controls
            autoPlay
            src={API + "/stream/" + current.id}
            onTimeUpdate={(e)=>{
              let p = (e.target.currentTime / e.target.duration)*100;

              fetch(API + "/progress", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({
                  id: current.id,
                  progress: p
                })
              });
            }}
          />
          <button onClick={()=>setCurrent(null)}>❌</button>
        </div>
      )}

    </div>
  );
}