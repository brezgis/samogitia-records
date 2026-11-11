"""Build versioned crops, the transcription queue, and a reviewed pilot table.

Original scans, crops, layouts and reader outputs are never overwritten.
Run after gazetteer.py: .venv/bin/python -I pipeline/prepare.py
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT/'data/plunge-1886-1890'


def sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = BOOK/'processed'
    for sub in ['rows', 'layout', 'batches']:
        (out/sub).mkdir(parents=True, exist_ok=True)
    overrides = json.loads((BOOK/'review/layout_overrides.json').read_text())
    adjudications = {(e['scan'], e['entry_no']): e for e in json.loads((BOOK/'review/adjudication.json').read_text())}
    sources = {}
    for path in sorted((BOOK/'reads').glob('*.json')):
        if 'merged' in path.name:
            continue
        for e in json.loads(path.read_text()):
            sources.setdefault((e['scan'], e['entry_no']), []).append({'file':str(path.relative_to(ROOT)), 'sha256':digest(path), 'entry':e})
    old_row_index = {}
    for key, reads in sources.items():
        for item in reads:
            rid = item['entry'].get('row_image')
            if rid:
                old_row_index[rid] = key
    queue, pages = [], []
    for path in sorted((BOOK/'layout').glob('*.json')):
        old = json.loads(path.read_text()); scan = old['scan']
        source = BOOK/f'pages/{scan:04}.jpg'
        image = Image.open(source); w,h=image.size; sha=digest(source)
        new_pages = []
        for pg in old['pages']:
            page_id = f"{scan:04}_{pg['page']}"
            classification = overrides['page_classification'].get(page_id, {})
            new = {'page_id':page_id, 'kind':classification.get('kind','register_table'),
                   'source':str(source.relative_to(ROOT)), 'source_sha256':sha,
                   'source_layout':str(path.relative_to(ROOT)), 'rows':[]}
            if classification:
                new['evidence'] = classification['evidence']; pages.append(new); new_pages.append(new); continue
            override = overrides['boundaries'].get(page_id)
            if override:
                cuts = override['cuts']
                intervals = list(zip(cuts[:-1],cuts[1:]))
                new['layout_status'] = override['status']
            else:
                intervals = [(r['y0'],r['y1']) for r in pg.get('rows',[])]
                new['layout_status'] = 'image_checked' if page_id in overrides['checked_unchanged'] else 'automatic_unreviewed'
            for i,(y0,y1) in enumerate(intervals,1):
                row_id=f'{page_id}{i}'
                label=overrides['row_classification'].get(row_id,{})
                year=label.get('register_year', overrides['page_years'].get(page_id,1888))
                kind=label.get('kind','baptism')
                # Entire half-page width retains the sideways surname and all table columns.
                x0,x1=(0,w//2) if pg['page']=='L' else (w//2,w)
                bbox=[x0,max(0,y0-70),x1,min(h,y1+150)]
                target=out/f'rows/{row_id}.jpg'
                image.crop(tuple(bbox)).save(target,quality=92)
                oldkey=old_row_index.get(row_id) if not override else None
                entry_no=label.get('entry_no', oldkey[1] if oldkey else None)
                row={'row_id':row_id, 'scan':scan, 'page':pg['page'], 'row_index':i,
                     'kind':kind,'register_year':year,'entry_no':entry_no,
                     'entry_no_status':'image_read' if 'entry_no' in label else 'prior_reader' if oldkey else 'not_read',
                     'image':str(target.relative_to(ROOT)), 'source':str(source.relative_to(ROOT)),
                     'source_sha256':sha,'image_sha256':digest(target),'bbox':bbox,
                     'focal_y':[y0,y1], 'layout_status':new['layout_status'],
                     'in_target_year':kind=='baptism' and year==1888,
                     'transcription_status':'pilot_image_reviewed' if oldkey in adjudications else 'pending',
                     'hand_group':'early_candidate' if scan<=109 else 'later_candidate',
                     'hand_group_status':'provisional_scan_range'}
                if 'evidence' in label: row['evidence']=label['evidence']
                new['rows'].append(row); queue.append(row)
            pages.append(new); new_pages.append(new)
        write_json(out/f'layout/{scan:04}.json',{'scan':scan,'pages':new_pages})
    target=[r for r in queue if r['in_target_year']]
    for expected,row in enumerate(target,1):
        # Coverage aid only. Never substitute this inferred sequence for a read number.
        row['expected_entry_no']=expected
        if row['entry_no'] is not None and row['entry_no']!=expected:
            raise ValueError(f"Number/coverage mismatch at {row['row_id']}: read {row['entry_no']}, expected {expected}")
    write_json(out/'queue.json',queue)
    pending=[r for r in target if r['transcription_status']=='pending']
    # Remove only generated batch manifests so reruns cannot leave obsolete jobs.
    for old_batch in (out/'batches').glob('[0-9][0-9][0-9].json'):
        old_batch.unlink()
    for first in range(0,len(pending),16):
        write_json(out/f'batches/{first//16+1:03}.json',{'status':'pending','independent_reads_required':2,
                   'instructions':'src/READING_INSTRUCTIONS.md','rows':pending[first:first+16]})
    g=sibling('gazetteer'); r=sibling('reconcile'); places=g.load_places()
    pilot=[]; field_rows=[]
    for key,review in sorted(adjudications.items()):
        source_image=BOOK/f"rows/{review['row_image']}.jpg"
        if digest(source_image)!=review['image_sha256']:
            raise ValueError(f'Review image changed: {source_image}')
        item={'scan':key[0], 'entry_no':key[1], 'register_year':1888, 'calendar':'Julian',
              'review_status':'provisional_image_review', 'human_verified':False,
              'source_image':str(source_image.relative_to(ROOT)), 'source_sha256':review['image_sha256'],
              'reviewer':review['reviewer'],'notes':review['notes'], 'fields':{},
              'original_readings':sources[key]}
        for field in r.FIELDS:
            values=[{'source_file':s['file'],'value':s['entry'].get(field),
                     'flagged':field in s['entry'].get('uncertain',[])} for s in sources[key]]
            if field in review['fields']:
                result=review['fields'][field].copy()
            else:
                nonempty=[r.norm(v['value']) for v in values if r.norm(v['value'])]
                agreed=bool(nonempty and len(nonempty)==len(values) and len(set(nonempty))==1)
                result={'value':values[0]['value'] if agreed else None,
                        'status':'reader_agreement_unreviewed' if agreed else 'unresolved', 'training_eligible':False}
            result['readings']=values
            item['fields'][field]=result
            field_rows.append({'scan':key[0],'entry_no':key[1],'field':field,
                               'value':result['value'],'status':result['status'],
                               'source_image':item['source_image'],'reviewer':review['reviewer']})
        item['village_candidates']=g.proposal(item['fields']['village_ru']['value'],places)
        pilot.append(item)
    write_json(out/'pilot_reference.json',pilot)
    with (out/'pilot_reference.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(field_rows[0]));writer.writeheader();writer.writerows(field_rows)
    summary={'source_spreads':54,'page_sides':len(pages),'classified_non_table_sides':sum(p['kind']!='register_table' for p in pages),
             'manually_corrected_table_sides':len(overrides['boundaries']),
             'all_row_crops':len(queue),'target_year_row_crops':len(target),'pending_target_rows':len(pending),
             'visually_reviewed_pilot_entries':len(pilot),'pilot_fields_by_status':{s:sum(f['status']==s for f in field_rows) for s in sorted({f['status'] for f in field_rows})},
             'year_end_entry_no':434, 'row_count_matches_terminal_number':len(target)==434,
             'warning':'Row counts are not proof of complete coverage. Pending rows still need number/date checks. Pilot is machine-adjudicated, not certified ground truth.'}
    write_json(out/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
