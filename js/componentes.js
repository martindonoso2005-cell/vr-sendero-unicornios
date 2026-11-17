/* Componentes A-Frame del entorno "Sendero de Unicornios VR" */

const MUNDOS = [
  { textura: '#pano-dia',       nombre: 'Dia arcoiris',      color: '#ffffff' },
  { textura: '#pano-atardecer', nombre: 'Atardecer magico',  color: '#ffe3f2' },
  { textura: '#pano-noche',     nombre: 'Noche estrellada',  color: '#c8f0ff' },
  { textura: '#pano-pastel',    nombre: 'Bosque pastel',     color: '#7a4aa8' }
];

/* Cambia el panorama de la esfera envolvente con un fundido. Teclas 1-4. */
AFRAME.registerComponent('gestor-mundos', {
  init() {
    this.actual = 0;
    this.ocupado = false;
    this.el.addEventListener('cambiar-mundo', e => this.cambiar(e.detail.mundo));
    window.addEventListener('keydown', e => {
      const n = parseInt(e.key, 10);
      if (n >= 1 && n <= MUNDOS.length) this.cambiar(n - 1);
    });
  },

  cambiar(indice) {
    if (this.ocupado || indice === this.actual) return;
    this.ocupado = true;
    const velo = document.getElementById('velo');
    const entorno = document.getElementById('entorno');
    const titulo = document.getElementById('titulo');
    velo.setAttribute('visible', true);
    velo.setAttribute('animation__in', { property: 'material.opacity', from: 0, to: 1, dur: 450, easing: 'easeInQuad' });

    setTimeout(() => {
      const m = MUNDOS[indice];
      entorno.setAttribute('material', 'src', m.textura);
      titulo.setAttribute('text', 'color', m.color);
      this.actual = indice;
      document.querySelectorAll('[esfera-mundo]').forEach(s => s.components['esfera-mundo'].marcar(indice));
      // los raycasters deben enterarse de que cambiaron los portales seleccionables
      document.querySelectorAll('[raycaster]').forEach(r => r.components.raycaster.refreshObjects());
      velo.setAttribute('animation__out', { property: 'material.opacity', from: 1, to: 0, dur: 650, easing: 'easeOutQuad' });
      setTimeout(() => { velo.setAttribute('visible', false); this.ocupado = false; }, 700);
    }, 470);
  }
});

