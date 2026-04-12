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

      <div className="nav">
        <div className="logo">NETFLIX</div>
        <input placeholder="🔍 Suche..." onChange={(e)=>search(e.target.value)} />
      </div>

      {filtered[0] && (
        <div
          className="hero"
          style={{backgroundImage:`url(${filtered[0].cover})`}}
        >
          <div className="hero-overlay">
            <h1>{filtered[0].title}</h1>
            <button onClick={()=>setCurrent(filtered[0])}>▶ Play</button>
          </div>
        </div>
      )}

      {categories.map(cat => (
        <div key={cat}>
          <h2 className="category">{cat}</h2>

          <div className="row">
            {filtered
              .filter(m => m.category === cat)
              .map(m => (
                <div
                  key={m.id}
                  className="card"
                  style={{backgroundImage:`url(${m.cover})`}}
                  onClick={()=>setCurrent(m)}
                >
                  <div className="card-title">{m.title}</div>
                </div>
              ))}
          </div>
        </div>
      ))}

      {current && (
        <div className="modal">
          <video
            controls
            autoPlay
            src={API + "/stream/" + current.id}
          />
          <button onClick={()=>setCurrent(null)}>✖</button>
        </div>
      )}

    </div>
  );
}