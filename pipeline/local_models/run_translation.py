"""Have a local language model (llama-server) translate the comparison set, one entry per request.

Usage: python3 -I pipeline/local_models/run_translation.py SET.json OUT.json --port 8771 [--langs en,lt] [--no-glossary]
The system prompt carries the same rules the translation agents get and, for Lithuanian / Polish,
the whole glossary (docs/LT_GLOSSARY.md, docs/PL_GLOSSARY.md); llama-server reuses that prefix
between requests. One request per language, so each fits a small model's context.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANG = {'en': 'English', 'lt': 'Lithuanian', 'pl': 'Polish'}
RULES = """You translate machine-read drafts of Roman Catholic baptism register entries (Plungė parish, Samogitia; Russian in pre-1918 spelling; 1849–1907) into direct, natural {lang}.

Each entry has three columns: baptism (when, where and by whom baptised, the child's name), parents (estate, township, father, mother with maiden name, family surname, birth date, village) and godparents. The drafts come from a handwriting-recognition model and contain errors: spurious spaces inside words, confused letters (х/к, е/с, и/н), dropped letters. The text follows a fixed formula:
- Baptism: "Тысяча восемьсотъ [year in words] года [month] [ordinal] дня въ Плунгянскомъ Р.К. Приходскомъ Костелѣ Викарнымъ Кс: [priest] окрещенъ младенецъ именемъ [NAME] со всѣми обрядами Таинства."
- Parents: "Крестьянъ [township] волости [father, gen.] и [mother, gen.] изъ [maiden name] [family surname, gen. pl.] законныхъ супруговъ сынъ/дочь родившійся/родившаяся [year] года [month] [day] дня въ деревнѣ [village] сего Прихода." (older books: "урожденной [maiden name]")
- Godparents: "Воспріемниками были [name] съ [name] [дѣвицею / вдовою / … супругою]."
margin_surname is the family surname as read from the margin of the page; it is the same surname the parents column writes, and usually the better reading.

Rules:
1. Translate fully into fluent sentences; never word-by-word glosses. Use the year actually written.
2. Repair obvious misreadings of the formula's FIXED words, and join split words.
3. NEVER correct, guess or normalise personal names, surnames, villages or townships beyond what the rules allow: transliterate what is written and add [?] when the reading is doubtful. {names}
4. Garbled fragments: {illegible} or transliteration + [?]. Never invent content. An empty column gives "".
5. Keep dates and numbers as the draft gives them; do not compute or correct.
6. Deviations from the formula (twins, illegitimate birth, another parish, notes) are translated, not dropped, and mentioned in "issues".
{model}
Answer with one JSON object: {{"baptism": "...", "parents": "...", "godparents": "...", "issues": "short note on uncertain parts, or empty"}}."""
SPEC = {
    'en': {'names': 'Romanise (ж zh, х kh, ц ts, ч ch, ш sh, щ shch, ю iu, я ia, й i, ъ dropped, ѣ e, і i); use the standard Polish given-name form only when it is clearly that name.',
           'illegible': '[illegible]',
           'model': 'Model: "In the year one thousand eight hundred and eighty-eight, on the [ordinal] day of [month], in the Plungė Roman Catholic parish church, the vicar Fr. [priest] baptised an infant named [NAME] with all the rites of the Sacrament." / "Son/daughter of [father] and [mother] née [maiden name], [surname], lawfully married peasants of [township] district, born on the [day] of [month] [year] in the village of [village] of this parish." / "The godparents were [name] and [name], [a maiden / a widow / wife of …]."'},
    'lt': {'names': 'Follow the glossary below exactly for every formula phrase, social term, month, clergy name, given name and surname rule.',
           'illegible': '[neįskaitoma]', 'model': ''},
    'pl': {'names': 'Follow the glossary below exactly for every formula phrase, social term, month, clergy name, given name and surname rule.',
           'illegible': '[nieczytelne]', 'model': ''},
}
SCHEMA = {'type': 'object', 'properties': {k: {'type': 'string'} for k in ('baptism', 'parents', 'godparents', 'issues')},
          'required': ['baptism', 'parents', 'godparents', 'issues']}


def system(lang, glossary):
    s = RULES.format(lang=LANG[lang], **SPEC[lang])
    if lang != 'en' and glossary:
        s += '\n\n===== GLOSSARY =====\n' + (ROOT / 'docs' / f'{lang.upper()}_GLOSSARY.md').read_text()
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--port', type=int, default=8771)
    ap.add_argument('--langs', default='en,lt')
    ap.add_argument('--no-glossary', action='store_true')
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    items = json.loads(args.set.read_text())[:args.limit]
    done = {r['id']: r for r in json.loads(args.out.read_text())} if args.out.exists() else {}
    for lang in args.langs.split(','):
        sysmsg = system(lang, not args.no_glossary)
        for it in items:
            rec = done.setdefault(it['id'], {'id': it['id'], 'seconds': {}})
            if f'baptism_{lang}' in rec or (lang == 'pl' and 'baptism_pl' not in it['reference']):
                continue
            user = json.dumps({'year_range': it['years'], **it['source'], 'margin_surname': it['margin_surname']}, ensure_ascii=False, indent=1)
            body = {'messages': [{'role': 'system', 'content': sysmsg}, {'role': 'user', 'content': user}], 'temperature': 0,
                    'max_tokens': 900, 'cache_prompt': True, 'chat_template_kwargs': {'enable_thinking': False},
                    'response_format': {'type': 'json_schema', 'json_schema': {'name': 'entry', 'schema': SCHEMA}}}
            req = urllib.request.Request(f'http://127.0.0.1:{args.port}/v1/chat/completions', json.dumps(body).encode(),
                                         {'Content-Type': 'application/json'})
            t = time.time()
            m = json.loads(urllib.request.urlopen(req, timeout=900).read())['choices'][0]['message']['content']
            try:
                o = json.loads(m)
            except ValueError:
                o = {'baptism': m, 'parents': '', 'godparents': '', 'issues': 'UNPARSED'}
            for c in ('baptism', 'parents', 'godparents', 'issues'):
                rec[f'{c}_{lang}'] = o.get(c, '')
            rec['seconds'][lang] = round(time.time() - t, 1)
            args.out.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1))
            print(lang, it['id'], rec['seconds'][lang], 's |', rec[f'parents_{lang}'][:150], flush=True)


if __name__ == '__main__':
    main()
