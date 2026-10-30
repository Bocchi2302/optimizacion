
  const svg=document.getElementById('plot'), body=document.getElementById('points');
  let points=[{x:-4,y:-3},{x:-2,y:-1},{x:0,y:1},{x:2,y:2},{x:4,y:4}], result=null;
  const NS='http://www.w3.org/2000/svg';
  function node(tag,attrs={}){let e=document.createElementNS(NS,tag);for(let [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e}
  let view={xmin:-5,xmax:5,ymin:-5,ymax:5};
  function X(x){return 50+(x-view.xmin)*500/(view.xmax-view.xmin)}
  function Y(y){return 550-(y-view.ymin)*500/(view.ymax-view.ymin)}
  function updateView(){
    let valid=points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
    if(!valid.length){view={xmin:-5,xmax:5,ymin:-5,ymax:5};return}
    let xs=valid.map(p=>p.x),ys=valid.map(p=>p.y);
    if(result){let left=Math.min(...xs),right=Math.max(...xs);
      ys.push(result.slope*left+result.intercept,result.slope*right+result.intercept)}
    if(xs.every(x=>x>=-5&&x<=5)&&ys.every(y=>y>=-5&&y<=5)){
      view={xmin:-5,xmax:5,ymin:-5,ymax:5};return}
    let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
    let xpad=Math.max((xmax-xmin)*.12,.5),ypad=Math.max((ymax-ymin)*.12,.5);
    view={xmin:xmin-xpad,xmax:xmax+xpad,ymin:ymin-ypad,ymax:ymax+ypad};
  }
  function draw(){updateView();svg.replaceChildren();
    const light=document.body.classList.contains('light');
    const grid=light?'#d6e6e4':'#294050',axis=light?'#32606b':'#6ba8b4',labels=light?'#58717a':'#a4bec7';
    for(let i=0;i<=10;i++){
      let xv=view.xmin+i*(view.xmax-view.xmin)/10,yv=view.ymin+i*(view.ymax-view.ymin)/10;
      svg.append(node('line',{x1:X(xv),y1:50,x2:X(xv),y2:550,stroke:grid,'stroke-width':1}));
      svg.append(node('line',{x1:50,y1:Y(yv),x2:550,y2:Y(yv),stroke:grid,'stroke-width':1}));
      let tx=node('text',{x:X(xv),y:570,'text-anchor':'middle','font-size':11,fill:labels});tx.textContent=Number(xv.toFixed(1));svg.append(tx);
      let ty=node('text',{x:34,y:Y(yv)+4,'text-anchor':'middle','font-size':11,fill:labels});ty.textContent=Number(yv.toFixed(1));svg.append(ty);
    }
    if(view.xmin<=0&&view.xmax>=0)svg.append(node('line',{x1:X(0),y1:50,x2:X(0),y2:550,stroke:axis,'stroke-width':2}));
    if(view.ymin<=0&&view.ymax>=0)svg.append(node('line',{x1:50,y1:Y(0),x2:550,y2:Y(0),stroke:axis,'stroke-width':2}));
    if(result){let x1=Math.min(...points.map(p=>p.x)),x2=Math.max(...points.map(p=>p.x));
      for(let p of result.points){svg.append(node('line',{x1:X(p.x),y1:Y(p.y),x2:X(p.x),y2:Y(p.prediction),stroke:light?'#79b7ad':'#51dcc7','stroke-width':1.5,'stroke-dasharray':'5 5',opacity:.65,class:'residual'}));}
      svg.append(node('line',{x1:X(x1),y1:Y(result.slope*x1+result.intercept),x2:X(x2),y2:Y(result.slope*x2+result.intercept),stroke:light?'#087f78':'#51dcc7','stroke-width':5,'stroke-linecap':'round',class:'regression-line'}));}
    for(let p of points)if(Number.isFinite(p.x)&&Number.isFinite(p.y))svg.append(node('circle',{cx:X(p.x),cy:Y(p.y),r:7,fill:light?'#d34c43':'#ff897c',stroke:light?'white':'#122331','stroke-width':2,class:'data-point'}));
  }
  function rows(){body.replaceChildren();points.forEach((p,i)=>{let tr=document.createElement('tr');tr.innerHTML=`<td>${i+1}</td><td><input aria-label="X del punto ${i+1}" type="number" step="any" value="${p.x}"></td><td><input aria-label="Y del punto ${i+1}" type="number" step="any" value="${p.y}"></td><td><button class="remove" aria-label="Eliminar punto ${i+1}">×</button></td>`;
    let inputs=tr.querySelectorAll('input');inputs.forEach((input,j)=>input.addEventListener('change',()=>{points[i][j===0?'x':'y']=Number(input.value);result=null;draw()}));tr.querySelector('button').onclick=()=>{points.splice(i,1);result=null;rows();draw()};body.append(tr)})}
  svg.addEventListener('click',e=>{if(points.length>=12){document.getElementById('error').textContent='Máximo 12 puntos.';return}let r=svg.getBoundingClientRect(),px=(e.clientX-r.left)*600/r.width,py=(e.clientY-r.top)*600/r.height;
    if(px<50||px>550||py<50||py>550)return;
    let x=Math.round((view.xmin+(px-50)*(view.xmax-view.xmin)/500)*10)/10;
    let y=Math.round((view.ymin+(550-py)*(view.ymax-view.ymin)/500)*10)/10;
    points.push({x,y});result=null;rows();draw()});
  document.getElementById('sample').onclick=()=>{points=[{x:0,y:0},{x:1,y:0},{x:2,y:2}];result=null;rows();draw()};
  document.getElementById('clear').onclick=()=>{points=[];result=null;rows();draw()};
  document.getElementById('add').onclick=()=>{if(points.length<12){points.push({x:0,y:0});result=null;rows();draw()}};
  function fmt(v){return Math.abs(v)<1e-8?'0':Number(v).toFixed(4).replace(/\.?0+$/,'')}
  function show(data){result=data;draw();document.getElementById('result').hidden=false;document.getElementById('steps').hidden=false;
    document.getElementById('stats').innerHTML=`<div class="stat">Pendiente<strong>${fmt(data.slope)}</strong></div><div class="stat">Intercepto<strong>${fmt(data.intercept)}</strong></div><div class="stat">Error máximo E<strong>${fmt(data.max_error)}</strong></div><div class="stat">Tablas mostradas<strong>${data.iterations.length}</strong></div>`;
    document.getElementById('formula').textContent=`Recta PL (línea verde en la gráfica): y = ${fmt(data.slope)}x ${data.intercept<0?'−':'+'} ${fmt(Math.abs(data.intercept))}`;
    let container=document.getElementById('tables');container.replaceChildren();data.iterations.forEach((step,index)=>{let details=document.createElement('details');if(index===0||index===data.iterations.length-1)details.open=true;
      let summary=document.createElement('summary');summary.textContent=`Fase ${step.phase} · tabla ${index+1} · ${step.label}`;details.append(summary);
      let wrap=document.createElement('div');wrap.className='scroll';let table=document.createElement('table');table.className='tableau';let head=document.createElement('tr');['Base',...step.columns].forEach(name=>{let th=document.createElement('th');th.textContent=name;head.append(th)});table.append(head);
      step.rows.forEach((row,r)=>{let tr=document.createElement('tr');let label=document.createElement('th');label.textContent=r===step.rows.length-1?'Z':step.basis[r];tr.append(label);row.forEach((v,c)=>{let td=document.createElement('td');td.textContent=fmt(v);if(step.pivot&&step.pivot[0]===r&&step.pivot[1]===c)td.className='pivot';tr.append(td)});table.append(tr)});wrap.append(table);details.append(wrap);container.append(details)})}
  document.getElementById('solve').onclick=async()=>{let error=document.getElementById('error');error.textContent='';try{let response=await fetch(document.querySelector('main').dataset.apiUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({points})});let data=await response.json();if(!response.ok)throw Error(data.error||'No se pudo calcular.');show(data)}catch(e){error.textContent=e.message}};
  rows();draw();

  document.getElementById('theme').onclick=()=>{document.body.classList.toggle('light');draw()};