/* Esfera "bola de cristal" texturizada con un panorama; al hacer clic viaja a ese mundo. */
AFRAME.registerComponent('esfera-mundo', {
  schema: {
    mundo: { type: 'int', default: 0 },
    textura: { type: 'string' },
    nombre: { type: 'string', default: '' }
  },

  init() {
    const el = this.el;
    const d = this.data;

    // esfera con el panorama (vista desde fuera, como un pequeno planeta)
    this.bola = document.createElement('a-entity');
    this.bola.setAttribute('geometry', 'primitive: sphere; radius: 0.32; segmentsWidth: 48; segmentsHeight: 32');
    this.bola.setAttribute('material', `shader: flat; src: ${d.textura}`);
    this.bola.setAttribute('animation__giro', 'property: rotation; to: 0 360 0; loop: true; dur: 24000; easing: linear');
    this.bola.setAttribute('animation__flotar',
      `property: position; from: 0 -0.04 0; to: 0 0.04 0; dir: alternate; loop: true; dur: ${2200 + d.mundo * 300}; easing: easeInOutSine`);
    el.appendChild(this.bola);

    // halo de cristal
    this.halo = document.createElement('a-entity');
    this.halo.setAttribute('geometry', 'primitive: sphere; radius: 0.36; segmentsWidth: 32; segmentsHeight: 24');
    this.halo.setAttribute('material', 'color: #ffffff; transparent: true; opacity: 0.12; metalness: 0.2; roughness: 0.05');
    this.bola.appendChild(this.halo);

    // anillo de seleccion
    this.anillo = document.createElement('a-entity');
    this.anillo.setAttribute('geometry', 'primitive: torus; radius: 0.42; radiusTubular: 0.008; segmentsTubular: 64');
    this.anillo.setAttribute('material', 'shader: flat; color: #ffd84d');
    this.anillo.setAttribute('rotation', '90 0 0');
    this.anillo.setAttribute('position', '0 -0.3 0');
    this.anillo.setAttribute('visible', d.mundo === 0);
    el.appendChild(this.anillo);

    // etiqueta
    const txt = document.createElement('a-entity');
    txt.setAttribute('text', `value: ${d.nombre}; align: center; width: 1.6; color: #ffffff; shader: msdf; font: https://cdn.aframe.io/examples/ui/Viga-Regular.json`);
    txt.setAttribute('position', '0 -0.6 0');
    const fondo = document.createElement('a-plane');
    fondo.setAttribute('width', 0.78); fondo.setAttribute('height', 0.13);
    fondo.setAttribute('material', 'color: #2a1a4a; opacity: 0.55; transparent: true; shader: flat');
    fondo.setAttribute('position', '0 -0.6 -0.005');
    el.appendChild(fondo);
    el.appendChild(txt);

    // vortice que gira mientras se "carga" el portal con la mirada
    this.vortice = document.createElement('a-entity');
    this.vortice.setAttribute('geometry', 'primitive: ring; radiusInner: 0.37; radiusOuter: 0.44; thetaLength: 300; segmentsTheta: 48');
    this.vortice.setAttribute('material', 'shader: flat; color: #ff9ad8; transparent: true; opacity: 0.85; side: double');
    this.vortice.setAttribute('visible', false);
    this.vortice.setAttribute('animation__girar', 'property: rotation; from: 0 0 0; to: 0 0 -360; loop: true; dur: 900; easing: linear');
    el.appendChild(this.vortice);

    // interaccion: varios cursores (raton, mirada, laseres) pueden apuntar a la vez
    this.cursores = new Set();
    if (d.mundo !== 0) this.bola.classList.add('portal'); // el mundo 0 es el inicial
    this.bola.addEventListener('mouseenter', e => {
      this.cursores.add(e.detail && e.detail.cursorEl);
      this.bola.setAttribute('animation__hover', 'property: scale; to: 1.18 1.18 1.18; dur: 200; easing: easeOutQuad');
      this.halo.setAttribute('material', 'opacity', 0.3);
    });
    this.bola.addEventListener('mouseleave', e => {
      this.cursores.delete(e.detail && e.detail.cursorEl);
      if (e.detail && e.detail.cursorEl && e.detail.cursorEl.id === 'reticula') this.cargando(false);
      if (this.cursores.size) return;
      this.bola.setAttribute('animation__hover', 'property: scale; to: 1 1 1; dur: 200; easing: easeOutQuad');
      this.halo.setAttribute('material', 'opacity', 0.12);
    });
    // "fusing": la reticula empezo la cuenta de mirada fija sobre este portal
    this.bola.addEventListener('fusing', () => this.cargando(true));
    this.bola.addEventListener('click', () => {
      this.cargando(false);
      if (!this.bola.classList.contains('portal')) return;
      el.sceneEl.emit('cambiar-mundo', { mundo: d.mundo });
    });
  },

  cargando(activo) {
    const dur = (document.getElementById('reticula').getAttribute('cursor') || {}).fuseTimeout || 1800;
    this.vortice.setAttribute('visible', activo);
    if (activo) {
      this.vortice.setAttribute('animation__crecer', `property: scale; from: 0.6 0.6 0.6; to: 1.15 1.15 1.15; dur: ${dur}; easing: easeInQuad`);
      this.halo.setAttribute('animation__brillo', `property: material.opacity; from: 0.2; to: 0.6; dur: ${dur}; easing: easeInQuad`);
    } else {
      this.vortice.removeAttribute('animation__crecer');
      this.halo.removeAttribute('animation__brillo');
    }
  },

  // el portal del mundo actual queda marcado y deja de ser seleccionable
  marcar(indice) {
    const actual = indice === this.data.mundo;
    this.anillo.setAttribute('visible', actual);
    this.bola.classList.toggle('portal', !actual);
    this.cargando(false);
    this.cursores.clear();
    this.bola.setAttribute('animation__hover', 'property: scale; to: 1 1 1; dur: 200; easing: easeOutQuad');
    this.halo.setAttribute('material', 'opacity', 0.12);
  }
});

