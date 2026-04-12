const API = "https://netflix-bot-5kzk.onrender.com";

function load() {
  fetch(API + "/movies")
    .then(r => r.json())
    .then(render);
}

function render(data) {
  let html = '<div class="nav">NETFLIX</div><div class="grid">';

  data.forEach(m => {
    html += `
      <div class="card" onclick="play('${m.id}')"
        style="background-image:url(${m.cover})">
      </div>
    `;
  });

  html += '</div><video id="video" controls></video>';

  document.getElementById("app").innerHTML = html;
}

function play(id){
  document.getElementById("video").src = API + "/stream/" + id;
}

load();