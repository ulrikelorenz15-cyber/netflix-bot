const grid = document.getElementById("grid");
const trending = document.getElementById("trending");
const hero = document.getElementById("hero");
const player = document.getElementById("player");
const video = document.getElementById("videoPlayer");

function createCard(m){
    const div = document.createElement("div");
    div.className = "card";

    div.innerHTML = `
        <img src="${m.poster || 'https://via.placeholder.com/300x450'}">
        <div class="preview">
            <h4>${m.title}</h4>
            <p>${m.rating}</p>
        </div>
    `;

    div.onclick = () => {
        video.src = m.video_url || "";
        player.classList.remove("hidden");
    }

    return div;
}

fetch("/api/trending")
.then(r=>r.json())
.then(data=>{
    if(data.length){
        hero.style.backgroundImage = `url(${data[0].poster})`;
    }

    data.forEach(m=>{
        trending.appendChild(createCard(m));
    });
});

fetch("/api/movies")
.then(r=>r.json())
.then(data=>{
    data.forEach(m=>{
        grid.appendChild(createCard(m));
    });
});