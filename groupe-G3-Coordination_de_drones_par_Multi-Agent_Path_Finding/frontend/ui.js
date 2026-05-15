// frontend/ui.js
export class UIManager {
  constructor({ onSolve, onPlay, onPause, onReset, onStep, onAddNoFly, onClearNoFly }) {
    this._nofly = [];
    this._placingNoFly = false;
    this._btnNF = document.getElementById('btn-nofly');

    document.getElementById('btn-solve').onclick  = () => onSolve(this._nofly);
    document.getElementById('btn-play').onclick     = onPlay;
    document.getElementById('btn-pause').onclick    = onPause;
    document.getElementById('btn-reset').onclick    = onReset;
    document.getElementById('btn-step').onclick     = onStep;

    this._btnNF.onclick = () => {
      this._placingNoFly = !this._placingNoFly;
      this._syncBtn();
    };

    document.getElementById('btn-clear-nofly').onclick = () => {
      this._nofly = [];
      this._placingNoFly = false;
      this._syncBtn();
      onClearNoFly();
    };

    this._onAddNoFly = onAddNoFly;
  }

  _syncBtn() {
    const on = this._placingNoFly;
    this._btnNF.classList.toggle('is-active', on);
    this._btnNF.textContent = on ? '🚫 Click grid…' : '🚫 No-Fly';
  }

  isPlacingNoFly() { return this._placingNoFly; }

  addNoFlyFromClick(row, col) {
    const nf = { min: [row, col], max: [row, col] };
    this._nofly.push(nf);
    this._onAddNoFly(nf);
  }

  getNoFly() { return this._nofly; }

  updateFrame(frame, maxFrame) {
    document.getElementById('h-frame').textContent = `${frame}/${maxFrame}`;
  }
}