/* Reticula de mirada: punto central + aro que se llena mientras miras fijo un portal. */
AFRAME.registerComponent('reticula-gaze', {
  init() {
    const el = this.el;
    const add = (geo, mat) => {
      const e = document.createElement('a-entity');
      e.setAttribute('geometry', geo);
      e.setAttribute('material', 'shader: flat; transparent: true; depthTest: false; ' + mat);
      e.object3D.renderOrder = 999;
      el.appendChild(e);
      return e;
    };
    this.punto = add('primitive: circle; radius: 0.005; segments: 16', 'color: #ffffff; opacity: 0.95');
    this.base = add('primitive: ring; radiusInner: 0.014; radiusOuter: 0.02; segmentsTheta: 48', 'color: #ffffff; opacity: 0.45');
    this.progreso = add('primitive: ring; radiusInner: 0.014; radiusOuter: 0.02; segmentsTheta: 48; thetaStart: 90; thetaLength: 0.01',
      'color: #ff6fc8; opacity: 1');
    this.inicio = null;

    el.addEventListener('mouseenter', () => el.setAttribute('animation__z', 'property: scale; to: 1.5 1.5 1.5; dur: 150'));
    el.addEventListener('mouseleave', () => { this.reset(); el.setAttribute('animation__z', 'property: scale; to: 1 1 1; dur: 150'); });
    el.addEventListener('fusing', () => { this.inicio = performance.now(); });
    el.addEventListener('click', () => this.reset());
  },
  reset() {
    this.inicio = null;
    this.progreso.setAttribute('geometry', 'thetaLength', 0.01);
  },
  tick() {
    if (this.inicio === null) return;
    const dur = this.el.getAttribute('cursor').fuseTimeout;
    const t = Math.min(1, (performance.now() - this.inicio) / dur);
    // en sentido horario desde arriba
    this.progreso.setAttribute('geometry', { thetaStart: 90 - 360 * t, thetaLength: Math.max(0.01, 360 * t) });
  }
});

/* Pequenos destellos que flotan y parpadean alrededor del usuario. */
AFRAME.registerComponent('destellos', {
  schema: {
    cantidad: { type: 'int', default: 60 },
    radio: { type: 'number', default: 6 }
  },
  init() {
    const colores = ['#ffffff', '#fff3a0', '#bfefff', '#ffc4ef', '#c9ffd0'];
    for (let i = 0; i < this.data.cantidad; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 1.8 + Math.random() * (this.data.radio - 1.8);
      const y = 0.3 + Math.random() * 3.2;
      const s = document.createElement('a-entity');
      s.setAttribute('geometry', 'primitive: octahedron; radius: ' + (0.015 + Math.random() * 0.025));
      s.setAttribute('material', `shader: flat; color: ${colores[i % colores.length]}; transparent: true; opacity: 0.9`);
      s.setAttribute('position', `${Math.cos(a) * r} ${y} ${Math.sin(a) * r}`);
      const dur = 2500 + Math.random() * 3500;
      s.setAttribute('animation__sube',
        `property: position; to: ${Math.cos(a) * r} ${y + 0.35} ${Math.sin(a) * r}; dir: alternate; loop: true; dur: ${dur}; easing: easeInOutSine`);
      s.setAttribute('animation__brillo',
        `property: material.opacity; from: 0.15; to: 1; dir: alternate; loop: true; dur: ${600 + Math.random() * 1400}; delay: ${Math.random() * 2000}`);
      s.setAttribute('animation__gira', `property: rotation; to: 0 360 0; loop: true; dur: ${3000 + Math.random() * 3000}; easing: linear`);
      this.el.appendChild(s);
    }
  }
});

/* Mantiene la camara cerca del centro para no romper la ilusion 360. */
AFRAME.registerComponent('movement-bounds', {
  schema: { radio: { type: 'number', default: 2.5 } },
  tick() {
    const cam = document.getElementById('camara');
    if (!cam) return;
    const p = cam.object3D.position;
    const d = Math.hypot(p.x, p.z);
    if (d > this.data.radio) {
      p.x *= this.data.radio / d;
      p.z *= this.data.radio / d;
    }
  }
});
