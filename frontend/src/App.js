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

  const categories = [...new Set(filtered.map(m => m.category))];

  return (
    <div className="app">

      {/* NAV */}
      <div className="nav">
        <div className="logo">NETFLIX</div>
        <input placeholder="🔍 Suche..." onChange={(e)=>search(e.target.value)} />
      </div>

      {/* HERO */}
      {filtered[0] && (
        <div
          className="hero"
          style={{backgroundImage:`url(${filtered[0].cover})`}}
        >
          <div className="hero-overlay">
            <h1>{filtered[0].title}</h1>
            <p>{filtered[0].story}</p>
            <button onClick={()=>setCurrent(filtered[0])}>▶ Play</button>
          </div>
        </div>
      )}

      {/* CONTINUE WATCHING */}
      <h2 className="category">▶ Continue Watching</h2>
      <div className="row">
        {filtered
          .filter(m => m.progress > 5 && m.progress < 95)
          .map(m => (
            <Card key={m.id} m={m} setCurrent={setCurrent} />
          ))}
      </div>

      {/* KATEGORIEN */}
      {categories.map(cat => (
        <div key={cat}>
          <h2 className="category">{cat}</h2>

          <div className="row">
            {filtered
              .filter(m => m.category === cat)
              .map(m => (
                <Card key={m.id} m={m} setCurrent={setCurrent} />
              ))}
          </div>
        </div>
      ))}

      {/* MODAL */}
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

            <button onClick={()=>setCurrent(null)}>✖</button>

          </div>
        </div>
      )}

    </div>
  );
}

function Card({ m, setCurrent }) {
  return (
    <div
      className="card"
      style={{backgroundImage:`url(${m.cover})`}}
      onClick={()=>setCurrent(m)}
    >
      <div className="card-overlay">
        <span>{m.title}</span>
      </div>

      <div
        className="progress"
        style={{width: m.progress + "%"}}
      ></div>
    </div>
  );
}