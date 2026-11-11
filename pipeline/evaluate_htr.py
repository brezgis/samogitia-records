"""Strict, Unicode-preserving CER/WER for a complete keyed prediction set.

Usage: evaluate_htr.py reference.json predictions.json
Each file is a list of {id, text, ...}. References may include hand_group/cell.
Missing predictions count as deletions; extra or duplicate IDs are errors.
"""
import json
import sys
import unicodedata
from collections import defaultdict


def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1): nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]


def index(entries):
    out={}
    for e in entries:
        if e['id'] in out: raise ValueError('Duplicate id: '+e['id'])
        if not isinstance(e.get('text'),str): raise ValueError('Missing text: '+e['id'])
        out[e['id']]=e
    return out


def evaluate(reference,predictions):
    refs,preds=index(reference),index(predictions)
    if not refs: raise ValueError('Empty reference set')
    if set(preds)-set(refs): raise ValueError('Predictions contain unknown ids')
    groups=defaultdict(lambda:{'lines':0,'exact_lines':0,'character_errors':0,'characters':0,'word_errors':0,'words':0,'missing_predictions':0})
    for ident,ref in refs.items():
        truth=unicodedata.normalize('NFC',ref['text'])
        if not truth: raise ValueError('Empty reference text: '+ident)
        guess=unicodedata.normalize('NFC',preds.get(ident,{}).get('text',''))
        for group in ['all','hand:'+ref.get('hand_group','unknown'),'cell:'+ref.get('cell','unknown')]:
            m=groups[group];m['lines']+=1;m['exact_lines']+=truth==guess
            m['character_errors']+=distance(truth,guess);m['characters']+=len(truth)
            m['word_errors']+=distance(truth.split(),guess.split());m['words']+=len(truth.split())
            m['missing_predictions']+=ident not in preds
    for m in groups.values():
        m['cer']=m['character_errors']/m['characters'] if m['characters'] else None
        m['wer']=m['word_errors']/m['words'] if m['words'] else None
    return dict(groups)


if __name__=='__main__':
    print(json.dumps(evaluate(json.load(open(sys.argv[1])),json.load(open(sys.argv[2]))),indent=2))
