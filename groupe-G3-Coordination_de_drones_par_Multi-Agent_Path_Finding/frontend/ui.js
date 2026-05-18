// frontend/ui.js
export class UIManager {
  constructor({ onSolve, onPlay, onPause, onReset, onStep }) {
    document.getElementById('btn-solve').onclick  = () => onSolve();
    document.getElementById('btn-play').onclick   = onPlay;
    document.getElementById('btn-pause').onclick  = onPause;
    document.getElementById('btn-reset').onclick  = onReset;
    document.getElementById('btn-step').onclick   = onStep;
  }

  updateFrame(frame, maxFrame) {
    document.getElementById('h-frame').textContent = `${frame}/${maxFrame}`;
  }
}
