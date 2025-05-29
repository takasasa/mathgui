const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
canvas.width = 1200;
canvas.height = 400;

let drawing = false;
let currentPath = [];
let paths = [];
let undonePaths = [];
let eraserMode = false;

const defaultLineWidth = 4;
const eraserLineWidth = defaultLineWidth * 3;

ctx.lineCap = 'round';
ctx.lineWidth = defaultLineWidth;
ctx.strokeStyle = 'black';

const macroBox = document.getElementById('macrosInput');
const promptBox = document.getElementById('promptInput');
if (macroBox && promptBox) {
    macroBox.value = "\\newcommand{\\R}{\\mathbb{R}}\n\\newcommand{\\vct}[1]{\\mathbf{#1}}\n\\newcommand{\\gvct}[1]{\\boldsymbol{#1}}\n\\newcommand{\\mat}[1]{\\mathbf{#1}}\n\\newcommand{\\gmat}[1]{\\boldsymbol{#1}}";
    promptBox.value = "Vectors and matrices should be expressed using \\vct (for Latin vectors), \\gvec (for Greek vectors), \\mat (for Latin matrices), and \\gmat (for Greek matrices). \nCharacters with double lines should be interpreted as vectors if they are lowercase letters, and as matrices if they are uppercase letters. ";
}

function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let stroke of paths) {
        ctx.beginPath();
        ctx.strokeStyle = stroke.color;
        ctx.lineWidth = stroke.width;
        for (let i = 0; i < stroke.points.length; i++) {
            const p = stroke.points[i];
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
    }
}

canvas.addEventListener('pointerdown', (e) => {
    drawing = true;
    currentPath = [];
    ctx.beginPath();
    ctx.moveTo(e.offsetX, e.offsetY);
    currentPath.push({ x: e.offsetX, y: e.offsetY });
    ctx.strokeStyle = eraserMode ? 'white' : 'black';
    ctx.lineWidth = eraserMode ? eraserLineWidth : defaultLineWidth;
});

canvas.addEventListener('pointermove', (e) => {
    if (!drawing) return;
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
    currentPath.push({ x: e.offsetX, y: e.offsetY });
});

canvas.addEventListener('pointerup', () => {
    drawing = false;
    if (currentPath.length > 0) {
        paths.push({
            points: currentPath,
            color: ctx.strokeStyle,
            width: ctx.lineWidth
        });
        undonePaths = [];
    }
});

canvas.addEventListener('pointerout', () => { drawing = false; });
canvas.addEventListener('pointercancel', () => { drawing = false; });

document.getElementById('undoBtn').addEventListener('click', () => {
    if (paths.length === 0) return;
    const last = paths.pop();
    undonePaths.push(last);
    redraw();
});

document.getElementById('redoBtn').addEventListener('click', () => {
    if (undonePaths.length === 0) return;
    const restored = undonePaths.pop();
    paths.push(restored);
    redraw();
});

document.getElementById('clearBtn').addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    paths = [];
    undonePaths = [];
});

document.getElementById('eraserToggle').addEventListener('click', () => {
    eraserMode = !eraserMode;
    document.getElementById('eraserToggle').innerText = eraserMode ? 'Eraser ON' : 'Eraser OFF';
});

// --- Convert ---
document.getElementById('convertBtn').addEventListener('click', async () => {
    const imageData = canvas.toDataURL('image/png');
    const macros = document.getElementById('macrosInput').value;
    const prompt = document.getElementById('promptInput').value;

    const response = await fetch('/convert', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image_data: imageData, macros: macros , prompt: prompt}),
    });

    if (response.ok) {
        const data = await response.json();
        const latex = data.latex || '';

        document.getElementById('latexDisplay').textContent = latex;
        document.getElementById('rendered').innerHTML = `\\[${data.full_latex}\\]`;
        MathJax.typesetPromise();
    } else {
        alert('変換に失敗しました。');
    }
});

// --- Copy ---
document.getElementById('copyBtn').addEventListener('click', () => {
    const latex = document.getElementById('latexDisplay').textContent;
    navigator.clipboard.writeText(latex).then(() => {
        alert('LaTeXコードをコピーしました');
    });
});