const grid = document.getElementById("grid");
const trending = document.getElementById("trending");
const hero = document.getElementById("hero");

function card(m){
 let div=document.createElement("div");
 div.className="card";

 div.innerHTML=`<img src="${m.poster}">`;

 div.onclick=()=>{
  document.getElementById("video").src=m.file_id;
 }

 return div;
}

fetch("/api/trending")
.then(r=>r.json())
.then(d=>{
 hero.style.backgroundImage=`url(${d[0].poster})`;
 d.forEach(m=>trending.appendChild(card(m)));
});

fetch("/api/movies")
.then(r=>r.json())
.then(d=>{
 d.forEach(m=>grid.appendChild(card(m)));
});