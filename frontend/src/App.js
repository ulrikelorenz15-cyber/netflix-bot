import { useEffect, useState } from "react";
import "./App.css";

const API = "https://DEIN-BACKEND.onrender.com";

export default function App() {
  const [movies, setMovies] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [current, setCurrent] = useState(null);

  useEffect(() => {
    fetch(API + "/movies")
      .then(r => r.json())
      .then(data => {
        setMovies(data);
        setFiltered(data);
      });
  }, []);

  const search = (q) => {
    setFiltered(
      movies.filter(m =>
        m.title.toLowerCase().includes(q.toLowerCase())
      )
    );
  };

  return (
    <div className="app">

      {/* NAV */}
      <div className="nav">
        🎬 NETFLIX
        <input
          placeholder="🔍 Suche..."
          onChange={(e)=>search(e.target.value)}
        />
      </div>

      {/* HERO */}
      {filtered[0] && (
        <div className="hero">
          <h1>{filtered[0].title}</h1>
          <p>{filtered[0].story}</p>
        </div>
      )}

      {/* ROW */}
      <div className="row">
        {filtered.map(m => (
          <div
            key={m.id}
            className="card"
            onClick={()=>setCurrent(m)}
          >
            <div className="card-title">{m.title}</div>

            <div
              className="progress"
              style={{width: m.progress + "%"}}
            ></div>
          </div>
        ))}
      </div>

      {/* MODAL PLAYER */}
      {current && (
        <div className="modal">
          <div className="modal-content">
            <h1>{current.title}</h1>
            <p>{current.story}</p>

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

            <button onClick={()=>setCurrent(null)}>❌ Schließen</button>
          </div>
        </div>
      )}

    </div>
  );
}