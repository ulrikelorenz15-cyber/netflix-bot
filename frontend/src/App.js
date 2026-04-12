import { useEffect, useState, useRef } from "react";
import "./App.css";

const API = "https://DEIN-BACKEND.onrender.com";

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
      {movies[0] && (
        <div
          className="hero"
          style={{backgroundImage:`url(${movies[0].cover})`}}
        >
          <div className="hero-overlay">
            <h1>{movies[0].title}</h1>
            <button onClick={()=>setCurrent(movies[0])}>▶ Play</button>
          </div>
        </div>
      )}

      {/* ROW */}
      <div className="row">
        {movies.map(m => (
          <Card key={m.id} m={m} setCurrent={setCurrent} />
        ))}
      </div>

      {/* MODAL PLAYER */}
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

function Card({ m, setCurrent }) {
  const videoRef = useRef(null);

  const handleEnter = () => {
    const video = videoRef.current;
    if (video) {
      video.currentTime = 0;
      video.play().catch(()=>{});
    }
  };

  const handleLeave = () => {
    const video = videoRef.current;
    if (video) {
      video.pause();
    }
  };

  return (
    <div
      className="card"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onClick={()=>setCurrent(m)}
    >

      {/* VIDEO PREVIEW */}
      <video
        ref={videoRef}
        src={API + "/stream/" + m.id}
        muted
        loop
        className="preview"
      />

      {/* COVER FALLBACK */}
      <div
        className="cover"
        style={{backgroundImage:`url(${m.cover})`}}
      />

      {/* TITLE */}
      <div className="card-title">{m.title}</div>

      {/* PROGRESS */}
      <div
        className="progress"
        style={{width: m.progress + "%"}}
      ></div>

    </div>
  );
}