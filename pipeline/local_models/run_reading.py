"""Have a local vision model (llama-server, OpenAI-style API) read the held-out line set.

Usage: python3 -I pipeline/local_models/run_reading.py SET.json OUT.json --port 8771 --mode blind|shots|correct
       [--limit N] [--scale 2.0]
blind: image + description of the source. shots: the same, after four checked lines of the same
book as worked examples. correct: image + the recognizer's draft, to be corrected against the image.
Resumable: lines already in OUT.json are skipped. Scores: pipeline/local_models/score_reading.py.
"""
import argparse
import base64
import io
import json
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CELL = {'baptism': 'when, where and by whom baptised', 'parents': 'the parents and the birth',
        'godparents': 'the godparents'}
SYSTEM = ("You transcribe single handwritten lines cut from a Roman Catholic baptism register of Samogitia "
          "(Russian Empire, {years}). The hand is Russian cursive in pre-1918 spelling (ъ at word ends, ѣ, і). "
          "The text follows formulas, e.g. «Тысяча восемьсотъ восемьдесятъ восьмаго года Января десятаго дня въ "
          "Плунгянскомъ Р.К. приходскомъ Костелѣ Викарнымъ Кс. … окрещенъ младенецъ именемъ … со всѣми обрядами "
          "Таинства», «Крестьянъ Плунгянской волости … и … изъ … законныхъ супруговъ сынъ/дочь родившійся … года … "
          "дня въ деревнѣ … сего прихода», «Воспріемниками были … съ … дѣвицею / супругою». Personal and place "
          "names are Lithuanian or Polish names in Russian letters. A line is a fragment: it may start or end in "
          "the middle of a word (keep a hyphen at the line end if written). Transcribe exactly what is written, "
          "letter for letter, in Cyrillic; do not modernise spelling, expand abbreviations or complete the "
          "sentence. Answer with the transcription only.")


def data_url(path, scale):
    im = Image.open(ROOT / path).convert('RGB')
    if scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def img(path, scale):
    return {'type': 'image_url', 'image_url': {'url': data_url(path, scale)}}


def messages(line, shots, mode, scale):
    msgs = [{'role': 'system', 'content': SYSTEM.format(years=line['years'])}]
    if mode == 'shots':
        for s in shots:
            msgs.append({'role': 'user', 'content': [img(s['image'], scale), {'type': 'text', 'text': f"Column: {CELL.get(s['cell'], s['cell'])}. Transcribe this line."}]})
            msgs.append({'role': 'assistant', 'content': s['text']})
    ask = f"Column: {CELL.get(line['cell'], line['cell'])}. Transcribe this line."
    if mode == 'correct':
        ask = (f"Column: {CELL.get(line['cell'], line['cell'])}. A handwriting-recognition model read this line as:\n{line['htr']}\n"
               "It is usually close but gets some letters wrong, splits or joins words wrongly, or drops letters. "
               "Compare it with the image and give the corrected line. If it is already right, repeat it unchanged.")
    msgs.append({'role': 'user', 'content': [img(line['image'], scale), {'type': 'text', 'text': ask}]})
    return msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--port', type=int, default=8771)
    ap.add_argument('--mode', choices=['blind', 'shots', 'correct'], default='blind')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--every', type=int, default=1)
    ap.add_argument('--scale', type=float, default=2.0)
    ap.add_argument('--max-tokens', type=int, default=120)
    args = ap.parse_args()
    data = json.loads(args.set.read_text())
    lines = data['lines'][::args.every][:args.limit]
    done = {r['id']: r for r in json.loads(args.out.read_text())} if args.out.exists() else {}
    t0 = time.time()
    for n, line in enumerate(lines):
        if line['id'] in done:
            continue
        body = {'messages': messages(line, data['shots'][line['book']], args.mode, args.scale), 'temperature': 0,
                'max_tokens': args.max_tokens, 'chat_template_kwargs': {'enable_thinking': False}}
        req = urllib.request.Request(f'http://127.0.0.1:{args.port}/v1/chat/completions', json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
        t = time.time()
        m = json.loads(urllib.request.urlopen(req, timeout=300).read())['choices'][0]['message']
        text = (m.get('content') or '').strip().split('\n')[0].strip(' «»"')
        done[line['id']] = {'id': line['id'], 'text': text, 'seconds': round(time.time() - t, 2)}
        if n % 20 == 0:
            args.out.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1))
            print(n, round(time.time() - t0), repr(line['text']), '|', repr(text), flush=True)
    args.out.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
